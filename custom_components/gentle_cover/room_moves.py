"""Which gentle moves are running in a room, so a new one stops the others.

Several curtains of a room can move the same real curtain gently — the
gentle curtain, and the normal and own curtains by tilt. Left to the
hands-off check, two such moves would stop each other through their step
commands, and a move whose first step waits out a hold could lose to the
older one. So the newest command wins, explicitly, the moment it starts.
"""

from __future__ import annotations

from collections.abc import Callable, Hashable, Iterable


class RoomMoves:
    def __init__(self) -> None:
        self._moves: dict[Hashable, tuple[frozenset[str], Callable[[], None]]] = {}

    def claim(
        self, owner: Hashable, covers: Iterable[str], cancel: Callable[[], None]
    ) -> None:
        """owner starts a move of covers; every other move sharing one of
        them is stopped through its cancel callback and forgotten."""
        wanted = frozenset(covers)
        for other, (theirs, stop) in list(self._moves.items()):
            if other != owner and theirs & wanted:
                del self._moves[other]
                stop()
        self._moves[owner] = (wanted, cancel)

    def release(self, owner: Hashable) -> None:
        """owner's move ended or was cancelled by owner itself."""
        self._moves.pop(owner, None)
