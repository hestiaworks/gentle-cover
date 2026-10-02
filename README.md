# Gentle Cover

One Home Assistant curtain per room that **opens and closes along a curve you
draw** — a slow sunrise for waking up, instead of curtains that go from dark to
dazzling in ten seconds.

Most curtain motors have one speed. "Slowly" can only mean a few short moves
with pauses between them, and done naively that looks like a motor that cannot
make up its mind. Gentle Cover plans each move once, before the first command,
and sends a handful of deliberate steps along your curve: small ones while the
room is still dark, bigger ones once your eyes have caught up.

Each room can have two curtains, both named by you and both optional:

- a **normal** curtain that moves straight to where it is sent, all the room's
  curtains in one command;
- a **gentle** curtain that moves along the room's curves.

Together they can replace the room's individual curtains on your dashboards,
in automations and in HomeKit.

## Installing

Add this repository to HACS as a custom repository of type **Integration**,
download it, and restart Home Assistant. Then **Settings → Devices & Services →
Add Integration → Gentle Cover**, once per room: give the room a name and pick
its curtains. A room called "Bedroom" gets a normal curtain "Bedroom" and a
gentle curtain "Bedroom Sunrise"; rename or switch either off on the page.

Curtain names come after the room's name, the way Home Assistant shows every
device's entities: the gentle curtain's name "Sunrise" shows as "Bedroom
Sunrise", and an empty name shows as just "Bedroom". Renaming the room renames
its curtains with it.

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

The **Room** tab holds the rest: the room's name, its curtains, which of the
normal and gentle curtains exist and what they are called (the page shows the
full name each will get), and the **scale**
— *100 % = open* (Home Assistant's way) or *100 % = closed*. The scale is how
this page, the card and the `gentle_cover.move` action count; Home Assistant
and HomeKit always use 100 % = open, because that is what their sliders and
buttons expect.

It also shows the lines to add under `homekit: filter: include_entities:` for
the room's curtains. The Home app removes the room's name from the start of an
accessory's name, so "Bedroom Sunrise" placed in the Bedroom shows as
"Sunrise".

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

The normal curtain is an ordinary cover. A command on it during a gentle move
stops the gentle move, like any other hands-off.

To use a different duration for one gentle move, call the action (`position`
in the room's scale):

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

It takes either of a room's curtains and draws the room's curve and current
position in the room's scale, and during a gentle move a marker travelling
along the curve with the time left. It is read-only; it is also in the card
picker.

## Upgrading from 0.2

Existing rooms keep their gentle curtain exactly as it was — same entity id,
same name — and get a normal curtain that starts switched off. Switch it on
in the Room tab when you want it.

## Known limitations

- Changing a room's settings while a move is running ends that move.
- An automation or scene that commands the real curtains during a gentle move
  stops it, by design (see *Hands off*).
- The page and card files are cached by browsers; after an update, reload the
  page if it still looks old.

## Licence

MIT. The Barlow and Roboto Mono fonts in `custom_components/gentle_cover/frontend/fonts`
are under the SIL Open Font License (`OFL.txt` there).
