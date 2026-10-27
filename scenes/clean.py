"""Bath time: drag the sponge over Sunny to scrub off the mud blobs."""
import math
import random

import pygame

import config
from scenes.care import CareScene
from ui import theme
from ui.sunny import SunnyRenderer, draw_sunny

# Grid cells on Sunny's body where mud can sit (all above the tub rim).
MUD_CELLS = [(6, 6), (16, 6), (12, 3), (8, 13), (15, 14), (10, 16), (7, 10), (17, 12)]
SCRUB_PER_PIXEL = 0.025      # ~40px of scrubbing clears a blob
SCRUB_RADIUS = 12
TICKLE_EVERY = 3.0
MUD = (110, 80, 40)
SPONGE = (255, 220, 80)


class CleanScene(CareScene):
    title = "Bath Time"
    TUB = pygame.Rect(95, 178, 210, 46)

    def __init__(self, app):
        super().__init__(app)
        self.sunny = SunnyRenderer(cell=5)
        sw, sh = self.sunny.size
        self.sunny_rect = pygame.Rect(self.TUB.centerx - sw // 2 + 10, self.TUB.top + 26 - sh, sw, sh)
        self.sponge = (300, 120)
        self.scrubbing = False
        self.bubbles = []
        self.done = False
        self._tickle = 0.0

        clean = app.pet.stats["clean"]
        count = 0 if clean >= 95 else min(len(MUD_CELLS), math.ceil((100 - clean) / 11))
        c = self.sunny.cell
        self.blobs = [{"off": ((x + 1) * c + c // 2, (y + 1) * c + c // 2), "hp": 1.0,
                       "r": random.randint(5, 7)} for x, y in random.sample(MUD_CELLS, count)]
        self._drawn_rect = self.sunny_rect

    def on_enter(self):
        pygame.mouse.set_visible(False)
        if self.blobs:
            self.app.pet.say("I'm all muddy! Scrub me with the sponge!", 4)
        else:
            self.app.pet.say("I'm already squeaky clean! Let's make bubbles!", 4)

    def on_exit(self):
        pygame.mouse.set_visible(True)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.scrubbing = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.scrubbing = False
        elif event.type == pygame.MOUSEMOTION:
            old, self.sponge = self.sponge, event.pos
            if self.scrubbing:
                self._scrub(math.dist(old, self.sponge))
        return super().handle_event(event)

    def _blob_pos(self, blob):
        return self._drawn_rect.x + blob["off"][0], self._drawn_rect.y + blob["off"][1]

    def _scrub(self, distance):
        if distance <= 0:
            return
        if random.random() < 0.5:
            self.bubbles.append([self.sponge[0] + random.randint(-8, 8), self.sponge[1],
                                 random.uniform(15, 35), random.randint(2, 4), 1.0])
        if self.done:
            return
        for blob in self.blobs:
            if blob["hp"] > 0 and math.dist(self._blob_pos(blob), self.sponge) <= SCRUB_RADIUS:
                blob["hp"] -= distance * SCRUB_PER_PIXEL
        if self._tickle <= 0 and self._drawn_rect.collidepoint(self.sponge):
            self._tickle = TICKLE_EVERY
            self.app.pet.react("love", 1.0)
        if self.blobs and all(b["hp"] <= 0 for b in self.blobs):
            self.done = True
            if self.app.pet.wash(100):
                self.reward()
                self.app.pet.say("Squeaky clean! Thank you!", 4)

    def update(self, dt):
        super().update(dt)
        self._tickle -= dt
        for b in self.bubbles:
            b[1] -= b[2] * dt
            b[4] -= dt * 0.8
        self.bubbles = [b for b in self.bubbles if b[4] > 0]

    def draw(self, surface):
        w, h = config.LOGICAL_SIZE
        surface.fill((170, 210, 240))
        for x in range(0, w, 20):
            pygame.draw.line(surface, (150, 190, 225), (x, 32), (x, h))
        for y in range(32, h, 20):
            pygame.draw.line(surface, (150, 190, 225), (0, y), (w, y))
        self.draw_header(surface)

        self._drawn_rect = draw_sunny(surface, self.sunny, self.app.pet, self.sunny_rect, self.t, show_mud=False)
        for blob in self.blobs:
            if blob["hp"] > 0:
                x, y = self._blob_pos(blob)
                r = max(2, round(blob["r"] * blob["hp"] ** 0.5))
                pygame.draw.circle(surface, MUD, (x, y), r)
                pygame.draw.circle(surface, (80, 55, 25), (x - 1, y + 1), max(1, r // 2))

        # bathtub in front of Sunny
        tub = self.TUB
        pygame.draw.rect(surface, theme.BLACK, tub.inflate(2, 2), border_radius=8)
        pygame.draw.rect(surface, theme.WHITE, tub, border_radius=8)
        pygame.draw.rect(surface, theme.LIGHT_GREY, (tub.x + 6, tub.bottom - 10, tub.w - 12, 4))
        for fx in (tub.x + 18, tub.right - 26):
            pygame.draw.rect(surface, theme.DARK_GREY, (fx, tub.bottom, 8, 6))
        for i in range(12):
            bx = tub.x + 10 + i * 17
            pygame.draw.circle(surface, theme.WHITE, (bx, tub.top + 2 + (i % 2) * 3), 7)
            pygame.draw.circle(surface, theme.LIGHT_GREY, (bx, tub.top + 2 + (i % 2) * 3), 7, 1)

        if self.done:
            for i in range(5):
                a = self.t * 2 + i * 1.26
                sx = int(self._drawn_rect.centerx + math.cos(a) * 70)
                sy = int(self._drawn_rect.centery - 10 + math.sin(a) * 45)
                pygame.draw.line(surface, theme.YELLOW, (sx - 3, sy), (sx + 3, sy))
                pygame.draw.line(surface, theme.YELLOW, (sx, sy - 3), (sx, sy + 3))

        for x, y, _, r, life in self.bubbles:
            pygame.draw.circle(surface, theme.WHITE, (int(x), int(y)), r, 1)

        self.draw_speech(surface, (8, 40), 120, (self._drawn_rect.x + 40, self._drawn_rect.y + 30))
        super().draw(surface)
        self._draw_sponge(surface)

    def _draw_sponge(self, surface):
        x, y = self.sponge
        tilt = 2 if self.scrubbing and int(self.t * 12) % 2 else 0
        body = pygame.Rect(x - 12, y - 8 + tilt, 24, 16)
        pygame.draw.rect(surface, theme.BLACK, body.inflate(2, 2))
        pygame.draw.rect(surface, SPONGE, body)
        pygame.draw.rect(surface, theme.GREEN, (body.x, body.y, body.w, 4))
        for hx, hy in ((5, 8), (13, 11), (18, 7), (9, 13)):
            pygame.draw.rect(surface, (210, 170, 40), (body.x + hx, body.y + hy, 2, 2))
