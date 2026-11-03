"""Scene base class and a generic placeholder scene."""
import pygame

import config
from ui import text, theme
from ui.widgets import Button


class Scene:
    captures_keyboard = False     # True while the scene needs typed text
    def __init__(self, app):
        self.app = app
        self.buttons = []

    def on_enter(self):
        pass

    def on_exit(self):
        pass

    def handle_event(self, event):
        for button in self.buttons:
            if button.handle_event(event):
                return True
        return False

    def update(self, dt):
        pass

    def draw(self, surface):
        for button in self.buttons:
            button.draw(surface)


class PlaceholderScene(Scene):
    """Stand-in for screens that are built in later steps."""

    def __init__(self, app, title):
        super().__init__(app)
        self.title = title
        w, h = config.LOGICAL_SIZE
        self.buttons = [Button((w // 2 - 40, h - 50, 80, 32), "Back", app.go_home, theme.BLUE)]

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.app.go_home()
            return True
        return super().handle_event(event)

    def draw(self, surface):
        surface.fill(theme.BG)
        w, h = config.LOGICAL_SIZE
        text.draw(surface, self.title, (w // 2, 70), text.HUGE, theme.ACCENT, anchor="center")
        text.draw(surface, "Coming soon!", (w // 2, 110), text.MEDIUM, theme.MUTED, anchor="center")
        super().draw(surface)
