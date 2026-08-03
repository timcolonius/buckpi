import unittest
from fractions import Fraction

from buckpi import (
    SymbolError, UnitError, analyze, analyze_options, dimensions, symbol_html,
    symbol_latex,
)


class BuckPiTests(unittest.TestCase):
    def test_derived_units(self):
        self.assertEqual(dimensions("N/m"), dimensions("kg/s^2"))
        self.assertEqual(dimensions("Pa*s"), dimensions("kg/(m*s)"))

    def test_pendulum(self):
        result = analyze([("T", "s"), ("L", "m"), ("g", "m/s^2")])
        self.assertEqual(result.group_count, 1)
        self.assertEqual(result.groups[0].exponents, (Fraction(2), Fraction(-1), Fraction(1)))

    def test_pendulum_lists_all_admissible_forms(self):
        options = analyze_options([("T", "s"), ("L", "m"), ("g", "m/s^2")])
        self.assertEqual(len(options), 3)
        target_exponents = []
        for option in options:
            target = next(i for i, name in enumerate(option.names) if name not in option.repeating_variables)
            target_exponents.append(option.groups[0].exponents[target])
        self.assertEqual(target_exponents, [1, 1, 1])

    def test_unit_power_filter(self):
        options = analyze_options(
            [("T", "s"), ("L", "m"), ("g", "m/s^2")], unit_power=["T"]
        )
        self.assertEqual(len(options), 1)
        self.assertEqual(options[0].groups[0].exponents[0], 1)

    def test_sphere(self):
        result = analyze([("V", "m^3"), ("R", "m")], repeating=["R"])
        self.assertEqual(result.groups[0].exponents, (Fraction(1), Fraction(-3)))

    def test_requested_repeating_variable(self):
        result = analyze([("T", "s"), ("L", "m"), ("g", "m/s^2")], repeating=["g"])
        self.assertIn("g", result.repeating_variables)

    def test_surface_gravity_waves(self):
        variables = [
            ("c_p", "m/s"), ("lambda", "m"), ("g", "m/s^2"),
            ("h", "m"), ("rho", "kg/m^3"), ("sigma", "N/m"),
        ]
        result = analyze(variables)
        self.assertEqual(result.rank, 3)
        self.assertEqual(result.group_count, 3)
        self.assertEqual(len(analyze_options(variables)), 14)

    def test_unknown_unit(self):
        with self.assertRaises(UnitError):
            dimensions("furlong/fortnight")

    def test_latex_style_symbols(self):
        self.assertEqual(symbol_html(r"\rho"), "ρ")
        self.assertEqual(symbol_html(r"U_{\infty}"), "U<sub>∞</sub>")
        self.assertEqual(symbol_html(r"c_p"), "c<sub>p</sub>")
        self.assertEqual(symbol_html(r"\Delta p"), "Δ p")
        self.assertEqual(symbol_latex(r"U_{\infty}"), r"U_{\infty}")
        self.assertEqual(symbol_latex("ρ"), r"\rho ")

    def test_group_latex(self):
        result = analyze([(r"\rho", "kg/m^3"), (r"U_\infty", "m/s"), ("p", "Pa")])
        rendered = result.groups[0].expression_latex(list(result.names))
        self.assertIn(r"\frac", rendered)
        self.assertIn(r"\rho", rendered)

    def test_unsupported_symbol_command(self):
        with self.assertRaises(SymbolError):
            symbol_html(r"\notacommand")


if __name__ == "__main__":
    unittest.main()
