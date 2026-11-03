"""Home screen: Sunny in the Everglades, need bars, speech bubble, menu."""
import math
import random
import time

import pygame

import config
from core.pet import STAT_LABELS, STATS, LOW
from scenes.base import Scene
from ui import text, theme
from ui.sunny import draw_sunny, make_sunny_renderer
from ui.widgets import Button, panel, points_badge, speech_bubble

GROUND_Y = 162
STAT_COLORS = {"food": theme.ORANGE, "clean": theme.BLUE, "fun": theme.PINK, "energy": theme.YELLOW}
IDLE_CHATTER_EVERY = 25.0


def sky_for_hour(hour):
    """(sky colour, is_night) for the current hour."""
    if 7 <= hour < 17:
        return (90, 170, 230), False
    if 17 <= hour < 20 or 6 <= hour < 7:
        return (190, 110, 120), False
    return theme.NAVY, True


class HomeScene(Scene):
    MENU = ["Feed", "Clean", "Sleep", "Games", "Chat", "Helper"]
    MENU_COLORS = [theme.ORANGE, theme.BLUE, theme.LAVENDER, theme.DARK_GREEN, theme.PINK, theme.BROWN]

    def __init__(self, app):
        super().__init__(app)
        self.t = 0.0
        self.sunny = make_sunny_renderer(cell=4)
        self._chatter_timer = IDLE_CHATTER_EVERY
        w, h = config.LOGICAL_SIZE
        bw, gap = 60, 5
        x = (w - (bw * len(self.MENU) + gap * (len(self.MENU) - 1))) // 2
        self.buttons = []
        for i, (name, color) in enumerate(zip(self.MENU, self.MENU_COLORS)):
            self.buttons.append(Button((x + i * (bw + gap), h - 40, bw, 32), name,
                                       lambda n=name: self._menu(n), color))
        self.sleep_button = self.buttons[self.MENU.index("Sleep")]

        sw, sh = self.sunny.size
        self.sunny_rect = pygame.Rect((w - sw) // 2 + 8, GROUND_Y - sh + 4, sw, sh)

        rng = random.Random(7)
        self.stars = [(rng.randrange(w), rng.randrange(36, 120)) for _ in range(40)]
        self.grass = [(rng.randrange(w), rng.randrange(GROUND_Y + 4, h - 46)) for _ in range(24)]

    def _menu(self, name):
        if name == "Sleep" and self.app.pet.asleep:
            self.app.pet.wake_up()
        else:
            self.app.open_scene(name)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 \
                and self.sunny_rect.collidepoint(event.pos):
            self.app.pet.touch()
            return True
        return super().handle_event(event)

    def update(self, dt):
        self.t += dt
        pet = self.app.pet
        self.sleep_button.label = "Wake" if pet.asleep else "Sleep"
        self._chatter_timer -= dt
        if self._chatter_timer <= 0:
            self._chatter_timer = IDLE_CHATTER_EVERY
            if not pet.speech:
                pet.say(pet.mood_line(), chatter=True)

    # --- drawing ---
    def draw(self, surface):
        pet = self.app.pet
        self._draw_background(surface, pet.asleep)
        self._draw_top_bar(surface)
        self._draw_stats(surface)

        shadow = pygame.Rect(0, 0, self.sunny_rect.w - 24, 8)
        shadow.midtop = (self.sunny_rect.centerx - 6, GROUND_Y - 2)
        pygame.draw.ellipse(surface, (0, 90, 50), shadow)
        draw_sunny(surface, self.sunny, pet, self.sunny_rect, self.t)

        if pet.speech:
            w, _ = config.LOGICAL_SIZE
            tip = (self.sunny_rect.right - 22, self.sunny_rect.top + 22)
            speech_bubble(surface, pet.speech, (w - 126, 40), 120, tip)
        super().draw(surface)

    def _draw_background(self, surface, asleep):
        w, h = config.LOGICAL_SIZE
        sky, night = sky_for_hour(time.localtime().tm_hour)
        if asleep:
            sky, night = theme.NAVY, True
        surface.fill(sky)
        if night:
            for i, (x, y) in enumerate(self.stars):
                if (int(self.t * 2) + i) % 7:      # gentle twinkle
                    surface.set_at((x, y), theme.WHITE)
            pygame.draw.circle(surface, theme.LIGHT_GREY, (136, 56), 10)
            pygame.draw.circle(surface, sky, (141, 52), 9)
        else:
            pygame.draw.circle(surface, theme.YELLOW, (136, 56), 11)

        # distant cypress tree line
        for i in range(0, w, 16):
            th = 10 + (i * 37 % 13)
            pygame.draw.rect(surface, (0, 100, 60), (i, GROUND_Y - th, 12, th))
        pygame.draw.rect(surface, theme.DARK_GREEN, (0, GROUND_Y, w, h - GROUND_Y))
        pygame.draw.rect(surface, (0, 100, 60), (0, GROUND_Y, w, 2))
        for x, y in self.grass:     # sawgrass tufts
            for dx in (-2, 0, 2):
                pygame.draw.line(surface, theme.GREEN, (x, y), (x + dx, y - 4))

    def _draw_top_bar(self, surface):
        w, _ = config.LOGICAL_SIZE
        panel(surface, (4, 4, w - 8, 28))
        text.draw(surface, time.strftime("%-I:%M %p"), (12, 18), text.MEDIUM, anchor="midleft")
        points_badge(surface, (w // 2, 18), self.app.points)

        reading = self.app.sensor.latest()
        if reading is None:
            climate = "Room: ..." if self.app.sensor.status != "offline" else "No sensor"
        else:
            unit = self.app.settings["temp_unit"]
            temp = reading.temp_f if unit == "F" else reading.temp_c
            climate = f"{temp:.0f}°{unit}  {reading.humidity:.0f}%"
        text.draw(surface, climate, (w - 12, 18), text.MEDIUM, theme.BLUE, anchor="midright")

    def _draw_stats(self, surface):
        box = panel(surface, (6, 38, 104, 92))
        text.draw(surface, config.PET_NAME, (box.centerx, box.top + 10), text.MEDIUM, theme.YELLOW, anchor="center")
        segments, seg_w = 10, 5
        for i, stat in enumerate(STATS):
            y = box.top + 22 + i * 17
            value = self.app.pet.stats[stat]
            low = value < LOW
            label_color = theme.RED if low and int(self.t * 3) % 2 else theme.TEXT
            text.draw(surface, STAT_LABELS[stat], (box.left + 6, y), text.SMALL, label_color)
            filled = math.ceil(value / 100 * segments)
            for s in range(segments):
                r = (box.left + 38 + s * (seg_w + 1), y + 1, seg_w, 8)
                color = (theme.RED if low else STAT_COLORS[stat]) if s < filled else theme.DARK_GREY
                pygame.draw.rect(surface, color, r)
