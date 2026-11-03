"""Render every mood of Sunny into one contact sheet: data/sunny_preview.png.

Usage: .venv/bin/python -m tools.preview_sunny [art_dir]
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

import config
from ui import text, theme
from ui.sunny import FALLBACKS, load_art, make_sunny_renderer, resolve_mood

MOODS = list(FALLBACKS)


def main():
    if len(sys.argv) > 1:
        config.SUNNY_ART_DIR = Path(sys.argv[1]).resolve()
    pygame.init()
    pygame.display.set_mode((1, 1))

    art = load_art()
    renderer = make_sunny_renderer(cell=4)
    cols = 6
    cw, ch = renderer.size[0] + 20, renderer.size[1] + 34
    rows = -(-len(MOODS) // cols) + 1
    sheet = pygame.Surface((cols * cw, rows * ch))
    sheet.fill(theme.NAVY)

    available = art["frames"] if art else {}
    for i, mood in enumerate(MOODS):
        x, y = (i % cols) * cw, (i // cols) * ch
        sheet.blit(renderer.render(mood, 0.5), (x + 10, y + 4))
        source = f"{resolve_mood(mood, available)}.png" if art else "built-in"
        text.draw(sheet, mood, (x + cw // 2, y + ch - 24), text.MEDIUM, theme.YELLOW, anchor="center")
        text.draw(sheet, source, (x + cw // 2, y + ch - 10), text.SMALL, theme.MUTED, anchor="center")

    # Last row: dirty state with mud, and the mouth / mud spot markers.
    y = (rows - 1) * ch
    sheet.blit(renderer.render("dirty", 0.5, clean=10), (10, y + 4))
    text.draw(sheet, "dirty + mud", (cw // 2, y + ch - 24), text.MEDIUM, theme.YELLOW, anchor="center")
    marked = renderer.render("ok", 0.5).copy()
    pygame.draw.circle(marked, theme.RED, renderer.mouth, 3)
    for p in renderer.mud_points:
        pygame.draw.circle(marked, theme.GREEN, p, 2)
    sheet.blit(marked, (cw + 10, y + 4))
    text.draw(sheet, "mouth / mud spots", (cw + cw // 2, y + ch - 24), text.MEDIUM, theme.YELLOW, anchor="center")

    out = config.DATA_DIR / "sunny_preview.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(sheet, str(out))
    print(f"Art folder: {config.SUNNY_ART_DIR} ({'custom art' if art else 'no idle.png, built-in sprite'})")
    if art:
        print("Drawings found:", ", ".join(f"{k} ({len(v)} frame{'s' * (len(v) > 1)})"
                                          for k, v in sorted(art["frames"].items())))
    print(f"Preview saved to {out}")


if __name__ == "__main__":
    main()
