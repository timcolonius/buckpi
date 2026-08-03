"""Small SI-oriented unit-expression parser used by BuckPi.

The parser deliberately represents dimensions, not conversion factors. Thus
``cm`` and ``m`` are equivalent inputs for dimensional analysis.
"""

from __future__ import annotations

import ast
from fractions import Fraction

BASE_DIMENSIONS = ("M", "L", "T", "I", "Theta", "N", "J")
ZERO = (Fraction(0),) * 7


class UnitError(ValueError):
    """Raised when a unit expression is unknown or malformed."""


def _d(*values: int) -> tuple[Fraction, ...]:
    return tuple(Fraction(value) for value in values)


_UNITS = {
    "1": ZERO,
    "dimensionless": ZERO,
    "s": _d(0, 0, 1, 0, 0, 0, 0),
    "sec": _d(0, 0, 1, 0, 0, 0, 0),
    "second": _d(0, 0, 1, 0, 0, 0, 0),
    "seconds": _d(0, 0, 1, 0, 0, 0, 0),
    "min": _d(0, 0, 1, 0, 0, 0, 0),
    "h": _d(0, 0, 1, 0, 0, 0, 0),
    "m": _d(0, 1, 0, 0, 0, 0, 0),
    "meter": _d(0, 1, 0, 0, 0, 0, 0),
    "meters": _d(0, 1, 0, 0, 0, 0, 0),
    "metre": _d(0, 1, 0, 0, 0, 0, 0),
    "metres": _d(0, 1, 0, 0, 0, 0, 0),
    "cm": _d(0, 1, 0, 0, 0, 0, 0),
    "mm": _d(0, 1, 0, 0, 0, 0, 0),
    "km": _d(0, 1, 0, 0, 0, 0, 0),
    "ft": _d(0, 1, 0, 0, 0, 0, 0),
    "in": _d(0, 1, 0, 0, 0, 0, 0),
    "kg": _d(1, 0, 0, 0, 0, 0, 0),
    "kilogram": _d(1, 0, 0, 0, 0, 0, 0),
    "kilograms": _d(1, 0, 0, 0, 0, 0, 0),
    "g": _d(1, 0, 0, 0, 0, 0, 0),
    "lb": _d(1, 0, 0, 0, 0, 0, 0),
    "a": _d(0, 0, 0, 1, 0, 0, 0),
    "ampere": _d(0, 0, 0, 1, 0, 0, 0),
    "amperes": _d(0, 0, 0, 1, 0, 0, 0),
    "k": _d(0, 0, 0, 0, 1, 0, 0),
    "kelvin": _d(0, 0, 0, 0, 1, 0, 0),
    "kelvins": _d(0, 0, 0, 0, 1, 0, 0),
    "mol": _d(0, 0, 0, 0, 0, 1, 0),
    "mole": _d(0, 0, 0, 0, 0, 1, 0),
    "moles": _d(0, 0, 0, 0, 0, 1, 0),
    "cd": _d(0, 0, 0, 0, 0, 0, 1),
    "candela": _d(0, 0, 0, 0, 0, 0, 1),
    "candelas": _d(0, 0, 0, 0, 0, 0, 1),
    "hz": _d(0, 0, -1, 0, 0, 0, 0),
    "n": _d(1, 1, -2, 0, 0, 0, 0),
    "newton": _d(1, 1, -2, 0, 0, 0, 0),
    "newtons": _d(1, 1, -2, 0, 0, 0, 0),
    "pa": _d(1, -1, -2, 0, 0, 0, 0),
    "pascal": _d(1, -1, -2, 0, 0, 0, 0),
    "pascals": _d(1, -1, -2, 0, 0, 0, 0),
    "j": _d(1, 2, -2, 0, 0, 0, 0),
    "joule": _d(1, 2, -2, 0, 0, 0, 0),
    "joules": _d(1, 2, -2, 0, 0, 0, 0),
    "w": _d(1, 2, -3, 0, 0, 0, 0),
    "watt": _d(1, 2, -3, 0, 0, 0, 0),
    "watts": _d(1, 2, -3, 0, 0, 0, 0),
    "c": _d(0, 0, 1, 1, 0, 0, 0),
    "v": _d(1, 2, -3, -1, 0, 0, 0),
    "ohm": _d(1, 2, -3, -2, 0, 0, 0),
}


def _combine(left, right, sign=1):
    return tuple(a + sign * b for a, b in zip(left, right))


def _evaluate(node: ast.AST) -> tuple[Fraction, ...]:
    if isinstance(node, ast.Name):
        try:
            return _UNITS[node.id.lower()]
        except KeyError as exc:
            raise UnitError(f"Unknown unit '{node.id}'") from exc
    if isinstance(node, ast.Constant) and node.value == 1:
        return ZERO
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
        return _combine(_evaluate(node.left), _evaluate(node.right))
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        return _combine(_evaluate(node.left), _evaluate(node.right), -1)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow):
        base = _evaluate(node.left)
        exponent = _number(node.right)
        return tuple(value * exponent for value in base)
    raise UnitError("Use unit names with *, /, parentheses, and numeric powers")


def _number(node: ast.AST) -> Fraction:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return Fraction(str(node.value))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_number(node.operand)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        return _number(node.left) / _number(node.right)
    raise UnitError("Unit powers must be numbers")


def dimensions(expression: str) -> tuple[Fraction, ...]:
    """Return M, L, T, I, temperature, amount, luminous exponents."""
    cleaned = expression.strip().replace("^", "**")
    if not cleaned:
        raise UnitError("A unit expression is required")
    try:
        tree = ast.parse(cleaned, mode="eval")
    except SyntaxError as exc:
        raise UnitError(f"Invalid unit expression '{expression}'") from exc
    return _evaluate(tree.body)

