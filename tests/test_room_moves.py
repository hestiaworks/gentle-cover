import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pkg import load  # noqa: E402

RoomMoves = load("room_moves").RoomMoves


class RoomMovesTest(unittest.TestCase):
    def setUp(self):
        self.moves = RoomMoves()
        self.cancelled = []

    def claim(self, owner, covers):
        self.moves.claim(owner, covers, lambda: self.cancelled.append(owner))

    def test_a_new_move_stops_older_ones_on_the_same_curtains(self):
        self.claim("room", ["left", "right"])
        self.claim("left", ["left"])
        self.assertEqual(self.cancelled, ["room"])

    def test_moves_on_other_curtains_are_left_alone(self):
        self.claim("left", ["left"])
        self.claim("right", ["right"])
        self.assertEqual(self.cancelled, [])

    def test_a_released_move_is_not_stopped_later(self):
        self.claim("room", ["left", "right"])
        self.moves.release("room")
        self.claim("left", ["left"])
        self.assertEqual(self.cancelled, [])

    def test_the_same_owner_claiming_again_does_not_stop_itself(self):
        self.claim("room", ["left"])
        self.claim("room", ["left", "right"])
        self.assertEqual(self.cancelled, [])

    def test_a_stopped_move_is_forgotten(self):
        self.claim("room", ["left", "right"])
        self.claim("left", ["left"])
        self.claim("right", ["right"])
        self.assertEqual(self.cancelled, ["room"])


if __name__ == "__main__":
    unittest.main()
