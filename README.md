# RoboEyes

RoboEyes is a Python library that creates smoothly animated robot eyes for GUI displays using **Pygame**. It provides configurable eye shapes and various moods and animations, making it ideal for robotics, art installations, and interactive applications.

---

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/knmac/RoboEyes.git
   cd RoboEyes
   ```
2. Install dependencies with [uv](https://docs.astral.sh/uv/):
   ```bash
   uv sync
   ```
3. Run:
   ```bash
   uv run main.py
   ```

### Options

```
--rotate {0,90,180,270}   Screen rotation in degrees (default: 0)
--port PORT               UDP port for remote commands (default: 5005)
--bind ADDRESS            Bind address for UDP (default: 127.0.0.1)
--color R,G,B             Eye color (default: 0,255,255)
--bgcolor R,G,B           Background color (default: 0,0,0)
--width WIDTH             Canvas width in pixels (default: 640)
--height HEIGHT           Canvas height in pixels (default: 480)
--fullscreen              Run in fullscreen mode
```

---

## Keyboard Controls

| Key | Action |
|-----|--------|
| `Esc` | Quit |
| `0` / `1` / `2` / `3` / `4` / `5` | Shape: default / tired / angry / smile / squint / sleep |
| Arrow keys | Look direction (up/down/left/right) |
| `Space` | Reset look to center |
| `q` / `e` | Wink left / right |
| `w` | Blink |
| `r` | Shake animation |
| `t` | Bounce animation |
| `y` | Toggle breathing animation |
| `f` | Toggle fullscreen |
| `?` | Toggle key bindings overlay |

---

## UDP Remote Commands

Send JSON to the configured UDP port to control the eyes remotely.

```bash
echo '{"shape":"smile","look":"w"}' | nc -u 127.0.0.1 5005
```

| Command | Example | Description |
|---------|---------|-------------|
| `shape` | `{"shape": "smile"}` | Set shape (`default`/`tired`/`angry`/`smile`/`squint`/`sleep`) |
| `look` | `{"look": "e"}` | Look direction (`n`/`ne`/`e`/`se`/`s`/`sw`/`w`/`nw`/`center`) |
| `anim` | `{"anim": "bounce"}` | Trigger animation (`shake`/`bounce`/`sleep`/`breathing`/`blink`/`wink_left`/`wink_right`) |
| `color` | `{"color": [0, 200, 255]}` | Set eye color `[R, G, B]` |
| `bgcolor` | `{"bgcolor": [20, 20, 40]}` | Set background color `[R, G, B]` |
| `cyclops` | `{"cyclops": true}` | Toggle single-eye mode |
| `idle` | `{"idle": true}` | Toggle idle random movement |
| `autoblink` | `{"autoblink": true}` | Toggle automatic blinking |
| `overlay` | `{"overlay": "blush"}` | Set visual overlay (`blush`/`bubbles`/`stress`/`null` to clear) |

Commands can be combined: `{"shape": "angry", "look": "e", "color": [255, 50, 50], "overlay": "stress"}`

---

## Emote Script

A convenience script that bundles shape, animation, overlay, color, and sound into named emotions.

```bash
./scripts/emote.sh <emotion> [OPTIONS]
```

| Emotion | Shape | Animation | Overlay | Color |
|---------|-------|-----------|---------|-------|
| `neutral` | default | blink | — | sky |
| `happy` | smile | blink | blush | pink |
| `tired` | tired | blink | stress | overlay1 |
| `angry` | angry | shake | — | red |
| `squint` | squint | blink | — | peach |
| `sleeping` | sleep | breathing | bubbles | lavender |
| `laughing` | smile | bounce | — | green |
| `surprised` | default | shake | — | yellow |
| `witty` | smile | wink_left | — | teal |

Options: `--color R,G,B`, `--duration SECS`, `--port PORT`, `--bind ADDR`

Colors are loaded from a scheme file in `scripts/colorschemes/`. Available schemes: `default`, `catppuccin`, `tokyonight`.

---

## API Reference

### General

- **`begin()`** — Initialize the display with eyes closed.
- **`update()`** — Run one frame of the animation loop.

### Configuration

- **`set_width(left_eye, right_eye)`** — Set width of eyes in pixels.
- **`set_height(left_eye, right_eye)`** — Set height of eyes in pixels.
- **`set_border_radius(left_eye, right_eye)`** — Set corner radius.
- **`set_space_between(space)`** — Adjust spacing between eyes.
- **`set_cyclops(cyclops_bit)`** — Toggle single-eye mode.
- **`set_curiosity(curious_bit)`** — Toggle curiosity mode (eyes grow taller at screen edges).

### Expressions and Animations

- **`set_shape(shape)`** — Set shape (`Shape.DEFAULT`, `Shape.TIRED`, `Shape.ANGRY`, `Shape.SMILE`, `Shape.SQUINT`, `Shape.SLEEP`).
- **`set_position(position)`** — Set gaze direction using `Position` enum.
- **`close(left, right)`** — Close one or both eyes.
- **`open_eyes(left, right)`** — Mark eyes to re-open after closing.
- **`blink(left, right)`** — Blink one or both eyes.
- **`wink_left()`** / **`wink_right()`** — Wink a single eye.
- **`anim_shake()`** — Horizontal shake animation.
- **`anim_bounce()`** — Vertical bounce animation.
- **`anim_sleep()`** — Enter sleep mode: sets sleep shape, centers eyes, and starts breathing animation. Blinking is automatically suppressed during sleep.
- **`anim_breathing()`** — Toggle breathing animation (works with any shape).

### Overlays

- **`set_overlay(name)`** — Enable a visual overlay (`"blush"`, `"bubbles"`, `"stress"`).
- **`clear_overlay(name)`** — Disable an overlay, or all if `name` is `None`.

### Macro Animators

- **`set_autoblinker(active, interval, variation)`** — Automated random blinking.
- **`set_idle_mode(active, interval, variation)`** — Automated random repositioning.
- **`set_h_flicker(flicker_bit, amplitude)`** — Horizontal flicker effect.
- **`set_v_flicker(flicker_bit, amplitude)`** — Vertical flicker effect.

---

## License

This project is licensed under the **GNU General Public License (GPL)**.

---

## Credits

Forked from [sofianhw/RoboEyes](https://github.com/sofianhw/RoboEyes), which was inspired by the [FluxGarage RoboEyes project](https://github.com/FluxGarage/RoboEyes/). Special thanks for the original work that inspired this project.
