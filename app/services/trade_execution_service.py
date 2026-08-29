from datetime import UTC, datetime
import logging
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


TradeExecutionResult = Literal["success", "error", "insufficient_funds"]


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
        current_hour = HourlyDate.current()
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

    def _try_execute_trade(self, trade: ActiveTrade, pricing_data: MarketState, portfolio: PortfolioState) -> tuple[TradeExecutionDetails | None, PortfolioState]:
        """Attempt to execute a single trade against the given hourly window."""
        match trade.kind:
            case "limit_buy":
                return self._try_execute_limit_buy(trade.symbol, trade.requested_price, trade.quantity, pricing_data, portfolio)
            case "limit_sell":
                return self._try_execute_limit_sell(trade.symbol, trade.requested_price, trade.quantity, pricing_data, portfolio)
            case _:  # pyright: ignore[reportUnnecessaryComparison]
                raise ValueError(f"Unknown trade kind: {trade.kind}")  # pyright: ignore[reportUnreachable]

    def _try_execute_limit_buy(
        self,
        symbol: str,
        requested_price: float,
        quantity: float,
        prices: MarketState,
        portfolio: PortfolioState,
    ) -> tuple[TradeExecutionDetails | None, PortfolioState]:
        """
        Attempt to execute a simple buy trade against the given hourly window.

        Returns a tuple of (result, updated_portfolio).
        """
        price_data = prices.prices.get(symbol, None)
        if price_data is None:
            self._logger.error(f"No price data for symbol: {symbol}")
            return TradeExecutionDetails(result="error", fill_price=None), portfolio # Trade should be closed - all other windows will also fail

        if price_data.low > requested_price:
            self._logger.debug(f"Low price ({price_data.low} @ {price_data.starting_hour.hour}:00 {price_data.starting_hour.day}) is above requested price ({requested_price}) - buy not executed")
            return None, portfolio

        total_price = quantity * requested_price
        if portfolio.cash < total_price:
            self._logger.debug(f"Insufficient cash: {portfolio.cash} < {total_price} - buy not executed")
            return TradeExecutionDetails(result="insufficient_funds", fill_price=None), portfolio

        new_cash = portfolio.cash - total_price
        new_holdings = portfolio.holdings.copy()
        new_holdings[symbol] = new_holdings.get(symbol, 0) + quantity
        new_portfolio = PortfolioState(cash=new_cash, holdings=new_holdings)
        return TradeExecutionDetails(result="success", fill_price=requested_price), new_portfolio

    def _try_execute_limit_sell(
        self,
        symbol: str,
        requested_price: float,
        quantity: float,
        prices: MarketState,
        portfolio: PortfolioState,
    ) -> tuple[TradeExecutionDetails | None, PortfolioState]:
        """
        Attempt to execute a simple sell trade against the given hourly window.

        Returns a tuple of (success, updated_portfolio).
        """
        price_data = prices.prices.get(symbol, None)
        if price_data is None:
            self._logger.error(f"No price data for symbol: {symbol}")
            return TradeExecutionDetails(result="error", fill_price=None), portfolio # Trade should be closed - all other windows will also fail

        if price_data.high < requested_price:
            self._logger.debug(f"High price ({price_data.high} @ {price_data.starting_hour.hour}:00 {price_data.starting_hour.day}) is below requested price ({requested_price}) - sell not executed")
            return None, portfolio # Trade stays open

        held_quantity = portfolio.holdings.get(symbol, 0)
        if held_quantity < quantity:
            self._logger.debug(f"Insufficient holdings: {symbol} {held_quantity} < {quantity}) - sell not executed")
            return TradeExecutionDetails(result="insufficient_funds", fill_price=None), portfolio

        new_cash = portfolio.cash + quantity * requested_price
        new_holdings = portfolio.holdings.copy()
        new_holdings[symbol] = held_quantity - quantity
        
        new_portfolio = PortfolioState(
            cash=new_cash,
            holdings=new_holdings,
        )
        self._logger.debug(f"Executed simple sell: {symbol} @ {requested_price} x {quantity}")
        return TradeExecutionDetails(result="success", fill_price=requested_price), new_portfolio

    @staticmethod
    def _to_status(result: TradeExecutionResult) -> InactiveTradeStatus:
        match result:
            case "success":
                return "executed"
            case "insufficient_funds":
                return "insufficient_funds"
            case "error":
                return "error"
            case _:  # pyright: ignore[reportUnnecessaryComparison]
                raise ValueError(f"Unknown result: {result}")  # pyright: ignore[reportUnreachable]
            