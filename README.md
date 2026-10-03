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

- a **normal** curtain that moves straight to where it is sent, all its
  curtains in one command;
- a **gentle** curtain that moves along the room's curves.

You choose which of the room's real curtains each of them moves, and any real
curtain can also be offered **on its own** as a full-speed curtain.

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

The **Room** tab holds the rest. Its curtains table says, for each real
curtain, whether the room's **normal** and **gentle** curtain move it — say
both halves for everyday use but only the window side for the sunrise — and
whether it is also offered **on its own** as a full-speed curtain, so every
curtain in the house can go through Gentle Cover. Below the table: the room's
name, which of the
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
- **Hands off**: if anyone moves one of the curtains a gentle move is driving —
  from Home Assistant, HomeKit, a voice command for the room, the curtain's
  own button or the vendor app — the gentle move stops instead of fighting
  them. Curtains the gentle curtain does not move can be used freely during it.
- A restart of Home Assistant ends a move where it was; nothing is resumed.

The normal curtain and the curtains offered on their own are ordinary covers.
A command on one of them during a gentle move stops the gentle move if it
moves one of the same real curtains, like any other hands-off.

### Gentle by tilt

Curtains don't tilt — so Gentle Cover borrows the tilt control for something
else. With **Tilt moves gently** on (Room tab), the normal curtain and the
curtains on their own get a second control:

| Control | Means | Speed |
|---|---|---|
| **Position** (slider, open / close, Siri "open …") | go to this position | full speed |
| **Tilt** | go to this position **gently**, along the room's curves | slow, in steps |

The tilt value is a position, not an angle of slats:

| Tilt in Home Assistant | Tilt angle in HomeKit | Gentle move to |
|---|---|---|
| 100 % | 90° | fully open |
| 50 % | 0° | half-way |
| 0 % | −90° | fully closed |

The tilt always shows where the curtain is, so it climbs while a gentle move
runs and settles where the curtain ends up. A position command, a stop, or
anyone moving the curtain by hand ends the gentle move.

Why this way: one curtain entity then covers both speeds. A room with two
curtains needs just two entities — *Left* and *Right* — for every combination
of left, right or both, normal or gentle, instead of a separate gentle curtain
for each.

**From Home Assistant** the tilt works everywhere: the curtain's dialog shows
a tilt slider next to the position, and automations call

```yaml
action: cover.set_cover_tilt_position
target:
  entity_id: [cover.bedroom_left, cover.bedroom_right]
data:
  tilt_position: 100   # both gently fully open
```

**From HomeKit** the curtain is one accessory with position and tilt, but
Apple's Home app only draws the position slider, and its scene and automation
editors don't offer tilt. Apps that show every HomeKit control do — **Eve** is
free. Use one of them to make **scenes** that set only the tilt:

- *Left Sunrise* — Curtains Left, tilt 90° → opens gently;
- *Left Sunset* — Curtains Left, tilt −90° → closes gently;
- *Sunrise* — both curtains, tilt 90°.

Those scenes live in HomeKit itself, so the Home app shows them as scene tiles,
Siri runs them ("Hey Siri, Left Sunrise"), and Home automations can start them
— a wake-up at 6:40, say. The curtain tiles stay for normal moves.

Good to know:

- **A scene should set either the position or the tilt, never both** — it
  would send both, and which arrives last decides what happens.
- **Tilt is always 100 % = open**, whatever the room's scale.
- **After switching *Tilt moves gently* on or off**, reload the HomeKit Bridge
  (Settings → Devices & services → HomeKit Bridge → ⋮ → Reload) or restart
  Home Assistant; HomeKit only picks up the change when the accessory is
  rebuilt.
- **The newest gentle command wins**: starting a gentle move — by tilt, on the
  gentle curtain or with `gentle_cover.move` — stops any other gentle move in
  the room that drives one of the same curtains.
- **During a gentle move** the Home app shows "Opening…" or "Closing…" until it
  arrives, which can take the whole curve's duration.
- It is a convention: anyone else in the house sees a tilt control on a
  curtain. `gentle_cover.move` also works on these curtains while tilt is on.

To use a different duration for one gentle move, call the action (`position`
in the room's scale — unlike tilt, which is always 100 % = open):

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

It takes any of a room's curtains — normal, gentle or one on its own — and
draws the room's curve and current
position in the room's scale, and during a gentle move a marker travelling
along the curve with the time left. It is read-only; it is also in the card
picker.

## Upgrading from 0.4 or earlier 0.5 builds

Nothing changes until you switch **Tilt moves gently** on for a room.

## Upgrading from 0.3

Existing rooms keep moving all their curtains with both the normal and the
gentle curtain, and no curtain is offered on its own until you tick it.

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
