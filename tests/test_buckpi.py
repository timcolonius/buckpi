import unittest
from fractions import Fraction

from buckpi import UnitError, analyze, dimensions


class BuckPiTests(unittest.TestCase):
    def test_derived_units(self):
        self.assertEqual(dimensions("N/m"), dimensions("kg/s^2"))
        self.assertEqual(dimensions("Pa*s"), dimensions("kg/(m*s)"))

    def test_pendulum(self):
        result = analyze([("T", "s"), ("L", "m"), ("g", "m/s^2")])
        self.assertEqual(result.group_count, 1)
        self.assertEqual(result.groups[0].exponents, (Fraction(2), Fraction(-1), Fraction(1)))

    def test_sphere(self):
        result = analyze([("V", "m^3"), ("R", "m")], repeating=["R"])
        self.assertEqual(result.groups[0].exponents, (Fraction(1), Fraction(-3)))

    def test_requested_repeating_variable(self):
        result = analyze([("T", "s"), ("L", "m"), ("g", "m/s^2")], repeating=["g"])
        self.assertIn("g", result.repeating_variables)

    def test_surface_gravity_waves(self):
        result = analyze([
            ("c_p", "m/s"), ("lambda", "m"), ("g", "m/s^2"),
            ("h", "m"), ("rho", "kg/m^3"), ("sigma", "N/m"),
        ])
        self.assertEqual(result.rank, 3)
        self.assertEqual(result.group_count, 3)

    def test_unknown_unit(self):
        with self.assertRaises(UnitError):
            dimensions("furlong/fortnight")


if __name__ == "__main__":
    unittest.main()
