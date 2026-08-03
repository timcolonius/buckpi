"""Exact Buckingham Pi analysis."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations
from math import gcd
from functools import reduce

from .units import dimensions


@dataclass(frozen=True)
class PiGroup:
    exponents: tuple[Fraction, ...]

    def expression(self, names: list[str]) -> str:
        numerator, denominator = [], []
        for name, power in zip(names, self.exponents):
            if not power:
                continue
            target = numerator if power > 0 else denominator
            magnitude = abs(power)
            target.append(name if magnitude == 1 else f"{name}^{_fraction_text(magnitude)}")
        top = " · ".join(numerator) or "1"
        bottom = " · ".join(denominator)
        return top if not bottom else f"{top} / ({bottom})"


@dataclass(frozen=True)
class AnalysisResult:
    names: tuple[str, ...]
    rank: int
    groups: tuple[PiGroup, ...]
    repeating_variables: tuple[str, ...]

    @property
    def group_count(self) -> int:
        return len(self.names) - self.rank


def _fraction_text(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"({value.numerator}/{value.denominator})"


def _rref(matrix):
    a = [list(map(Fraction, row)) for row in matrix]
    rows, cols = len(a), len(a[0]) if a else 0
    pivots, row = [], 0
    for col in range(cols):
        pivot = next((r for r in range(row, rows) if a[r][col]), None)
        if pivot is None:
            continue
        a[row], a[pivot] = a[pivot], a[row]
        divisor = a[row][col]
        a[row] = [value / divisor for value in a[row]]
        for r in range(rows):
            if r != row and a[r][col]:
                factor = a[r][col]
                a[r] = [x - factor * y for x, y in zip(a[r], a[row])]
        pivots.append(col)
        row += 1
        if row == rows:
            break
    return a, pivots


def _rank(matrix) -> int:
    return len(_rref(matrix)[1])


def _solve(square, rhs):
    augmented = [list(row) + [value] for row, value in zip(square, rhs)]
    reduced, pivots = _rref(augmented)
    if len(pivots) != len(square) or any(p >= len(square) for p in pivots):
        raise ValueError("Repeating variables are not dimensionally independent")
    return [reduced[i][-1] for i in range(len(square))]


def _normalize(values):
    denominators = [v.denominator for v in values if v]
    lcm = reduce(lambda a, b: a * b // gcd(a, b), denominators, 1)
    integers = [int(v * lcm) for v in values]
    common = reduce(gcd, (abs(v) for v in integers if v), 0) or 1
    integers = [v // common for v in integers]
    return tuple(Fraction(v) for v in integers)


def analyze(variables, repeating=None) -> AnalysisResult:
    """Find one set of independent Pi groups.

    ``variables`` is an iterable of ``(name, unit_expression)`` pairs.
    ``repeating`` may contain variable names that should form the repeating set.
    """
    pairs = [(str(name).strip(), str(unit).strip()) for name, unit in variables]
    if len(pairs) < 2:
        raise ValueError("Enter at least two variables")
    names = [name for name, _ in pairs]
    if any(not name for name in names) or len(set(names)) != len(names):
        raise ValueError("Variable names must be non-empty and unique")
    columns = [dimensions(unit) for _, unit in pairs]
    matrix = [[column[row] for column in columns] for row in range(7)]
    rank = _rank(matrix)
    if rank == 0:
        groups = tuple(PiGroup(tuple(Fraction(i == j) for i in range(len(names)))) for j in range(len(names)))
        return AnalysisResult(tuple(names), rank, groups, ())

    requested = list(repeating or [])
    unknown = [name for name in requested if name not in names]
    if unknown:
        raise ValueError(f"Unknown repeating variable: {unknown[0]}")
    if len(requested) > rank:
        raise ValueError(f"Choose at most {rank} repeating variables")

    requested_indices = [names.index(name) for name in requested]
    candidates = [i for i in range(len(names)) if i not in requested_indices]
    repeat_indices = None
    for extras in combinations(candidates, rank - len(requested_indices)):
        trial = requested_indices + list(extras)
        square = [[matrix[row][col] for col in trial] for row in range(7)]
        if _rank(square) == rank:
            repeat_indices = trial
            break
    if repeat_indices is None:
        raise ValueError("The requested variables cannot form an independent repeating set")

    active_rows = _rref([[matrix[row][col] for row in range(7)] for col in repeat_indices])[1]
    square = [[matrix[row][col] for col in repeat_indices] for row in active_rows]
    groups = []
    for target in range(len(names)):
        if target in repeat_indices:
            continue
        rhs = [-matrix[row][target] for row in active_rows]
        powers = _solve(square, rhs)
        exponents = [Fraction(0)] * len(names)
        for index, power in zip(repeat_indices, powers):
            exponents[index] = power
        exponents[target] = 1
        groups.append(PiGroup(_normalize(exponents)))
    return AnalysisResult(tuple(names), rank, tuple(groups), tuple(names[i] for i in repeat_indices))

