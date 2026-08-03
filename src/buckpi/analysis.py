"""Exact Buckingham Pi analysis."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations
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


def analyze_options(variables, unit_power=None) -> tuple[AnalysisResult, ...]:
    """Find every admissible tabular representation of the Pi groups.

    ``variables`` is an iterable of ``(name, unit_expression)`` pairs.
    ``unit_power`` may contain variable names required to occur to the first
    power in separate groups, corresponding to ``nonrep`` in ``Buck.nb``.
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
        return (AnalysisResult(tuple(names), rank, groups, ()),)

    requested = list(unit_power or [])
    unknown = [name for name in requested if name not in names]
    if unknown:
        raise ValueError(f"Unknown unit-power variable: {unknown[0]}")
    group_count = len(names) - rank
    if len(requested) > group_count:
        raise ValueError(f"Choose at most {group_count} unit-power variables")

    requested_indices = {names.index(name) for name in requested}
    options = []
    for repeat_tuple in combinations(range(len(names)), rank):
        repeat_indices = list(repeat_tuple)
        targets = [index for index in range(len(names)) if index not in repeat_indices]
        if not requested_indices.issubset(targets):
            continue
        repeat_matrix = [[matrix[row][col] for col in repeat_indices] for row in range(7)]
        if _rank(repeat_matrix) != rank:
            continue
        active_rows = _rref([[matrix[row][col] for row in range(7)] for col in repeat_indices])[1]
        square = [[matrix[row][col] for col in repeat_indices] for row in active_rows]
        groups = []
        for target in targets:
            rhs = [-matrix[row][target] for row in active_rows]
            powers = _solve(square, rhs)
            exponents = [Fraction(0)] * len(names)
            for index, power in zip(repeat_indices, powers):
                exponents[index] = power
            exponents[target] = 1
            groups.append(PiGroup(tuple(exponents)))
        options.append(
            AnalysisResult(
                tuple(names), rank, tuple(groups), tuple(names[i] for i in repeat_indices)
            )
        )
    if not options:
        raise ValueError("No independent Pi-group set satisfies the requested unit-power variables")
    return tuple(options)


def analyze(variables, repeating=None) -> AnalysisResult:
    """Return the first admissible representation (compatibility helper).

    For the complete ``Buck.nb``-style table, use :func:`analyze_options`.
    The legacy ``repeating`` argument still selects actual repeating variables.
    """
    if repeating:
        pairs = list(variables)
        repeating = list(repeating)
        options = analyze_options(pairs)
        for option in options:
            if set(repeating).issubset(option.repeating_variables):
                return option
        raise ValueError("The requested variables cannot form an independent repeating set")
    return analyze_options(variables)[0]
