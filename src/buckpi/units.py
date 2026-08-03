"""Physical-unit parsing backed by Pint's comprehensive unit registry."""

from __future__ import annotations

from fractions import Fraction

from pint import UnitRegistry
from pint.errors import PintError

BASE_DIMENSIONS = ("M", "L", "T", "I", "Theta", "N", "J")
PINT_DIMENSIONS = (
    "[mass]",
    "[length]",
    "[time]",
    "[current]",
    "[temperature]",
    "[substance]",
    "[luminosity]",
)
ZERO = (Fraction(0),) * 7


class UnitError(ValueError):
    """Raised when a unit expression is unknown or malformed."""


_REGISTRY = UnitRegistry()


def _fraction(value) -> Fraction:
    if isinstance(value, Fraction):
        return value
    return Fraction(str(value))


def dimensions(expression: str) -> tuple[Fraction, ...]:
    """Return exact M, L, T, I, temperature, amount, luminous exponents.

    Pint accepts SI, US customary, CGS, prefixed, pluralized, and compound unit
    expressions. Only dimensionality is retained; conversion factors do not
    enter the Buckingham Pi calculation.
    """
    cleaned = expression.strip()
    if not cleaned:
        raise UnitError("A unit expression is required")
    try:
        dimensionality = _REGISTRY.parse_units(cleaned).dimensionality
    except (PintError, ValueError, TypeError, AttributeError) as exc:
        raise UnitError(f"Invalid or unknown unit expression '{expression}'") from exc

    values = {str(dimension): _fraction(power) for dimension, power in dimensionality.items()}
    unexpected = sorted(set(values) - set(PINT_DIMENSIONS))
    if unexpected:
        raise UnitError(f"Unsupported fundamental dimension {unexpected[0]}")
    return tuple(values.get(dimension, Fraction(0)) for dimension in PINT_DIMENSIONS)
