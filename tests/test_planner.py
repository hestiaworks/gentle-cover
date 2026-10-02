"""Planner tests. Run: python3 -m unittest discover -s tests -v"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pkg import load  # noqa: E402

planner = load("planner")
curve = load("curve")
plan, preview, off_course = planner.plan, planner.preview, planner.off_course
OPEN, CLOSE, PRESETS = curve.OPEN, curve.CLOSE, curve.PRESETS


def make(direction, name):
    return curve.Curve(PRESETS[direction][name], direction)


class PlanTest(unittest.TestCase):
    def test_zero_distance(self):
        self.assertEqual(plan(40, 40, make(OPEN, "even"), 1200, 5).steps, [])
        self.assertEqual(plan(40.3, 39.8, make(OPEN, "even"), 1200, 5).steps, [])

    def test_slow_start_full_open(self):
        self.assertEqual(
            plan(0, 100, make(OPEN, "slow_start"), 1200, 5).steps,
            [(0.0, 6), (450.0, 14), (600.0, 25), (750.0, 39),
             (900.0, 56), (1050.0, 77), (1200.0, 100)],
        )

    def test_even_close(self):
        self.assertEqual(
            plan(100, 0, make(CLOSE, "even"), 600, 5).steps,
            [(0.0, 75), (300.0, 50), (450.0, 25), (600.0, 0)],
        )

    def test_partial_open_plays_the_rest_of_the_curve(self):
        result = plan(60, 100, make(OPEN, "slow_start"), 1200, 5)
        self.assertEqual(result.steps, [(0.0, 80), (269.0, 100)])
        self.assertGreater(result.t_start, 0.75)

    def test_set_position_stops_where_the_curve_reaches_it(self):
        self.assertEqual(
            plan(0, 50, make(OPEN, "slow_start"), 1200, 5).steps,
            [(0.0, 5), (425.2, 12), (567.0, 22), (708.7, 35), (850.5, 50)],
        )

    def test_hold_keeps_its_length(self):
        self.assertEqual(
            plan(0, 100, make(OPEN, "hold_then_open"), 1200, 5).steps,
            [(0.0, 10), (600.0, 15), (750.0, 31), (900.0, 53), (1050.0, 78), (1200.0, 100)],
        )

    def test_starting_inside_a_hold_skips_it(self):
        self.assertEqual(
            plan(10, 100, make(OPEN, "hold_then_open"), 1200, 5).steps,
            [(0.0, 16), (288.0, 33), (432.0, 55), (576.0, 79), (720.0, 100)],
        )

    def test_tiny_distance_single_immediate_move(self):
        self.assertEqual(plan(0, 3, make(OPEN, "slow_start"), 1200, 5).steps, [(0.0, 3)])

    def test_short_interval_gives_more_steps(self):
        self.assertEqual(len(plan(0, 100, make(OPEN, "slow_start"), 240, 5).steps), 2)
        self.assertEqual(len(plan(0, 100, make(OPEN, "slow_start"), 240, 5, 30).steps), 7)

    def test_no_intermediate_step_below_min_step(self):
        for direction, name, start, target in (
            (OPEN, "slow_start", 0, 100), (OPEN, "even", 20, 65),
            (OPEN, "hold_then_open", 0, 100), (CLOSE, "slow_start", 100, 0),
            (CLOSE, "even", 90, 10),
        ):
            steps = plan(start, target, make(direction, name), 1200, 8).steps
            previous = start
            for _, position in steps[:-1]:
                self.assertGreaterEqual(abs(position - previous), 8)
                previous = position
            self.assertEqual(steps[-1][1], target)

    def test_commands_never_run_ahead_of_the_curve(self):
        for direction, name, start, target in (
            (OPEN, "slow_start", 0, 100), (OPEN, "hold_then_open", 0, 100),
            (OPEN, "even", 20, 65), (CLOSE, "slow_start", 100, 0), (CLOSE, "even", 90, 10),
        ):
            c = make(direction, name)
            sign = 1 if direction == OPEN else -1
            result = plan(start, target, c, 1200, 5)
            for at, position in result.steps[1:]:
                reached = c.at(result.t_start + at / 1200)
                self.assertGreaterEqual(sign * (reached - position), -0.5, (name, at, position))

    def test_full_travel_ends_at_the_full_duration(self):
        self.assertEqual(plan(0, 100, make(OPEN, "slow_start"), 1200, 5).steps[-1], (1200.0, 100))

    def test_first_command_waits_out_a_hold(self):
        c = make(OPEN, "hold_then_open")
        result = plan(8, 100, c, 1200, 5)
        self.assertGreater(result.steps[0][0], 0.0)
        for at, position in result.steps:
            self.assertGreaterEqual(c.at(result.t_start + at / 1200) - position, -0.5, (at, position))

    def test_first_command_still_at_once_on_a_slow_start(self):
        self.assertEqual(plan(0, 100, make(OPEN, "slow_start"), 1200, 5).steps[0], (0.0, 6))

    def test_preview_full_travel(self):
        result = preview(make(CLOSE, "even"), 600, 5, 150)
        self.assertEqual(result["steps"], [[0.0, 75], [300.0, 50], [450.0, 25], [600.0, 0]])
        self.assertEqual(len(result["samples"]), 101)
        self.assertEqual(result["samples"][50], [0.5, 50.0])
        self.assertEqual(result["span_s"], 600.0)
        self.assertEqual(result["t_start"], 0.0)

    def test_preview_starts_after_an_initial_hold(self):
        held = curve.Curve([[0, 0], [0.2, 0], [1, 100]], OPEN)
        self.assertAlmostEqual(preview(held, 1200, 5, 150)["t_start"], 0.2, places=4)


class OffCourseTest(unittest.TestCase):
    def test_on_the_way_or_arrived_is_on_course(self):
        for reported in (20, 25, 30, 38):
            self.assertFalse(off_course(20, 30, reported, 10), reported)

    def test_late_report_of_the_old_position_is_on_course(self):
        self.assertFalse(off_course(20, 30, 20, 10))
        self.assertFalse(off_course(30, 20, 30, 10))

    def test_moved_past_or_back_is_off_course(self):
        self.assertTrue(off_course(20, 30, 45, 10))
        self.assertTrue(off_course(20, 30, 5, 10))
        self.assertTrue(off_course(30, 20, 0, 10))

    def test_unknown_origin_judges_against_the_sent_position(self):
        self.assertFalse(off_course(None, 30, 38, 10))
        self.assertTrue(off_course(None, 30, 15, 10))


if __name__ == "__main__":
    unittest.main()
