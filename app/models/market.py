from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, date, datetime, timedelta
from typing import override

from pydantic.dataclasses import dataclass


@dataclass(order=True)
class HourlyDate:
    day: date
    hour: int

    def timestamp(self) -> datetime:
        return datetime(self.day.year, self.day.month, self.day.day, self.hour, tzinfo=UTC)

    @staticmethod
    def containing(timestamp: datetime) -> HourlyDate:
        return HourlyDate(day=timestamp.date(), hour=timestamp.hour)

    @staticmethod
    def current() -> HourlyDate:
        return HourlyDate.containing(datetime.now(UTC))

    @staticmethod
    def last_passed_hour() -> HourlyDate:
        """
        Returns the HourlyDate for the last passed hour.
        Use this to determine the last hour for which market data is available and trades can be executed.
        """
        return HourlyDate.containing(datetime.now(UTC) - timedelta(hours=1))

    @staticmethod
    def next(hour: HourlyDate) -> HourlyDate:
        return HourlyDate.containing(hour.timestamp() + timedelta(hours=1))

    @staticmethod
    def enumerate_range(start: HourlyDate, end: HourlyDate) -> Iterable[HourlyDate]:
        """Yields each HourlyDate in the range [start, end), starting from `start` and incrementing by hour."""
        current = start
        while current < end:
            yield current
            current = HourlyDate.next(current)

    @override
    def __str__(self) -> str:
        return f"{self.hour:02}:00 {self.day.isoformat()}"


@dataclass
class HourlyPriceData:
    symbol: str
    open: float
    high: float
    low: float
    close: float
    starting_hour: HourlyDate


@dataclass
class MarketState:
    hour: HourlyDate
    prices: dict[str, HourlyPriceData]
