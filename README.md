# Gentle Cover

One Home Assistant curtain per room that **opens and closes along a curve you
draw** — a slow sunrise for waking up, instead of curtains that go from dark to
dazzling in ten seconds.

Most curtain motors have one speed. "Slowly" can only mean a few short moves
with pauses between them, and done naively that looks like a motor that cannot
make up its mind. Gentle Cover plans each move once, before the first command,
and sends a handful of deliberate steps along your curve: small ones while the
room is still dark, bigger ones once your eyes have caught up.

The real curtains keep working as before for normal, fast movement. The gentle
curtain is an extra `cover` entity per room that drives them.

## Installing

Add this repository to HACS as a custom repository of type **Integration**,
download it, and restart Home Assistant. Then **Settings → Devices & Services →
Add Integration → Gentle Cover**, once per room: give the room a name and pick
its curtains. "Bedroom Curtains" with a left and a right curtain becomes
`cover.bedroom_curtains_gentle`, which moves both together.

The curtains must report and accept a position (`current_position` and
`cover.set_cover_position`).

## Drawing the movement

Everything else happens on the **Gentle Cover** page in the sidebar (admins
only). Each room has an **Opening** and a **Closing** curve: time across, how
open the curtains are up the side.

- Drag a point; tap the line to add one; select a point and **Remove point**,
  or use the arrow keys and Delete.
- **Presets**: *Slow start*, *Even*, and *Hold then open* — 10 % straight away,
  held for a while, then opening.
- A curve never goes backwards, and between its points it is smooth without
  ever bulging past them, so a hold stays perfectly level.
- **Duration** is for a full opening or closing; **step interval** is how often
  a command may be sent (default 2.5 minutes); **smallest move** combines
  steps smaller than it, because tiny moves are what these motors do worst.
- The dashed staircase on the chart is what the curtains will actually be
  told, worked out by the same planner that runs the move. The line under the
  chart says how many commands that is and when the last one goes.
- **Test opening** and **Test closing** run the move on the real curtains.

The *Configure* button on the integration only points to this page; a room is
never edited in two places.

## How a move behaves

- **Open, close, set position, stop** work as on any cover — from the
  dashboard, from automations, from HomeKit and Siri.
- A move that does not start at the end of the curve plays **the rest of it**:
  from 60 % an opening picks up where the curve reaches 60 %, at the same pace.
  Starting inside a hold skips the hold.
- Each command is sent when the curve gets to its position, never before;
  only the first goes out at once, so you can see the move has started.
- A new command replaces the running move. **Stop** ends it; the curtains
  finish their current short run.
- **Hands off**: if anyone moves a real curtain during a gentle move — from
  Home Assistant, HomeKit, a voice command for the room, the curtain's own
  button or the vendor app — the gentle move stops instead of fighting them.
- A restart of Home Assistant ends a move where it was; nothing is resumed.

To use a different duration for one move, call the action:

```yaml
action: gentle_cover.move
target:
  entity_id: cover.bedroom_curtains_gentle
data:
  position: 100
  duration: 30   # minutes for a full travel; optional
```

## Dashboard card

```yaml
type: custom:gentle-cover-card
entity: cover.bedroom_curtains_gentle
```

It draws the room's curve and current position, and during a move a marker
travelling along the curve with the time left. It is read-only; it is also in
the card picker.

## Known limitations

- Changing a room's settings while a move is running ends that move.
- An automation or scene that commands the real curtains during a gentle move
  stops it, by design (see *Hands off*).
- Starting just below a hold, the first step can go past the held level.
- The page and card files are cached by browsers; after an update, reload the
  page if it still looks old.

## Licence

MIT. The Barlow and Roboto Mono fonts in `custom_components/gentle_cover/frontend/fonts`
are under the SIL Open Font License (`OFL.txt` there).
