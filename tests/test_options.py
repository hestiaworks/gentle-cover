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
        d = options.defaults("Room", ["cover.a"])
        self.assertEqual(d["open_curve"], PRESETS[OPEN]["slow_start"])
        self.assertEqual(d["close_curve"], PRESETS[CLOSE]["even"])
        self.assertEqual(
            (d["open_duration"], d["close_duration"], d["step_interval"], d["min_step"]),
            (20, 10, 150, 5),
        )
        d["open_curve"].append([2, 2])
        self.assertEqual(options.defaults("Room", ["cover.a"])["open_curve"], PRESETS[OPEN]["slow_start"])

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
        data = options.defaults("Room", ["cover.a"])
        data["open_duration"] = "15"
        self.assertEqual(options.validate_options(data, ["cover.a"])["open_duration"], 15.0)

    def test_validate_options_rejects_backwards_curve(self):
        data = options.defaults("Room", ["cover.a"])
        data["open_curve"] = [[0, 0], [0.5, 60], [0.7, 40], [1, 100]]
        with self.assertRaises(ValueError):
            options.validate_options(data, ["cover.a"])

    def test_validate_options_rejects_out_of_range(self):
        for key, value in (("open_duration", 0), ("step_interval", 10), ("min_step", 80)):
            data = options.defaults("Room", ["cover.a"])
            data[key] = value
            with self.assertRaises(ValueError, msg=key):
                options.validate_options(data, ["cover.a"])

    def test_defaults_name_both_curtains(self):
        d = options.defaults("Bedroom", ["cover.a"])
        self.assertEqual(
            (d["normal_enabled"], d["normal_name"], d["gentle_enabled"], d["gentle_name"], d["scale"]),
            (True, "", True, "Sunrise", "open_is_100"),
        )

    def test_migrate_room_settings(self):
        old = options.migrate_options({"open_easing": "slow_start"})
        new = options.migrate_room_settings(old, "Living Room")
        self.assertEqual(
            (new["normal_enabled"], new["normal_name"], new["gentle_enabled"], new["gentle_name"], new["scale"]),
            (False, "", True, "Gentle", "open_is_100"),
        )
        self.assertEqual(new["open_curve"], old["open_curve"])

    def test_validate_room_settings(self):
        data = options.defaults("Bedroom", ["cover.a"])
        data["gentle_name"] = "  Sunrise  "
        self.assertEqual(options.validate_options(data, ["cover.a"])["gentle_name"], "Sunrise")
        for key, value in (("normal_name", "x" * 65), ("scale", "upside_down"),
                           ("normal_enabled", "yes"), ("gentle_name", 7)):
            bad = options.defaults("Bedroom", ["cover.a"])
            bad[key] = value
            with self.assertRaises(ValueError, msg=key):
                options.validate_options(bad, ["cover.a"])
        # Names follow the room's name, so an empty one is just the room.
        blank = options.defaults("Bedroom", ["cover.a"])
        blank["gentle_name"] = "  "
        blank["normal_name"] = "Curtains"
        self.assertEqual(options.validate_options(blank, ["cover.a"])["gentle_name"], "")
        for normal, gentle in (("", ""), ("Sunrise", "sunrise ")):
            same = options.defaults("Bedroom", ["cover.a"])
            same["normal_name"], same["gentle_name"] = normal, gentle
            with self.assertRaises(ValueError, msg=(normal, gentle)):
                options.validate_options(same, ["cover.a"])
        neither = options.defaults("Bedroom", ["cover.a"])
        neither["normal_enabled"] = neither["gentle_enabled"] = False
        with self.assertRaises(ValueError):
            options.validate_options(neither, ["cover.a"])

    def test_validate_covers(self):
        kinds = {"cover.a": "ok", "cover.b": "ok", "cover.gone": "missing",
                 "cover.fixed": "no_position", "cover.mine": "ours"}
        describe = kinds.__getitem__
        self.assertEqual(options.validate_covers(["cover.a", "cover.b"], describe), ["cover.a", "cover.b"])
        for covers in ([], ["cover.gone"], ["cover.a", "cover.fixed"], ["cover.mine"], "cover.a"):
            with self.assertRaises(ValueError, msg=covers):
                options.validate_covers(covers, describe)

    def test_validate_title(self):
        self.assertEqual(options.validate_title("  Office ", {"bedroom"}), "Office")
        for title in ("", "   ", "Bedroom", "BEDROOM ", "x" * 65):
            with self.assertRaises(ValueError, msg=title):
                options.validate_title(title, {"bedroom"})

    def test_scale_round_trip(self):
        for scale in ("open_is_100", "closed_is_100"):
            for p in (0, 7, 50, 100):
                self.assertEqual(options.from_room_scale(options.to_room_scale(p, scale), scale), p)
        self.assertEqual(options.to_room_scale(30, "closed_is_100"), 70)
        self.assertEqual(options.to_room_scale(30, "open_is_100"), 30)

    def test_defaults_tick_every_curtain(self):
        d = options.defaults("Bedroom", ["cover.l", "cover.r"])
        self.assertEqual((d["normal_covers"], d["gentle_covers"], d["individual"]),
                         (["cover.l", "cover.r"], ["cover.l", "cover.r"], {}))

    def test_migrate_room_covers(self):
        old = options.migrate_room_settings(options.migrate_options({}), "Living Room")
        new = options.migrate_room_covers(old, ["cover.l", "cover.r"])
        self.assertEqual((new["normal_covers"], new["gentle_covers"], new["individual"]),
                         (["cover.l", "cover.r"], ["cover.l", "cover.r"], {}))
        self.assertEqual(new["gentle_name"], old["gentle_name"])

    def test_validate_subsets(self):
        covers = ["cover.l", "cover.r"]
        good = options.defaults("Bedroom", covers)
        good["gentle_covers"] = ["cover.r", "cover.l"]
        self.assertEqual(options.validate_options(good, covers)["gentle_covers"], ["cover.l", "cover.r"])
        for key, value in (("gentle_covers", ["cover.x"]), ("normal_covers", ["cover.l", "cover.l"]),
                           ("gentle_covers", []), ("normal_covers", "cover.l")):
            bad = options.defaults("Bedroom", covers)
            bad[key] = value
            with self.assertRaises(ValueError, msg=(key, value)):
                options.validate_options(bad, covers)
        off = options.defaults("Bedroom", covers)
        off["gentle_enabled"], off["gentle_covers"] = False, []
        self.assertEqual(options.validate_options(off, covers)["gentle_covers"], [])

    def test_validate_own_curtains(self):
        covers = ["cover.l", "cover.r"]
        data = options.defaults("Bedroom", covers)
        data["individual"] = {"cover.r": {"enabled": True, "name": " Right "}, "cover.l": {"enabled": False, "name": "Left"}}
        result = options.validate_options(data, covers)
        self.assertEqual(result["individual"]["cover.r"], {"enabled": True, "name": "Right"})
        for individual in ({"cover.x": {"enabled": True, "name": "X"}},
                           {"cover.r": {"enabled": "yes", "name": "R"}},
                           {"cover.r": {"enabled": True, "name": "x" * 65}},
                           {"cover.r": "Right"}):
            bad = options.defaults("Bedroom", covers)
            bad["individual"] = individual
            with self.assertRaises(ValueError, msg=individual):
                options.validate_options(bad, covers)

    def test_names_must_differ_across_all_curtains(self):
        covers = ["cover.l", "cover.r"]
        data = options.defaults("Bedroom", covers)
        data["individual"] = {"cover.r": {"enabled": True, "name": ""}}
        with self.assertRaises(ValueError):
            options.validate_options(data, covers)
        data["individual"] = {"cover.r": {"enabled": True, "name": "sunrise"}}
        with self.assertRaises(ValueError):
            options.validate_options(data, covers)
        data["individual"] = {"cover.r": {"enabled": False, "name": ""}}
        options.validate_options(data, covers)

    def test_a_room_of_only_own_curtains_is_fine(self):
        covers = ["cover.l"]
        data = options.defaults("Bedroom", covers)
        data["normal_enabled"] = data["gentle_enabled"] = False
        data["individual"] = {"cover.l": {"enabled": True, "name": "Left"}}
        options.validate_options(data, covers)
        data["individual"]["cover.l"]["enabled"] = False
        with self.assertRaises(ValueError):
            options.validate_options(data, covers)

    def test_default_own_name(self):
        self.assertEqual(options.default_own_name("Bedroom Curtains Right", "Bedroom"), "Curtains Right")
        self.assertEqual(options.default_own_name("bedroom left", "Bedroom"), "left")
        self.assertEqual(options.default_own_name("Office Blind", "Bedroom"), "Office Blind")
        self.assertEqual(options.default_own_name("Bedroom", "Bedroom"), "Bedroom")


if __name__ == "__main__":
    unittest.main()
