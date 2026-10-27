"""Shared layout for the care screens (Feed, Clean, Sleep)."""
import pygame

import config
from scenes.base import Scene
from ui import text, theme
from ui.widgets import Button, panel, points_badge, speech_bubble

CARE_POINTS = 1     # stars for each care action Sunny accepts


class CareScene(Scene):
    title = ""

    def __init__(self, app):
        super().__init__(app)
        self.t = 0.0
        w, _ = config.LOGICAL_SIZE
        self.back_button = Button((w - 66, 7, 58, 22), "Back", self.leave, theme.BLUE)
        self.buttons = [self.back_button]

    def leave(self):
        self.app.go_home()

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.leave()
            return True
        return super().handle_event(event)

    def update(self, dt):
        self.t += dt

    def reward(self):
        self.app.add_points(CARE_POINTS)

    def draw_header(self, surface):
        w, _ = config.LOGICAL_SIZE
        panel(surface, (4, 4, w - 8, 28))
        text.draw(surface, self.title, (12, 18), text.LARGE, theme.ACCENT, anchor="midleft")
        points_badge(surface, (w - 120, 18), self.app.points)

    def draw_speech(self, surface, topleft, width, tip):
        if self.app.pet.speech:
            speech_bubble(surface, self.app.pet.speech, topleft, width, tip)
