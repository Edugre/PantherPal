"""Hand-drawn props from assets/props/ (heart, moon, fish, ball, ...).

Each image is cropped to its visible pixels and cached; get() returns None
when a prop hasn't been drawn so callers can use their built-in fallback.
"""
import pygame

import config

_cache = {}


def get(name, scale=1):
    key = (name, scale)
    if key not in _cache:
        _cache[key] = _load(name, scale)
    return _cache[key]


def _load(name, scale):
    if not config.PROPS_DIR.is_dir():
        return None
    for path in config.PROPS_DIR.iterdir():
        if path.stem.lower() == name and path.suffix.lower() == ".png":
            image = pygame.image.load(str(path))
            image = image.subsurface(image.get_bounding_rect()).copy()
            if scale != 1:
                image = pygame.transform.scale(image, (image.get_width() * scale, image.get_height() * scale))
            return image
    return None
