"""Crisp, non-antialiased text for the pixel canvas."""
import pygame

from ui import theme

SMALL, MEDIUM, LARGE, HUGE = 12, 16, 24, 36

_fonts = {}


def font(size):
    if size not in _fonts:
        _fonts[size] = pygame.font.Font(None, size)
    return _fonts[size]


def render(text, size=MEDIUM, color=theme.TEXT):
    return font(size).render(text, False, color)


def wrap(text, width, size=MEDIUM):
    """Split text into lines that fit within `width` pixels."""
    f = font(size)
    lines, line = [], ""
    for word in text.split():
        candidate = f"{line} {word}".strip()
        if line and f.size(candidate)[0] > width:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines


def draw(surface, text, pos, size=MEDIUM, color=theme.TEXT, anchor="topleft", shadow=True):
    """Draw text with an optional 1px drop shadow. Returns the text rect."""
    img = render(text, size, color)
    rect = img.get_rect(**{anchor: pos})
    if shadow:
        surface.blit(render(text, size, theme.BLACK), rect.move(1, 1))
    surface.blit(img, rect)
    return rect
