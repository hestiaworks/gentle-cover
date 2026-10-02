"""Move runner tests against the Home Assistant stand-in in ha_stub.py."""

import asyncio
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ha_stub import FakeHass, HomeAssistantError, load_mover  # noqa: E402
from pkg import load  # noqa: E402

mover = load_mover()
curve = load("curve")

LEFT = "cover.bedroom_curtains_left"
RIGHT = "cover.bedroom_curtains_right"


async def settle() -> None:
    for _ in range(5):
        await asyncio.sleep(0)


class MoveTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.hass = FakeHass({LEFT: 0, RIGHT: 0})
        self.events: list = []

    def make_move(self, covers=(LEFT, RIGHT), target=100):
        return mover.GentleMove(
            self.hass, list(covers), target,
            curve.Curve(curve.PRESETS["open"]["even"], "open"), 1200, 5, 150,
            lambda move, reason: self.events.append(("end", reason)),
        )

    async def asyncTearDown(self):
        for task in self.hass.tasks:
            task.cancel()
        await settle()

    async def test_failed_first_command_ends_after_start_returns(self):
        self.hass.services.raises = HomeAssistantError("broker down")
        started = self.make_move().start()
        self.events.append(("started", started))
        await settle()
        self.assertEqual(self.events, [("started", True), ("end", "failed")])

    async def test_unexpected_exception_ends_move_and_unsubscribes(self):
        self.hass.services.raises = ValueError("bad data")
        self.make_move().start()
        await settle()
        self.assertEqual(self.events, [("end", "failed")])
        self.assertEqual(self.hass.bus.listeners, [])
        self.assertEqual(self.hass.state_listeners, [])

    async def test_own_commands_do_not_interrupt(self):
        self.make_move().start()
        await settle()
        self.assertEqual(len(self.hass.services.calls), 1)
        self.assertEqual(self.events, [])

    async def test_area_command_interrupts(self):
        self.hass.areas = {"bedroom": [LEFT, RIGHT]}
        self.make_move().start()
        await settle()
        self.hass.bus.fire(
            "call_service",
            {"domain": "cover", "service": "close_cover", "service_data": {"area_id": "bedroom"}},
        )
        self.assertEqual(self.events, [("end", "interrupted")])

    async def test_all_and_comma_separated_targets_interrupt(self):
        for entity_id in ("all", f"cover.other, {LEFT}"):
            self.events.clear()
            self.make_move().start()
            await settle()
            self.hass.bus.fire(
                "call_service",
                {"domain": "cover", "service": "stop_cover",
                 "service_data": {"entity_id": entity_id}},
            )
            self.assertEqual(self.events, [("end", "interrupted")], entity_id)

    async def test_stale_report_of_old_position_does_not_interrupt(self):
        mover.SETTLE_GRACE_S = 0
        try:
            self.make_move(covers=(LEFT,)).start()
            await settle()
            # Sent 12 from 0; a late re-publish of the old position is not a person.
            self.hass.set_position(LEFT, 0)
            self.assertEqual(self.events, [])
            # Far past what was sent: someone opened it.
            self.hass.set_position(LEFT, 60)
            self.assertEqual(self.events, [("end", "interrupted")])
        finally:
            mover.SETTLE_GRACE_S = 30.0


if __name__ == "__main__":
    unittest.main()
