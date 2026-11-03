"""Sunny's sprite.

Two interchangeable renderers share one interface (size, cell, mouth,
mud_points, render()):
  * SunnyArt draws hand-made PNGs from assets/sunny/ (see the README there)
  * SunnyRenderer is the built-in fallback: a sitting Florida panther drawn
    from a cell grid, with eyes, mouth, tail and mud drawn on top per mood,
    a 1-cell black outline, scaled up with nearest-neighbour.
make_sunny_renderer() picks the art when it exists.
"""
import json
import math
import random
import re

import config

import pygame

from ui import props, text, theme

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
# Cells for scrub-able mud blobs in the bath (all above the tub rim).
SCRUB_CELLS = [(6, 6), (16, 6), (12, 3), (8, 13), (15, 14), (10, 16), (7, 10), (17, 12)]

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
        self.mouth = (12 * cell, 11 * cell)
        self.mud_points = [((x + 1) * cell + cell // 2, (y + 1) * cell + cell // 2) for x, y in SCRUB_CELLS]

    @staticmethod
    def has_own(mood):
        return False

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


# ---------------------------------------------------------------------------
# Hand-drawn art
# ---------------------------------------------------------------------------

# If a mood has no drawing, try these in order. Everything ends at "idle"
# (and "idle" itself falls back to the happy drawing when it isn't drawn).
FALLBACKS = {
    "ok": [],
    "happy": [],
    "love": ["happy"],
    "eating": ["happy"],
    "hungry": ["sad"],
    "dirty": ["sad"],
    "bored": ["sad"],
    "sleepy": ["sad"],
    "hot": ["sad"],
    "cold": ["sad"],
    "sleeping": [],
}
DEFAULT_ART_FPS = 4
MUD = (110, 80, 40)
MOOD_NAMES = set(FALLBACKS) | {"idle", "sad"}
# idle.png, idle_0.png, idle1.png, Happy2.PNG ... (case-insensitive)
_FRAME_RE = re.compile(r"^([a-z]+?)_?(\d+)?\.png$")
_art_cache = {}


def load_art(directory=None):
    """{name: [frame surfaces]}, the names actually drawn, and sprite.json
    settings; or None if there is neither an idle nor a happy drawing.
    Cached per directory."""
    directory = directory or config.SUNNY_ART_DIR
    key = str(directory)
    if key in _art_cache:
        return _art_cache[key]
    frames = {}
    if directory.is_dir():
        found = {}
        for path in directory.iterdir():
            match = _FRAME_RE.match(path.name.lower())
            if not match:
                continue
            name, index = match.group(1), int(match.group(2) or 0)
            if name not in MOOD_NAMES:
                print(f"[sunny] ignoring {path.name}: '{name}' is not a mood (props go in assets/props/)")
                continue
            found.setdefault(name, []).append((index, path))
        for name, items in found.items():
            frames[name] = [pygame.image.load(str(p)) for _, p in sorted(items)]
    settings = {}
    settings_path = directory / "sprite.json"
    if settings_path.is_file():
        settings = json.loads(settings_path.read_text())
    drawn = set(frames)
    if "idle" not in frames and "happy" in frames:
        frames["idle"] = frames["happy"]
    art = {"frames": frames, "drawn": drawn, "settings": settings} if "idle" in frames else None
    if frames and art is None:
        print(f"[sunny] {directory} has drawings but no idle or happy; using the built-in sprite")
    _art_cache[key] = art
    return art


def resolve_mood(mood, available):
    """Name of the drawing to use for `mood`."""
    for name in [mood] + FALLBACKS.get(mood, []) + ["idle"]:
        if name in available:
            return name
    return "idle"


class SunnyArt:
    def __init__(self, art, target_height):
        self.settings = art["settings"]
        self.drawn = art["drawn"]
        self.fps = self.settings.get("fps", DEFAULT_ART_FPS)
        raw = art["frames"]
        mouth = self.settings.get("mouth")

        # Trim the empty border shared by every frame so Sunny stands on the
        # ground and fills the space (one crop for all frames keeps them aligned).
        all_frames = [f for fs in raw.values() for f in fs]
        if len({f.get_size() for f in all_frames}) == 1:
            crop = all_frames[0].get_bounding_rect().unionall([f.get_bounding_rect() for f in all_frames])
            raw = {name: [f.subsurface(crop).copy() for f in fs] for name, fs in raw.items()}
            if mouth:
                mouth = (mouth[0] - crop.x, mouth[1] - crop.y)

        art_w = max(f.get_width() for fs in raw.values() for f in fs)
        art_h = max(f.get_height() for fs in raw.values() for f in fs)

        # Crisp whole-number upscaling for small pixel art; smooth fit otherwise.
        factor = target_height / art_h
        if factor >= 1:
            factor = int(factor)
            scale = pygame.transform.scale
        else:
            scale = pygame.transform.smoothscale
        self.factor = factor
        self.size = (round(art_w * factor), round(art_h * factor))
        self.cell = max(2, self.size[1] // 24)    # effects scale with this

        self.frames = {}
        for name, frames in raw.items():
            out = []
            for f in frames:
                scaled = scale(f, (round(f.get_width() * factor), round(f.get_height() * factor)))
                canvas = pygame.Surface(self.size, pygame.SRCALPHA)
                # bottom-centre align so different frame sizes stand on the same spot
                canvas.blit(scaled, scaled.get_rect(midbottom=(self.size[0] // 2, self.size[1])))
                out.append(canvas)
            self.frames[name] = out

        self.mouth = ((round(mouth[0] * factor), round(mouth[1] * factor)) if mouth
                      else (self.size[0] // 2, int(self.size[1] * 0.45)))
        self.mud_points = self._find_mud_points()

    def _find_mud_points(self, count=8):
        """Spots on solid parts of the idle drawing, away from its edges."""
        idle = self.frames["idle"][0]
        mask = pygame.mask.from_surface(idle)
        w, h = self.size
        margin = max(3, self.cell)
        points = []
        for gy in range(2, 10):
            for gx in range(1, 9):
                x, y = gx * w // 9, gy * h // 13
                if all(0 <= px < w and 0 <= py < h and mask.get_at((px, py))
                       for px, py in ((x, y), (x - margin, y), (x + margin, y), (x, y - margin), (x, y + margin))):
                    points.append((x, y))
        random.Random(11).shuffle(points)
        return points[:count]

    def has_own(self, mood):
        """True if this mood was drawn by hand (so its effects are in the art)."""
        return mood in self.drawn

    def render(self, mood, t, clean=100.0):
        frames = self.frames[resolve_mood(mood, self.frames)]
        frame = frames[int(t * self.fps) % len(frames)]
        if clean >= 70 or not self.mud_points:
            return frame
        frame = frame.copy()
        spots = round((1 - clean / 100) * len(self.mud_points))
        for x, y in self.mud_points[:spots]:
            pygame.draw.circle(frame, MUD, (x, y), max(2, self.cell))
        return frame


def make_sunny_renderer(cell=4):
    """Hand-drawn art when assets/sunny/idle.png exists, else the built-in sprite.

    `cell` sets the size: art is scaled to the same height the built-in
    sprite would have at that cell size.
    """
    art = load_art()
    if art:
        return SunnyArt(art, (GRID_H + 2) * cell)
    return SunnyRenderer(cell)


HEART = [".XX.XX.", "XXXXXXX", ".XXXXX.", "..XXX..", "...X..."]


def heart(surface, pos, size=2):
    art = props.get("heart")
    if art:
        surface.blit(art, pos)
        return
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
    elif renderer.has_own(mood):
        pass                                          # the drawing has its own effects
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
