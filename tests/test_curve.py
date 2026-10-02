import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pkg import load  # noqa: E402

curve = load("curve")
OPEN, CLOSE, PRESETS, Curve = curve.OPEN, curve.CLOSE, curve.PRESETS, curve.Curve


class CurveTest(unittest.TestCase):
    def test_passes_through_points(self):
        c = Curve(PRESETS[OPEN]["slow_start"], OPEN)
        for t, y in PRESETS[OPEN]["slow_start"]:
            self.assertAlmostEqual(c.at(t), y, places=6)

    def test_slow_start_values(self):
        c = Curve(PRESETS[OPEN]["slow_start"], OPEN)
        self.assertEqual(
            [round(c.at(t / 10), 2) for t in range(11)],
            [0.0, 1.78, 3.97, 8.78, 15.91, 25.0, 35.91, 48.78, 63.97, 81.78, 100.0],
        )

    def test_monotone_and_hold_never_dips(self):
        c = Curve(PRESETS[OPEN]["hold_then_open"], OPEN)
        values = [c.at(i / 1000) for i in range(1001)]
        self.assertTrue(all(b >= a - 1e-9 for a, b in zip(values, values[1:])))
        self.assertTrue(all(abs(c.at(t / 100) - 10) < 1e-9 for t in range(10, 41)))

    def test_closing_curve_goes_down(self):
        c = Curve(PRESETS[CLOSE]["slow_start"], CLOSE)
        values = [c.at(i / 100) for i in range(101)]
        self.assertTrue(all(b <= a + 1e-9 for a, b in zip(values, values[1:])))

    def test_last_time_at_skips_a_hold(self):
        c = Curve(PRESETS[OPEN]["hold_then_open"], OPEN)
        self.assertAlmostEqual(c.last_time_at(10), 0.4, places=4)
        self.assertAlmostEqual(c.first_time_reaching(10), 0.1, places=4)

    def test_lookup_at_ends(self):
        c = Curve(PRESETS[CLOSE]["even"], CLOSE)
        self.assertAlmostEqual(c.last_time_at(100), 0.0, places=6)
        self.assertAlmostEqual(c.first_time_reaching(0), 1.0, places=6)
        self.assertAlmostEqual(c.first_time_reaching(50), 0.5, places=6)

    def test_validate_rejects(self):
        bad = [
            [[0, 0]],                                  # too few points
            [[0, 5], [1, 100]],                        # start not 0
            [[0, 0], [0.5, 60], [0.5, 70], [1, 100]],  # time not increasing
            [[0, 0], [0.5, 60], [0.7, 40], [1, 100]],  # backwards
            [[0, 0], [0.5, 120], [1, 100]],            # out of range
        ]
        for points in bad:
            with self.assertRaises(ValueError, msg=points):
                curve.validate_curve(points, OPEN)
        with self.assertRaises(ValueError):
            curve.validate_curve(PRESETS[OPEN]["even"], CLOSE)


if __name__ == "__main__":
    unittest.main()
