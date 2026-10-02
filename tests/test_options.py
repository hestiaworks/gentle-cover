import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pkg import load  # noqa: E402

options = load("options")
curve = load("curve")
PRESETS, OPEN, CLOSE = curve.PRESETS, curve.OPEN, curve.CLOSE


class OptionsTest(unittest.TestCase):
    def test_defaults(self):
        d = options.defaults()
        self.assertEqual(d["open_curve"], PRESETS[OPEN]["slow_start"])
        self.assertEqual(d["close_curve"], PRESETS[CLOSE]["even"])
        self.assertEqual(
            (d["open_duration"], d["close_duration"], d["step_interval"], d["min_step"]),
            (20, 10, 150, 5),
        )
        d["open_curve"].append([2, 2])
        self.assertEqual(options.defaults()["open_curve"], PRESETS[OPEN]["slow_start"])

    def test_migrate_easings_to_curves(self):
        old = {"close_duration": 4.0, "close_easing": "slow_start", "min_step": 5.0,
               "open_duration": 20.0, "open_easing": "slow_start"}
        self.assertEqual(options.migrate_options(old), {
            "open_duration": 20.0, "close_duration": 4.0, "min_step": 5.0,
            "step_interval": 150,
            "open_curve": PRESETS[OPEN]["slow_start"],
            "close_curve": PRESETS[CLOSE]["slow_start"],
        })

    def test_migrate_even_and_missing(self):
        new = options.migrate_options({"open_easing": "even"})
        self.assertEqual(new["open_curve"], PRESETS[OPEN]["even"])
        self.assertEqual(new["close_curve"], PRESETS[CLOSE]["even"])
        self.assertEqual(new["open_duration"], 20)

    def test_validate_options_accepts_and_normalises(self):
        data = options.defaults()
        data["open_duration"] = "15"
        self.assertEqual(options.validate_options(data)["open_duration"], 15.0)

    def test_validate_options_rejects_backwards_curve(self):
        data = options.defaults()
        data["open_curve"] = [[0, 0], [0.5, 60], [0.7, 40], [1, 100]]
        with self.assertRaises(ValueError):
            options.validate_options(data)

    def test_validate_options_rejects_out_of_range(self):
        for key, value in (("open_duration", 0), ("step_interval", 10), ("min_step", 80)):
            data = options.defaults()
            data[key] = value
            with self.assertRaises(ValueError, msg=key):
                options.validate_options(data)


if __name__ == "__main__":
    unittest.main()
