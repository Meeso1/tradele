from datetime import UTC, datetime
import logging
import math
from typing import Literal

from pydantic.dataclasses import dataclass

from app.models.market import HourlyDate, MarketState
from app.models.portfolio import Portfolio
from app.models.trade import ActiveTrade, InactiveTradeStatus
from app.repositories.portfolio_repository import PortfolioRepository
from app.repositories.trade_repository import TradeRepository
from app.services.database_service import DatabaseService
from app.services.market_data_service import MarketDataService
from app.services.user_service import UserService


TradeExecutionResult = Literal[
    "success",
    "error",
    "insufficient_funds",
    "symbol_unavailable",
    "malformed_request",
]


@dataclass
class PortfolioState:
    cash: float
    holdings: dict[str, float]


@dataclass
class TradeExecutionDetails:
    result: TradeExecutionResult
    fill_price: float | None


class TradeExecutionService:
    def __init__(
        self,
        logger: logging.Logger,
        trade_repo: TradeRepository,
        market_data_service: MarketDataService,
        portfolio_repo: PortfolioRepository,
        user_service: UserService,
        database: DatabaseService,
    ) -> None:
        self._logger: logging.Logger = logger
        self._trade_repo: TradeRepository = trade_repo
        self._market_data_service: MarketDataService = market_data_service
        self._portfolio_repo: PortfolioRepository = portfolio_repo
        self._user_service: UserService = user_service
        self._database: DatabaseService = database

    def configure(self, logger: logging.Logger) -> None:
        self._logger = logger

    def fastforward_all_users(self) -> None:
        """Fastforward active trades to the current hour for every user."""
        for user_id in self._user_service.list_ids():
            try:
                self.fastforward_user_trades_to_current_hour(user_id)
            except Exception:
                self._logger.exception("Failed to fastforward trades for user %s", user_id)

    def fastforward_user_trades_to_current_hour(self, user_id: str) -> None:
        """Fastforward all active trades for the given user to the current hour."""
        # Start updates from the first hour after the last portfolio update
        current_hour = HourlyDate.current_with_available_market_data()
        starting_hour = HourlyDate.next(last_portfolio_update) \
            if (last_portfolio_update := self._portfolio_repo.get_or_create(user_id).last_hourly_update) is not None \
            else None
        if starting_hour is None:
            # If portfolio is new, start from the earliest active_from out of active trades
            trades = self._trade_repo.list_active_in_order(user_id, current_hour)
            if len(trades) == 0:
                # Nothing to do
                return

            starting_hour = trades[0].active_from
        
        for hour in HourlyDate.enumerate_range(starting_hour, current_hour):
            self.execute_user_trades_at_hour(user_id, hour)
    
    def execute_user_trades_at_hour(self, user_id: str, hour: HourlyDate) -> None:
        """Attempt to execute all active trades for the given user against hourly windows up to the current time."""
        active_trades = self._trade_repo.list_active_in_order(user_id, hour)

        portfolio = self._portfolio_repo.get_or_create(user_id)
        if portfolio.last_hourly_update is not None and portfolio.last_hourly_update >= hour:
            self._logger.info("Skipping trades update for hour %s for user %s - portfolio was updated up %s", hour, user_id, portfolio.last_hourly_update)
            return

        pricing_data = self._market_data_service.get_prices(hour)
        if not pricing_data.market_open:
            self._logger.info("Skipping trades update for hour %s for user %s - market is closed", hour, user_id)
            return

        state = PortfolioState(cash=portfolio.cash, holdings=portfolio.holdings)

        executed_trades: list[tuple[ActiveTrade, TradeExecutionDetails]] = []
        for trade in active_trades:
            details, state = self._try_execute_trade(trade, pricing_data, state)
            if details is not None:
                executed_trades.append((trade, details))

        new_portfolio = Portfolio(cash=state.cash, holdings=state.holdings, last_hourly_update=hour)

        # Move all executed trades and update the portfolio in a single
        # transaction, so a failure partway through can't leave a trade
        # marked executed without the portfolio reflecting it (or vice versa).
        with self._database.transaction():
            for trade, details in executed_trades:
                self._trade_repo.move_to_executed(
                    trade.id,
                    details.fill_price,
                    datetime.now(UTC),
                    pricing_data.hour,
                    self._to_status(details.result),
                )

            self._portfolio_repo.update(user_id, new_portfolio)

    def _try_execute_trade(
        self,
        trade: ActiveTrade,
        pricing_data: MarketState,
        portfolio: PortfolioState,
    ) -> tuple[TradeExecutionDetails | None, PortfolioState]:
        """Attempt to execute a single trade against the given hourly window."""
        match trade.kind:
            case "market_buy":
                return self._try_execute_market_buy(trade.symbol, trade.quantity, trade.value, pricing_data, portfolio)
            case "market_sell":
                return self._try_execute_market_sell(trade.symbol, trade.quantity, trade.value, pricing_data, portfolio)
            case "limit_buy":
                return self._try_execute_limit_buy(trade.symbol, trade.requested_price, trade.quantity, trade.value, pricing_data, portfolio)
            case "limit_sell":
                return self._try_execute_limit_sell(trade.symbol, trade.requested_price, trade.quantity, trade.value, pricing_data, portfolio)
            case "stop_buy":
                return self._try_execute_stop_buy(trade.symbol, trade.requested_price, trade.quantity, trade.value, pricing_data, portfolio)
            case "stop_sell":
                return self._try_execute_stop_sell(trade.symbol, trade.requested_price, trade.quantity, trade.value, pricing_data, portfolio)
            case _:  # pyright: ignore[reportUnnecessaryComparison]
                raise ValueError(f"Unknown trade kind: {trade.kind}") # pyright: ignore[reportUnreachable]

    def _try_execute_market_buy(
        self,
        symbol: str,
        quantity: float | None,
        value: float | None,
        prices: MarketState,
        portfolio: PortfolioState,
    ) -> tuple[TradeExecutionDetails | None, PortfolioState]:
        """
        Attempt to execute a market buy trade against the given hourly window.

        Returns a tuple of (result, updated_portfolio).
        """
        if not self._is_quantity_and_value_valid(quantity, value):
            return TradeExecutionDetails(result="malformed_request", fill_price=None), portfolio

        price_data = prices.prices.get(symbol, None)
        if price_data is None:
            self._logger.error(f"No price data for symbol: {symbol} - it may no longer be tradable")
            return TradeExecutionDetails(result="symbol_unavailable", fill_price=None), portfolio # Trade should be closed - all other windows will also fail

        if quantity is None:
            quantity = self._value_to_quantity(value, price_data.open, "buy")  # pyright: ignore[reportArgumentType]

        # Market buy is executed at the beginning of the first available hourly window
        total_price = quantity * price_data.open
        if portfolio.cash < total_price:
            self._logger.debug(f"Insufficient cash: {portfolio.cash} < {total_price} - market buy not executed")
            return TradeExecutionDetails(result="insufficient_funds", fill_price=None), portfolio

        new_cash = portfolio.cash - total_price
        new_holdings = portfolio.holdings.copy()
        new_holdings[symbol] = new_holdings.get(symbol, 0) + quantity
        new_portfolio = PortfolioState(cash=new_cash, holdings=new_holdings)
        self._logger.debug(f"Executed market buy: {symbol} @ {price_data.open} x {quantity}")
        return TradeExecutionDetails(result="success", fill_price=price_data.open), new_portfolio

    def _try_execute_market_sell(
        self,
        symbol: str,
        quantity: float | None,
        value: float | None,
        prices: MarketState,
        portfolio: PortfolioState,
    ) -> tuple[TradeExecutionDetails | None, PortfolioState]:
        """
        Attempt to execute a market sell trade against the given hourly window.

        Returns a tuple of (result, updated_portfolio).
        """
        price_data = prices.prices.get(symbol, None)
        if price_data is None:
            self._logger.error(f"No price data for symbol: {symbol} - it may no longer be tradable")
            return TradeExecutionDetails(result="symbol_unavailable", fill_price=None), portfolio # Trade should be closed - all other windows will also fail

        if not self._is_quantity_and_value_valid(quantity, value):
            return TradeExecutionDetails(result="malformed_request", fill_price=None), portfolio

        if quantity is None:
            quantity = self._value_to_quantity(value, price_data.open, "sell")  # pyright: ignore[reportArgumentType]

        # Market sell is executed at the beginning of the first available hourly window
        held_quantity = portfolio.holdings.get(symbol, 0)
        if held_quantity < quantity:
            self._logger.debug(f"Insufficient holdings: {held_quantity} < {quantity} - market sell not executed")
            return TradeExecutionDetails(result="insufficient_funds", fill_price=None), portfolio

        new_cash = portfolio.cash + quantity * price_data.open
        new_holdings = portfolio.holdings.copy()
        new_holdings[symbol] = held_quantity - quantity
        
        new_portfolio = PortfolioState(
            cash=new_cash,
            holdings=new_holdings,
        )
        self._logger.debug(f"Executed market sell: {symbol} @ {price_data.open} x {quantity}")
        return TradeExecutionDetails(result="success", fill_price=price_data.open), new_portfolio

    def _try_execute_limit_buy(
        self,
        symbol: str,
        requested_price: float | None,
        quantity: float | None,
        value: float | None,
        prices: MarketState,
        portfolio: PortfolioState,
    ) -> tuple[TradeExecutionDetails | None, PortfolioState]:
        """
        Attempt to execute a limit buy trade against the given hourly window.

        Returns a tuple of (result, updated_portfolio).
        """
        if not self._is_quantity_and_value_valid(quantity, value):
            return TradeExecutionDetails(result="malformed_request", fill_price=None), portfolio

        if requested_price is None:
            return TradeExecutionDetails(result="malformed_request", fill_price=None), portfolio
        
        price_data = prices.prices.get(symbol, None)
        if price_data is None:
            self._logger.error(f"No price data for symbol: {symbol} - it may no longer be tradable")
            return TradeExecutionDetails(result="symbol_unavailable", fill_price=None), portfolio # Trade should be closed - all other windows will also fail

        if price_data.low > requested_price:
            self._logger.debug(f"Low price ({price_data.low} @ {price_data.starting_hour}) is above requested price ({requested_price}) - limit buy not executed")
            return None, portfolio

        if quantity is None:
            quantity = self._value_to_quantity(value, requested_price, "buy")  # pyright: ignore[reportArgumentType]

        total_price = quantity * requested_price
        if portfolio.cash < total_price:
            self._logger.debug(f"Insufficient cash: {portfolio.cash} < {total_price} - buy not executed")
            return TradeExecutionDetails(result="insufficient_funds", fill_price=None), portfolio

        new_cash = portfolio.cash - total_price
        new_holdings = portfolio.holdings.copy()
        new_holdings[symbol] = new_holdings.get(symbol, 0) + quantity
        new_portfolio = PortfolioState(cash=new_cash, holdings=new_holdings)
        self._logger.debug(f"Executed limit buy: {symbol} @ {requested_price} x {quantity}")
        return TradeExecutionDetails(result="success", fill_price=requested_price), new_portfolio

    def _try_execute_limit_sell(
        self,
        symbol: str,
        requested_price: float | None,
        quantity: float | None,
        value: float | None,
        prices: MarketState,
        portfolio: PortfolioState,
    ) -> tuple[TradeExecutionDetails | None, PortfolioState]:
        """
        Attempt to execute a limit sell trade against the given hourly window.

        Returns a tuple of (success, updated_portfolio).
        """
        if not self._is_quantity_and_value_valid(quantity, value):
            return TradeExecutionDetails(result="malformed_request", fill_price=None), portfolio

        if requested_price is None:
            return TradeExecutionDetails(result="malformed_request", fill_price=None), portfolio

        price_data = prices.prices.get(symbol, None)
        if price_data is None:
            self._logger.error(f"No price data for symbol: {symbol} - it may no longer be tradable")
            return TradeExecutionDetails(result="symbol_unavailable", fill_price=None), portfolio # Trade should be closed - all other windows will also fail

        if price_data.high < requested_price:
            self._logger.debug(f"High price ({price_data.high} @ {price_data.starting_hour}) is below requested price ({requested_price}) - sell not executed")
            return None, portfolio # Trade stays open

        if quantity is None:
            quantity = self._value_to_quantity(value, requested_price, "sell")  # pyright: ignore[reportArgumentType]

        held_quantity = portfolio.holdings.get(symbol, 0)
        if held_quantity < quantity:
            self._logger.debug(f"Insufficient holdings: {symbol} {held_quantity} < {quantity}) - limit sell not executed")
            return TradeExecutionDetails(result="insufficient_funds", fill_price=None), portfolio

        new_cash = portfolio.cash + quantity * requested_price
        new_holdings = portfolio.holdings.copy()
        new_holdings[symbol] = held_quantity - quantity
        
        new_portfolio = PortfolioState(
            cash=new_cash,
            holdings=new_holdings,
        )
        self._logger.debug(f"Executed limit sell: {symbol} @ {requested_price} x {quantity}")
        return TradeExecutionDetails(result="success", fill_price=requested_price), new_portfolio

    def _try_execute_stop_buy(
        self,
        symbol: str,
        requested_price: float | None,
        quantity: float | None,
        value: float | None,
        prices: MarketState,
        portfolio: PortfolioState,
    ) -> tuple[TradeExecutionDetails | None, PortfolioState]:
        """
        Attempt to execute a stop buy trade against the given hourly window.

        Returns a tuple of (result, updated_portfolio).
        """
        if not self._is_quantity_and_value_valid(quantity, value):
            return TradeExecutionDetails(result="malformed_request", fill_price=None), portfolio

        if requested_price is None:
            return TradeExecutionDetails(result="malformed_request", fill_price=None), portfolio
        
        price_data = prices.prices.get(symbol, None)
        if price_data is None:
            self._logger.error(f"No price data for symbol: {symbol} - it may no longer be tradable")
            return TradeExecutionDetails(result="symbol_unavailable", fill_price=None), portfolio # Trade should be closed - all other windows will also fail

        if price_data.high < requested_price:
            self._logger.debug(f"High price ({price_data.high} @ {price_data.starting_hour}) is below requested price ({requested_price}) - stop buy not executed")
            return None, portfolio

        if quantity is None:
            quantity = self._value_to_quantity(value, requested_price, "buy")  # pyright: ignore[reportArgumentType]

        # Stop buy will execute immediately (at open) if the price is above the requested price.
        # Otherwise, it will execute when the price reaches the requested price.
        settled_price = max(price_data.open, requested_price)
        total_price = quantity * settled_price
        if portfolio.cash < total_price:
            self._logger.debug(f"Insufficient cash: {portfolio.cash} < {total_price} - buy not executed")
            return TradeExecutionDetails(result="insufficient_funds", fill_price=None), portfolio

        new_cash = portfolio.cash - total_price
        new_holdings = portfolio.holdings.copy()
        new_holdings[symbol] = new_holdings.get(symbol, 0) + quantity
        new_portfolio = PortfolioState(cash=new_cash, holdings=new_holdings)
        self._logger.debug(f"Executed stop buy: {symbol} @ {settled_price} x {quantity}")
        return TradeExecutionDetails(result="success", fill_price=settled_price), new_portfolio

    def _try_execute_stop_sell(
        self,
        symbol: str,
        requested_price: float | None,
        quantity: float | None,
        value: float | None,
        prices: MarketState,
        portfolio: PortfolioState,
    ) -> tuple[TradeExecutionDetails | None, PortfolioState]:
        """
        Attempt to execute a stop sell trade against the given hourly window.

        Returns a tuple of (result, updated_portfolio).
        """
        if not self._is_quantity_and_value_valid(quantity, value):
            return TradeExecutionDetails(result="malformed_request", fill_price=None), portfolio

        if requested_price is None:
            return TradeExecutionDetails(result="malformed_request", fill_price=None), portfolio
        
        price_data = prices.prices.get(symbol, None)
        if price_data is None:
            self._logger.error(f"No price data for symbol: {symbol} - it may no longer be tradable")
            return TradeExecutionDetails(result="symbol_unavailable", fill_price=None), portfolio # Trade should be closed - all other windows will also fail

        if price_data.low > requested_price:
            self._logger.debug(f"Low price ({price_data.low} @ {price_data.starting_hour}) is above requested price ({requested_price}) - stop sell not executed")
            return None, portfolio

        if quantity is None:
            quantity = self._value_to_quantity(value, requested_price, "sell")  # pyright: ignore[reportArgumentType]

        # Stop sell will execute immediately (at open) if the price is below the requested price.
        # Otherwise, it will execute when the price reaches the requested price.
        held_quantity = portfolio.holdings.get(symbol, 0)
        if held_quantity < quantity:
            self._logger.debug(f"Insufficient holdings: {symbol} {held_quantity} < {quantity}) - stop sell not executed")
            return TradeExecutionDetails(result="insufficient_funds", fill_price=None), portfolio

        settled_price = min(price_data.open, requested_price)
        new_cash = portfolio.cash + quantity * settled_price
        new_holdings = portfolio.holdings.copy()
        new_holdings[symbol] = held_quantity - quantity
        
        new_portfolio = PortfolioState(
            cash=new_cash,
            holdings=new_holdings,
        )
        self._logger.debug(f"Executed stop sell: {symbol} @ {settled_price} x {quantity}")
        return TradeExecutionDetails(result="success", fill_price=settled_price), new_portfolio

    @staticmethod
    def _to_status(result: TradeExecutionResult) -> InactiveTradeStatus:
        match result:
            case "success":
                return "executed"
            case "insufficient_funds":
                return "insufficient_funds"
            case "error":
                return "error"
            case "symbol_unavailable":
                return "symbol_unavailable"
            case "malformed_request":
                return "malformed_request"
            case _:  # pyright: ignore[reportUnnecessaryComparison]
                raise ValueError(f"Unknown result: {result}")  # pyright: ignore[reportUnreachable]

    @staticmethod
    def _is_quantity_and_value_valid(quantity: float | None, value: float | None) -> bool:
        if quantity is None and value is None:
            return False
        if quantity is not None and value is not None:
            return False
        return True

    @staticmethod
    def _value_to_quantity(value: float, price: float, side: Literal["buy", "sell"]) -> float:
        base_quantity = value / price
        if side == "buy":
            # Round down for buy orders - required value must not exceed the requested value
            return int(base_quantity * 1000) / 1000
        if side == "sell":
            # Round up for sell orders - acquired value must not be less than the requested value
            return math.ceil(base_quantity * 1000) / 1000