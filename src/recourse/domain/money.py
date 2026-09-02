"""An amount of money, in whole cents.

An Explanation of Benefits carries billed, allowed, plan paid and patient
responsibility, and those figures get summed and compared and then quoted back at an
insurer in a letter. A float that drifts by a cent in a document someone is using to
argue is a defect, not a rounding detail.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal


@dataclass(frozen=True, order=True)
class Money:
    cents: int

    @classmethod
    def from_dollars(cls, amount: str | int | float) -> Money:
        """Parse a dollar amount. Strings are exact; floats are a last resort."""
        quantised = (Decimal(str(amount)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return cls(cents=int(quantised))

    @classmethod
    def zero(cls) -> Money:
        return cls(cents=0)

    def scaled(self, factor: float) -> Money:
        """Multiply, rounding half-up to the nearest cent, once."""
        quantised = (Decimal(self.cents) * Decimal(str(factor))).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP,
        )
        return Money(cents=int(quantised))

    def __add__(self, other: Money) -> Money:
        return Money(cents=self.cents + other.cents)

    def __sub__(self, other: Money) -> Money:
        return Money(cents=self.cents - other.cents)

    @property
    def dollars(self) -> str:
        """`"1234.50"` — the form the API sends and a letter quotes."""
        sign = "-" if self.cents < 0 else ""
        whole, part = divmod(abs(self.cents), 100)
        return f"{sign}{whole}.{part:02d}"

    def __str__(self) -> str:
        return f"${self.dollars}"
