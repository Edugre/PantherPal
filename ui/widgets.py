"""Chunky, kid-sized pixel widgets."""
import pygame

from ui import icons, text, theme


class Button:
    def __init__(self, rect, label, on_click, color=theme.ORANGE, text_size=text.MEDIUM):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.on_click = on_click
        self.color = color
        self.text_size = text_size
        self.hover = False
        self.pressed = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.pressed = True
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was_pressed, self.pressed = self.pressed, False
            if was_pressed and self.rect.collidepoint(event.pos):
                self.on_click()
                return True
        return False

    def draw(self, surface):
        # Pressed buttons shift down 2px onto their "shadow" for a tactile feel.
        offset = 2 if self.pressed else 0
        body = self.rect.move(0, offset)
        if not self.pressed:
            pygame.draw.rect(surface, theme.BLACK, self.rect.move(0, 2))
        fill = tuple(min(255, c + 30) for c in self.color) if self.hover else self.color
        pygame.draw.rect(surface, fill, body)
        pygame.draw.rect(surface, theme.BLACK, body, 1)
        # top highlight line
        pygame.draw.line(surface, theme.WHITE, (body.left + 2, body.top + 2), (body.right - 3, body.top + 2))
        text.draw(surface, self.label, body.center, self.text_size, theme.WHITE, anchor="center")


def panel(surface, rect, color=theme.PANEL):
    rect = pygame.Rect(rect)
    pygame.draw.rect(surface, color, rect)
    pygame.draw.rect(surface, theme.BLACK, rect, 1)
    pygame.draw.rect(surface, theme.LAVENDER, rect.inflate(-2, -2), 1)
    return rect


def speech_bubble(surface, message, topleft, width, tip):
    """White speech bubble with a pointer toward `tip` (below the box)."""
    lines = text.wrap(message, width - 16)
    line_h = 13
    box = pygame.Rect(topleft, (width, len(lines) * line_h + 12))
    base = min(max(tip[0] - 7, box.left + 6), box.right - 20)
    pygame.draw.rect(surface, theme.WHITE, box)
    pygame.draw.rect(surface, theme.BLACK, box, 1)
    pygame.draw.polygon(surface, theme.WHITE, [(base, box.bottom - 1), (base + 14, box.bottom - 1), tip])
    pygame.draw.line(surface, theme.BLACK, (base, box.bottom), tip)
    pygame.draw.line(surface, theme.BLACK, (base + 14, box.bottom), tip)
    for i, line in enumerate(lines):
        text.draw(surface, line, (box.centerx, box.top + 6 + i * line_h + line_h // 2),
                  text.MEDIUM, theme.BLACK, anchor="center", shadow=False)
    return box


def points_badge(surface, center, points):
    """Star icon followed by the point total, centred on `center`."""
    star = icons.icon(icons.STAR, 2)
    label = text.render(str(points), text.MEDIUM, theme.YELLOW)
    total_w = star.get_width() + 4 + label.get_width()
    x = center[0] - total_w // 2
    surface.blit(star, star.get_rect(midleft=(x, center[1])))
    text.draw(surface, str(points), (x + star.get_width() + 4, center[1]), text.MEDIUM, theme.YELLOW, anchor="midleft")
