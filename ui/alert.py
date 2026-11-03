"""Pop-up shown over any screen when a timer, alarm or bedtime goes off."""
import math

import pygame

import config
from ui import text, theme
from ui.widgets import Button, panel

KIND_COLORS = {"timer": theme.ORANGE, "alarm": theme.PINK, "bedtime_warning": theme.LAVENDER,
               "bedtime": theme.BLUE}


class AlertOverlay:
    def __init__(self, on_dismiss):
        self.queue = []
        self.t = 0.0
        self.on_dismiss = on_dismiss
        w, h = config.LOGICAL_SIZE
        self.box = pygame.Rect(0, 0, 260, 132)
        self.box.center = (w // 2, h // 2)
        self.ok = Button((self.box.centerx - 40, self.box.bottom - 40, 80, 30), "OK", self.dismiss, theme.DARK_GREEN)

    @property
    def active(self):
        return bool(self.queue)

    def push(self, alert):
        self.queue.append(alert)
        self.t = 0.0

    def dismiss(self):
        alert = self.queue.pop(0)
        self.t = 0.0
        self.on_dismiss(alert)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER,
                                                          pygame.K_SPACE, pygame.K_ESCAPE):
            self.dismiss()
            return True
        self.ok.handle_event(event)
        return True     # the pop-up swallows everything while it's up

    def update(self, dt):
        self.t += dt

    def draw(self, surface):
        alert = self.queue[0]
        shade = pygame.Surface(config.LOGICAL_SIZE, pygame.SRCALPHA)
        shade.fill((0, 0, 0, 150))
        surface.blit(shade, (0, 0))
        color = KIND_COLORS.get(alert.kind, theme.ORANGE)
        border = color if int(self.t * 3) % 2 == 0 else theme.WHITE
        pygame.draw.rect(surface, border, self.box.inflate(8, 8))
        panel(surface, self.box)
        self._draw_bell(surface, (self.box.x + 26, self.box.y + 20), color)
        text.draw(surface, alert.title, (self.box.centerx + 14, self.box.y + 22), text.LARGE, theme.YELLOW, anchor="center")
        for i, line in enumerate(text.wrap(alert.message, self.box.w - 30)[:3]):
            text.draw(surface, line, (self.box.centerx, self.box.y + 54 + i * 14), text.MEDIUM, anchor="center")
        self.ok.draw(surface)

    def _draw_bell(self, surface, center, color):
        # A little bell that rings for the first couple of seconds.
        swing = math.sin(self.t * 18) * 3 if self.t < 2.5 else 0
        x, y = center[0] + round(swing), center[1]
        pygame.draw.circle(surface, theme.BLACK, (x, y - 2), 11)
        pygame.draw.rect(surface, theme.BLACK, (x - 13, y - 2, 26, 14))
        pygame.draw.circle(surface, color, (x, y - 2), 10)
        pygame.draw.rect(surface, color, (x - 12, y - 2, 24, 13))
        pygame.draw.rect(surface, theme.BLACK, (x - 14, y + 10, 28, 3))
        pygame.draw.circle(surface, theme.YELLOW, (x, y + 15), 3)
