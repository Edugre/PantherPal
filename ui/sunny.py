"""Sunny's sprite: a sitting Florida panther drawn from a cell grid.

The body is a fixed grid; eyes, mouth, tail and mud spots are drawn on top
per frame depending on mood, then the whole thing gets a 1-cell black outline
and is scaled up with nearest-neighbour.
"""
import math
import random

import pygame

from ui import text, theme

GRID_W, GRID_H = 26, 22

BODY = [
    "......TT........TT........",
    ".....TDDT......TDDT.......",
    ".....TDTTTTTTTTTTDT.......",
    ".....TTTTTTTTTTTTTT.......",
    "....TTTTTTTTTTTTTTTT......",
    "....TTTTTTTTTTTTTTTT......",
    "....TTTTTTTTTTTTTTTT......",
    "....TTTTTTLLLLTTTTTT......",
    ".....TTTTLLNNLLTTTT.......",
    ".....TTTLLLLLLLLTTT.......",
    "......TTTLLLLLLTTT........",
    ".......TTTTTTTTTT.........",
    "......TTTLLLLLLTTT........",
    ".....TTTTLLLLLLTTTT.......",
    ".....TTTTLLLLLLTTTT.......",
    "....TTTTTLLLLLLTTTTT......",
    "....TTTTTLLLLLLTTTTT......",
    "....TTTTTTLLLLTTTTTT......",
    "....TTTTTTTTTTTTTTTT......",
    "....TTLLLTTTTTTLLLTT......",
    "....TLLLLTTTTTTLLLLT......",
    "....DLDLD......DLDLD......",
]

COLORS = {
    "T": (201, 149, 90),     # tawny coat
    "D": (107, 68, 38),      # dark brown (ears, toes)
    "L": theme.PEACH,        # light muzzle / chest
    "N": (90, 50, 40),       # nose
    "W": theme.WHITE,
    "K": theme.BLACK,
    "P": theme.PINK,         # tongue
    "M": (110, 80, 40),      # mud
    "B": theme.BLUE,         # tear
}

# Eye patches are 2x2 at these grid positions (left eye, right eye).
EYE_POS = [(7, 4), (15, 4)]
EYES = {
    "open":   (["WW", "WK"], ["WW", "KW"]),
    "closed": (["TT", "KK"], ["TT", "KK"]),
    "happy":  (["KK", "TT"], ["KK", "TT"]),
    "tired":  (["KK", "WK"], ["KK", "KW"]),
}

# Mouth patches are 4x2 starting at this grid position. "." = leave as is.
MOUTH_POS = (10, 9)
MOUTHS = {
    "smile":   ["....", "K..K", ".KK."],
    "neutral": ["....", ".KK."],
    "frown":   [".KK.", "K..K"],
    "open":    [".KK.", ".PP."],
}

MUD_SPOTS = [(7, 15), (16, 16), (9, 18), (13, 2), (5, 6), (15, 13), (11, 19), (17, 7)]

# Per-mood look: eyes, mouth, tail wag speed (0 = tail lying down)
LOOKS = {
    "happy":    ("open", "smile", 6.0),
    "ok":       ("open", "neutral", 3.0),
    "love":     ("happy", "smile", 9.0),
    "eating":   ("happy", "open", 6.0),
    "hungry":   ("open", "frown", 1.5),
    "dirty":    ("open", "frown", 1.5),
    "bored":    ("tired", "neutral", 0.0),
    "sleepy":   ("tired", "neutral", 0.0),
    "sleeping": ("closed", "neutral", 0.0),
    "hot":      ("open", "open", 1.5),
    "cold":     ("open", "frown", 1.0),
}


def _patch(surface, rows, topleft):
    x0, y0 = topleft
    for dy, row in enumerate(rows):
        for dx, ch in enumerate(row):
            if ch in COLORS:
                surface.set_at((x0 + dx, y0 + dy), COLORS[ch])


def _base_surface():
    surf = pygame.Surface((GRID_W, GRID_H), pygame.SRCALPHA)
    _patch(surf, BODY, (0, 0))
    return surf


class SunnyRenderer:
    def __init__(self, cell=4):
        self.cell = cell
        self._base = _base_surface()
        # +2 cells for the outline on every side
        self.size = ((GRID_W + 2) * cell, (GRID_H + 2) * cell)

    def render(self, mood, t, clean=100.0):
        eyes, mouth, wag = LOOKS.get(mood, LOOKS["ok"])

        # Blink for 0.15s roughly every 4s
        if eyes == "open" and (t % 4.0) < 0.15:
            eyes = "closed"
        # Chewing / yawning animate the mouth
        if mood == "eating" and int(t * 6) % 2:
            mouth = "neutral"
        if mood == "sleepy" and (t % 6.0) < 1.0:
            mouth = "open"

        cells = self._base.copy()
        for (pos, patch) in zip(EYE_POS, EYES[eyes]):
            _patch(cells, patch, pos)
        _patch(cells, MOUTHS[mouth], MOUTH_POS)

        if clean < 70:
            spots = round((1 - clean / 100) * len(MUD_SPOTS))
            for x, y in MUD_SPOTS[:spots]:
                cells.set_at((x, y), COLORS["M"])

        if mood in ("hungry", "dirty") and (t % 3.0) < 1.5:
            cells.set_at((8, 6), COLORS["B"])   # little tear

        self._draw_tail(cells, t, wag)

        # Outline: black silhouette offset in 4 directions behind the sprite.
        framed = pygame.Surface((GRID_W + 2, GRID_H + 2), pygame.SRCALPHA)
        silhouette = pygame.mask.from_surface(cells).to_surface(
            setcolor=theme.BLACK, unsetcolor=(0, 0, 0, 0))
        for dx, dy in ((0, 1), (2, 1), (1, 0), (1, 2)):
            framed.blit(silhouette, (dx, dy))
        framed.blit(cells, (1, 1))
        return pygame.transform.scale(framed, self.size)

    @staticmethod
    def _draw_tail(cells, t, wag):
        tawny, tip = COLORS["T"], COLORS["K"]
        if wag == 0:
            # Lying along the ground, tip curled up
            for x in range(20, 25):
                cells.set_at((x, 21), tawny)
            cells.set_at((25, 21), tip)
            cells.set_at((25, 20), tip)
            return
        # Rising S-curve from the hip; the top sways with t * wag.
        cells.set_at((20, 20), tawny)
        length = 10
        for i in range(length):
            y = 20 - i
            sway = math.sin(t * wag) * (i / length) * 2
            x = 21 + round(1.2 * math.sin(i * 0.45) + sway)
            cells.set_at((x, y), tip if i >= length - 2 else tawny)


HEART = [".XX.XX.", "XXXXXXX", ".XXXXX.", "..XXX..", "...X..."]


def heart(surface, pos, size=2):
    x, y = pos
    for dy, row in enumerate(HEART):
        for dx, ch in enumerate(row):
            if ch == "X":
                pygame.draw.rect(surface, theme.RED, (x + dx * size, y + dy * size, size, size))


def draw_sunny(surface, renderer, pet, rect, t, show_mud=True):
    """Draw Sunny with mood motion (bounce, shiver, breathing) and effects.

    Returns the rect Sunny was actually drawn at this frame.
    """
    mood = pet.mood
    r = rect.copy()
    if mood == "sleeping":
        r.y += round(math.sin(t * 1.2))               # slow breathing
    elif mood == "cold":
        r.x += random.choice((-1, 0, 1))              # shiver
    elif mood in ("happy", "love"):
        r.y -= abs(round(math.sin(t * 5) * 3))        # bounce
    else:
        r.y += round(math.sin(t * 2))
    surface.blit(renderer.render(mood, t, pet.stats["clean"] if show_mud else 100.0), r)

    c = renderer.cell
    if mood == "love":
        for i in range(3):
            phase = (t * 0.8 + i / 3) % 1
            heart(surface, (r.centerx - 5 * c + i * 4 * c, int(r.top + 2 * c - phase * 8 * c)))
    elif mood == "hot":
        dy = int(t * 10) % (2 * c)
        pygame.draw.rect(surface, theme.BLUE, (r.left + 2 * c, r.top + 4 * c + dy, c, c + 2))
    elif mood == "sleeping":
        for i in range(3):
            phase = (t * 0.5 + i / 3) % 1
            text.draw(surface, "z" if i % 2 else "Z",
                      (r.right - 5 * c + phase * 5 * c, r.top + 5 * c - phase * 10 * c),
                      text.MEDIUM + i * 4, theme.WHITE)
    return r
