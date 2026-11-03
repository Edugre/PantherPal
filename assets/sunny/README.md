# Sunny's art

Drop PNG drawings of Sunny in this folder. The app picks them up on its next
start. If there's no `idle.png`, it uses the built-in pixel panther instead.

## File names

One file per mood, or numbered frames for an animation:

```
idle.png                      # still image
idle_0.png  idle_1.png  ...   # animation, played in number order
```

| File      | When it shows                          | If missing, uses |
|-----------|----------------------------------------|------------------|
| `idle`    | **required**: normal / "ok" mood        | (built-in sprite) |
| `happy`   | all needs high                         | idle             |
| `love`    | being petted, after a bath, playing    | happy → idle     |
| `eating`  | right after being fed                  | happy → idle     |
| `sad`     | general "not great" pose               | idle             |
| `hungry`  | Food is low                            | sad → idle       |
| `dirty`   | Clean is low                           | sad → idle       |
| `bored`   | Fun is low                             | sad → idle       |
| `sleepy`  | Energy is low                          | sad → idle       |
| `hot`     | room is 28 °C / 82 °F or warmer         | sad → idle       |
| `cold`    | room is 16 °C / 61 °F or cooler         | sad → idle       |
| `sleeping`| napping / goodnight                    | idle             |
| `ok`      | in-between mood (optional)             | idle             |

The app adds some effects on top of your drawings, so you don't need to draw
them: mud spots when Sunny is dirty, hearts, Zzz, sweat drops, bouncing,
shivering and breathing.

## Drawing tips

- **Transparent background.** Mud spots only land on the solid parts of
  the drawing.
- **Same canvas size for every file** keeps Sunny from jumping around.
  Different sizes still work, though: each frame is lined up bottom-centre.
- **Size:** any size works. Small pixel art (for example 32×32 or 48×48) is
  enlarged in whole steps so the pixels stay sharp. Big drawings are shrunk
  smoothly. On screen, Sunny is about 96 px tall (home) or 120 px tall (bath)
  on the 400×240 pixel canvas.
- **Pose:** sitting, facing the viewer, feet at the bottom of the canvas.

## Optional `sprite.json`

```json
{
  "fps": 4,
  "mouth": [16, 20]
}
```

- `fps`: animation speed for numbered frames (default 4).
- `mouth`: pixel position of the mouth in your original drawing. Food
  flies to this spot. Default: centre, 45% down.

## Check your art

```
.venv/bin/python -m tools.preview_sunny
```

This writes `data/sunny_preview.png`, which shows every mood (and which file
it used) at home, bath and dirty sizes.
