"""Sunny's den: a short nap the child can watch, or Goodnight for a long sleep."""
import math
import random

import pygame

import config
from scenes.care import CareScene
from ui import text, theme
from ui.sunny import draw_sunny, make_sunny_renderer
from ui.widgets import Button

NAP_SECONDS = 20.0
NAP_ENERGY = 30.0            # extra energy over a full nap
NOT_SLEEPY = 90
DEN = (70, 50, 60)
BED = (120, 100, 50)


class SleepScene(CareScene):
    title = "Sunny's Den"
    GROUND_Y = 196

    def __init__(self, app):
        super().__init__(app)
        self.sunny = make_sunny_renderer(cell=4)
        sw, sh = self.sunny.size
        w, _ = config.LOGICAL_SIZE
        self.sunny_rect = pygame.Rect((w - sw) // 2 + 8, self.GROUND_Y - sh + 2, sw, sh)
        self.napping = False
        self.nap_left = 0.0
        self.darkness = 0.0
        self.nap_button = Button((40, 150, 88, 34), "Nap", self.start_nap, theme.LAVENDER)
        self.night_button = Button((w - 128, 150, 88, 34), "Goodnight", self.goodnight, theme.NAVY)
        self.wake_button = Button((40, 150, 88, 34), "Wake up", self.end_nap, theme.ORANGE)
        rng = random.Random(3)
        self.fireflies = [(rng.randrange(20, w - 20), rng.randrange(50, 140), rng.random() * 6) for _ in range(8)]
        self._set_buttons()

    def _set_buttons(self):
        extra = [self.wake_button] if self.napping else [self.nap_button, self.night_button]
        self.buttons = [self.back_button] + extra

    def on_enter(self):
        pet = self.app.pet
        if pet.stats["energy"] >= NOT_SLEEPY:
            pet.say("I'm not sleepy! But I can say goodnight later.", 4)
        else:
            pet.say("*yawn* A nap sounds nice...", 4)

    def start_nap(self):
        pet = self.app.pet
        if pet.stats["energy"] >= NOT_SLEEPY:
            pet.say("I'm not sleepy right now! Let's play!", 3)
            return
        pet.go_to_sleep()
        self.napping = True
        self.nap_left = NAP_SECONDS
        self._set_buttons()

    def end_nap(self, finished=False):
        self.napping = False
        self.app.pet.wake_up()
        if finished:
            self.reward()
            self.app.pet.say("What a nice nap! I feel rested!", 4)
        self._set_buttons()

    def goodnight(self):
        self.app.pet.go_to_sleep()
        self.app.go_home()

    def leave(self):
        if self.napping:
            self.end_nap()
        super().leave()

    def update(self, dt):
        super().update(dt)
        target = 1.0 if self.napping else 0.0
        self.darkness += (target - self.darkness) * min(1.0, dt * 2)
        if self.napping:
            step = min(dt, self.nap_left)
            self.nap_left -= step
            self.app.pet.rest(NAP_ENERGY * step / NAP_SECONDS)
            if self.nap_left <= 0:
                self.end_nap(finished=True)

    def draw(self, surface):
        w, h = config.LOGICAL_SIZE
        surface.fill(DEN)
        # rocky den wall
        for i in range(0, w, 24):
            pygame.draw.circle(surface, (85, 62, 72), (i + 12, 50 + (i * 7) % 20), 18)
        pygame.draw.rect(surface, (55, 40, 45), (0, self.GROUND_Y, w, h - self.GROUND_Y))
        r = self.sunny_rect
        pygame.draw.ellipse(surface, theme.BLACK, (r.x - 2, self.GROUND_Y - 13, r.w + 4, 22))
        pygame.draw.ellipse(surface, BED, (r.x, self.GROUND_Y - 12, r.w, 20))

        drawn = draw_sunny(surface, self.sunny, self.app.pet, r, self.t)

        if self.darkness > 0.01:
            veil = pygame.Surface((w, h), pygame.SRCALPHA)
            veil.fill((0, 0, 30, int(150 * self.darkness)))
            surface.blit(veil, (0, 0))
            for x, y, phase in self.fireflies:
                if math.sin(self.t * 2 + phase) > 0.3:
                    fx = x + round(math.sin(self.t + phase) * 6)
                    pygame.draw.rect(surface, theme.YELLOW, (fx, y, 2, 2))

        self.draw_header(surface)
        self.draw_speech(surface, (8, 40), 140, (drawn.x + 36, drawn.y + 24))
        self._draw_energy(surface)
        super().draw(surface)

    def _draw_energy(self, surface):
        w, _ = config.LOGICAL_SIZE
        energy = self.app.pet.stats["energy"]
        box = pygame.Rect(w - 128, 44, 120, 26)
        text.draw(surface, "Energy", (box.x, box.y), text.SMALL)
        pygame.draw.rect(surface, theme.BLACK, (box.x, box.y + 12, box.w, 10))
        pygame.draw.rect(surface, theme.YELLOW, (box.x + 1, box.y + 13, int((box.w - 2) * energy / 100), 8))
