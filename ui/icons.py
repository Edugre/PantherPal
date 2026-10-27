"""Small pixel-art icons (foods, star). One char = one pixel before scaling."""
import pygame

from ui import theme

PALETTE = {
    "R": (200, 70, 50),       # meat
    "W": theme.WHITE,         # bone / stick
    "B": theme.BLUE,          # fish
    "K": theme.BLACK,
    "Y": theme.YELLOW,
    "O": theme.ORANGE,
    "G": theme.DARK_GREEN,
    "L": theme.GREEN,
    "P": theme.PINK,
}

MEAT = [
    "....RRR.",
    "...RRRRR",
    "...RRRRR",
    "....RRR.",
    "...WW...",
    "..WW....",
    ".WW.....",
    "WW......",
]

FISH = [
    "..........",
    "...BBBB...",
    ".BBBBBBB.B",
    "BBKBBBBBBB",
    "BBBBBBBBBB",
    ".BBBBBBB.B",
    "...BBBB...",
    "..........",
]

FISH_POP = [
    "..OOOO....",
    ".OYYYYO.O.",
    "OKYYYYYOO.",
    ".OYYYYO.O.",
    "..OOOO....",
    "....W.....",
    "....W.....",
    "....W.....",
]

STEAK = [
    "..RRRRR...",
    ".RRRRRRRR.",
    "RRRWRRRRRR",
    "RRRWWWRRRR",
    "RRRWRRRRRR",
    ".RRRRRRRR.",
    "..RRRRRR..",
    "..........",
]

BROCCOLI = [
    "..GGGG..",
    ".GGLGGG.",
    "GGGGGLGG",
    ".GLGGGG.",
    "...LL...",
    "...LL...",
    "...LL...",
    "........",
]

CANDY = [
    "..........",
    "..........",
    "P..PPPP..P",
    "PPPPWPPPPP",
    "PPPPPWPPPP",
    "P..PPPP..P",
    "..........",
    "..........",
]

STAR = [
    "...Y...",
    "...Y...",
    "YYYYYYY",
    ".YYYYY.",
    "..YYY..",
    ".YY.YY.",
    "YY...YY",
]

_cache = {}


def icon(rows, scale=3):
    """Render an icon grid to a cached surface, with a 1px black outline."""
    key = (id(rows), scale)
    if key not in _cache:
        w, h = len(rows[0]), len(rows)
        cells = pygame.Surface((w, h), pygame.SRCALPHA)
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch in PALETTE:
                    cells.set_at((x, y), PALETTE[ch])
        framed = pygame.Surface((w + 2, h + 2), pygame.SRCALPHA)
        silhouette = pygame.mask.from_surface(cells).to_surface(
            setcolor=theme.BLACK, unsetcolor=(0, 0, 0, 0))
        for dx, dy in ((0, 1), (2, 1), (1, 0), (1, 2)):
            framed.blit(silhouette, (dx, dy))
        framed.blit(cells, (1, 1))
        _cache[key] = pygame.transform.scale(framed, ((w + 2) * scale, (h + 2) * scale))
    return _cache[key]
