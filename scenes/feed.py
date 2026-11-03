"""Feed Sunny: pick a food, it flies to Sunny, then Sunny shares a fact.

Two "wrong" foods teach that panthers are carnivores. Treats cost stars
and also add a little Fun.
"""
import math

import pygame

import config
from scenes.care import CareScene
from ui import icons, props, text, theme
from ui.sunny import draw_sunny, make_sunny_renderer
from ui.widgets import Button, panel

FLY_TIME = 0.7
FACT_DELAY = 2.0

FOODS = [
    {"name": "Meat", "icon": icons.MEAT, "cost": 0, "food": 25,
     "fact": "Panthers are carnivores. That means they eat meat!"},
    {"name": "Broccoli", "icon": icons.BROCCOLI,
     "wrong": "No thanks! Panthers don't eat veggies. They eat meat!"},
    {"name": "Fish", "icon": icons.FISH, "prop": "fish", "cost": 0, "food": 20,
     "fact": "Panthers can swim, but they like to hunt on land!"},
    {"name": "Candy", "icon": icons.CANDY,
     "wrong": "Candy is not good for panthers. Or for teeth!"},
    {"name": "Fish Pop", "icon": icons.FISH_POP, "cost": 5, "food": 30, "fun": 10,
     "fact": "Baby panthers are called kittens. They have spots!"},
    {"name": "Big Steak", "icon": icons.STEAK, "cost": 10, "food": 50, "fun": 15,
     "fact": "Panthers hunt deer and wild hogs in the Everglades!"},
]


def food_image(food):
    """Hand-drawn prop when there is one, else the built-in pixel icon."""
    return (food.get("prop") and props.get(food["prop"], 2)) or icons.icon(food["icon"], 3)


class FoodCard(Button):
    def __init__(self, rect, food, on_click):
        super().__init__(rect, food["name"], on_click, theme.PANEL)
        self.food = food
        self.affordable = True

    def draw(self, surface):
        offset = 2 if self.pressed else 0
        body = self.rect.move(0, offset)
        if not self.pressed:
            pygame.draw.rect(surface, theme.BLACK, self.rect.move(0, 2))
        fill = (45, 60, 100) if self.hover else theme.PANEL
        panel(surface, body, fill)
        img = food_image(self.food)
        surface.blit(img, img.get_rect(center=(body.centerx, body.top + 20)))
        text.draw(surface, self.label, (body.centerx, body.bottom - 18), text.SMALL, anchor="center")
        cost = self.food.get("cost", 0)
        price = "Free" if cost == 0 else f"{cost} stars"
        color = theme.GREEN if cost == 0 else (theme.YELLOW if self.affordable else theme.RED)
        text.draw(surface, price, (body.centerx, body.bottom - 7), text.SMALL, color, anchor="center")
        if not self.affordable:
            veil = pygame.Surface(body.size, pygame.SRCALPHA)
            veil.fill((0, 0, 0, 110))
            surface.blit(veil, body)


class FeedScene(CareScene):
    title = "Feed Sunny"
    GROUND_Y = 200

    def __init__(self, app):
        super().__init__(app)
        self.sunny = make_sunny_renderer(cell=4)
        sw, sh = self.sunny.size
        self.sunny_rect = pygame.Rect(40, self.GROUND_Y - sh + 4, sw, sh)
        self.flying = None
        self.pending_fact = None
        self._fact_timer = 0.0

        self.cards = []
        cw, ch, gap = 92, 58, 6
        for i, food in enumerate(FOODS):
            col, row = i % 2, i // 2
            rect = (200 + col * (cw + gap), 40 + row * (ch + gap), cw, ch)
            card = FoodCard(rect, food, None)
            card.on_click = lambda c=card: self.choose(c)
            self.cards.append(card)
        self.buttons += self.cards

    def on_enter(self):
        pet = self.app.pet
        pet.say("What's for lunch?" if pet.can_eat() else "I'm full! Thank you!", 3)

    @property
    def mouth(self):
        mx, my = self.sunny.mouth
        return self.sunny_rect.x + mx, self.sunny_rect.y + my

    def choose(self, card):
        if self.flying:
            return
        food, pet = card.food, self.app.pet
        if "wrong" in food:
            pet.say(food["wrong"], 5)
            return
        cost = food.get("cost", 0)
        if cost > self.app.points:
            missing = cost - self.app.points
            pet.say(f"You need {missing} more stars! Play games to earn them.", 4)
            return
        if not pet.can_eat():
            pet.feed()          # Sunny explains (full / sleeping)
            return
        self.app.add_points(-cost)
        self.flying = {"food": food, "start": card.rect.center, "p": 0.0}
        self.pending_fact = None

    def update(self, dt):
        super().update(dt)
        for card in self.cards:
            card.affordable = card.food.get("cost", 0) <= self.app.points

        if self.flying:
            self.flying["p"] += dt / FLY_TIME
            if self.flying["p"] >= 1:
                food = self.flying["food"]
                self.flying = None
                if self.app.pet.feed(food["food"], food.get("fun", 0)):
                    self.reward()
                    self.pending_fact = food["fact"]
                    self._fact_timer = FACT_DELAY

        if self.pending_fact:
            self._fact_timer -= dt
            if self._fact_timer <= 0:
                self.app.pet.say(self.pending_fact, 6)
                self.pending_fact = None

    def draw(self, surface):
        w, h = config.LOGICAL_SIZE
        surface.fill((60, 90, 140))
        pygame.draw.rect(surface, theme.DARK_GREEN, (0, self.GROUND_Y, w, h - self.GROUND_Y))
        pygame.draw.rect(surface, (0, 100, 60), (0, self.GROUND_Y, w, 2))
        self.draw_header(surface)

        r = self.sunny_rect
        pygame.draw.ellipse(surface, (0, 90, 50), (r.x + 12, self.GROUND_Y - 2, r.w - 36, 8))
        draw_sunny(surface, self.sunny, self.app.pet, r, self.t)
        self.draw_speech(surface, (8, 38), 184, (r.x + 72, r.y + 18))

        super().draw(surface)

        if self.flying:
            p = self.flying["p"]
            (sx, sy), (ex, ey) = self.flying["start"], self.mouth
            x = sx + (ex - sx) * p
            y = sy + (ey - sy) * p - math.sin(p * math.pi) * 40
            img = food_image(self.flying["food"])
            surface.blit(img, img.get_rect(center=(int(x), int(y))))
