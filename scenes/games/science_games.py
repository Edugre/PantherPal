"""Science games: what animals eat, and hot vs cold (with the real room sensor)."""
import pygame

from scenes.games.base import ROUNDS, QuizGame, Round
from ui import icons, props, text, theme

# (animal, what it eats). Kept to animals young kids know, plus a few from Florida.
ANIMALS = [
    ("panther", "Meat"), ("alligator", "Meat"), ("owl", "Meat"), ("shark", "Meat"), ("eagle", "Meat"),
    ("deer", "Plants"), ("rabbit", "Plants"), ("manatee", "Plants"), ("cow", "Plants"), ("horse", "Plants"),
    ("raccoon", "Both"), ("bear", "Both"), ("pig", "Both"), ("chicken", "Both"), ("monkey", "Both"),
]
DIET_WORD = {"Meat": "a carnivore", "Plants": "an herbivore", "Both": "an omnivore"}
DIET_SAYS = {"Meat": "eats meat", "Plants": "eats plants", "Both": "eats meat and plants"}

ITEMS = [
    ("the sun", icons.SUN, "Hot"), ("a campfire", icons.FIRE, "Hot"), ("hot cocoa", icons.COCOA, "Hot"),
    ("an ice cube", icons.ICE, "Cold"), ("a snowman", icons.SNOWMAN, "Cold"), ("ice cream", icons.ICE_CREAM, "Cold"),
]
WARM_C = 21     # 70 °F and up counts as warm for the room question


def article(word):
    return f"an {word}" if word[0] in "aeiou" else f"a {word}"


class EatsGame(QuizGame):
    key, title, subject = "eats", "Who Eats What?", "Science"

    def __init__(self, app):
        self.unused = []
        super().__init__(app)

    def make_round(self, level):
        if not self.unused:
            self.unused = list(ANIMALS)
            self.rng.shuffle(self.unused)
        animal, diet = self.unused.pop()
        options = ["Meat", "Plants", "Both"]
        both = pygame.Surface((26, 24), pygame.SRCALPHA)
        both.blit(icons.icon(icons.MEAT, 1), (0, 0))
        both.blit(icons.icon(icons.BROCCOLI, 1), (14, 10))
        option_icons = [icons.icon(icons.MEAT, 2), icons.icon(icons.BROCCOLI, 2), both]
        name = article(animal)
        explain = f"{name.capitalize()} {DIET_SAYS[diet]}, so it's {DIET_WORD[diet]}!"
        return Round(f"What does {name} eat?", options, options.index(diet),
                     {"animal": animal}, option_icons=option_icons, explain=explain)

    def draw_visual(self, surface, rect, rnd):
        animal = rnd.data["animal"]
        art = props.get(animal, 3)      # hand-drawn animal, if one is in assets/props/
        if art:
            surface.blit(art, art.get_rect(center=(rect.centerx, rect.centery - 12)))
        else:
            text.draw(surface, animal.capitalize(), (rect.centerx, rect.centery - 14), text.HUGE + 12,
                      theme.ORANGE, anchor="center")


class HotColdGame(QuizGame):
    key, title, subject = "hot_cold", "Hot or Cold?", "Science"

    def __init__(self, app):
        self.unused = []
        super().__init__(app)

    def make_round(self, level):
        reading = self.app.sensor.latest()
        if self.round_no == ROUNDS and reading is not None:
            return self._room_round(reading)
        if not self.unused:
            self.unused = list(ITEMS)
            self.rng.shuffle(self.unused)
        name, icon, answer = self.unused.pop()
        return Round(f"Is {name} hot or cold?", ["Hot", "Cold"], ["Hot", "Cold"].index(answer),
                     {"icon": icon})

    def _room_round(self, reading):
        unit = self.app.settings["temp_unit"]
        temp = reading.temp_f if unit == "F" else reading.temp_c
        warm = reading.temp_c >= WARM_C
        explain = f"Our room is {temp:.0f}°{unit}. That's {'warm' if warm else 'cool'}!"
        return Round("Feel the air! Is our room warm or cool?", ["Warm", "Cool"], 0 if warm else 1,
                     {"room": reading.temp_c, "label": f"{temp:.0f}°{unit}"}, explain=explain)

    def draw_visual(self, surface, rect, rnd):
        if "room" in rnd.data:
            self._draw_thermometer(surface, rect, rnd)
            return
        img = icons.icon(rnd.data["icon"], 6)
        surface.blit(img, img.get_rect(center=(rect.centerx, rect.centery - 10)))

    def _draw_thermometer(self, surface, rect, rnd):
        cx, top, bottom = rect.centerx, rect.top + 10, rect.bottom - 34
        pygame.draw.rect(surface, theme.WHITE, (cx - 6, top, 12, bottom - top), border_radius=6)
        pygame.draw.circle(surface, theme.WHITE, (cx, bottom), 11)
        level = max(0.1, min(1.0, (rnd.data["room"] - 10) / 25))       # 10-35 °C scale
        fill_top = bottom - int((bottom - top - 6) * level)
        pygame.draw.rect(surface, theme.RED, (cx - 3, fill_top, 6, bottom - fill_top))
        pygame.draw.circle(surface, theme.RED, (cx, bottom), 8)
        if self.state != "question":        # reveal the number with the answer
            text.draw(surface, rnd.data["label"], (cx + 22, fill_top), text.LARGE, theme.YELLOW, anchor="midleft")
