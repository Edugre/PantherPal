"""Math games: counting, adding/subtracting, comparing."""
import pygame

from scenes.games.base import QuizGame, Round, number_options, spread_positions
from ui import icons, props, text, theme

LEVEL_COUNTS = {1: (1, 5), 2: (3, 8), 3: (5, 10)}


def fish_image():
    return props.get("fish", 2) or icons.icon(icons.FISH, 2)


def ball_image():
    return props.get("ball", 2) or icons.icon(icons.STAR, 2)


def place(rng, count, rect, size):
    """Non-overlapping positions; falls back to a tidy grid if the random fill can't fit."""
    spots = spread_positions(rng, count, rect, size)
    if len(spots) < count:
        per_row = max(1, rect.w // (size + 4))
        spots = [(rect.x + (i % per_row) * (size + 4), rect.y + (i // per_row) * (size + 4)) for i in range(count)]
    return spots


class CountFishGame(QuizGame):
    key, title, subject = "count_fish", "Count the Fish", "Math"

    def make_round(self, level):
        low, high = LEVEL_COUNTS[level]
        count = self.rng.randint(low, high)
        options, answer = number_options(self.rng, count, 1, 12)
        pond = pygame.Rect(self.VISUAL.x + 40, self.VISUAL.y + 12, self.VISUAL.w - 80, self.VISUAL.h - 40)
        size = max(fish_image().get_size())
        return Round("How many fish?", options, answer, {"fish": place(self.rng, count, pond, size)})

    def draw_visual(self, surface, rect, rnd):
        pond = rect.inflate(-16, -10)
        pygame.draw.ellipse(surface, (30, 110, 170), pond)
        pygame.draw.ellipse(surface, (60, 150, 210), pond, 3)
        img = fish_image()
        for i, (x, y) in enumerate(rnd.data["fish"]):
            bob = round(((self.t * 2 + i) % 2) - 1)
            surface.blit(img, (x, y + bob))


class PounceGame(QuizGame):
    key, title, subject = "pounce", "Panther Pounce", "Math"

    def make_round(self, level):
        subtract = level == 3 and self.rng.random() < 0.5
        if subtract:
            a = self.rng.randint(3, 10)
            b = self.rng.randint(1, a - 1)
            result, sign = a - b, "-"
        else:
            top = {1: 6, 2: 10, 3: 10}[level]
            a = self.rng.randint(1, top - 1)
            b = self.rng.randint(1, top - a)
            result, sign = a + b, "+"
        options, answer = number_options(self.rng, result, 0, 20)
        prompt = "How many in all?" if sign == "+" else "How many are left?"
        return Round(prompt, options, answer, {"a": a, "b": b, "sign": sign})

    def draw_visual(self, surface, rect, rnd):
        a, b, sign = rnd.data["a"], rnd.data["b"], rnd.data["sign"]
        text.draw(surface, f"{a} {sign} {b} = ?", (rect.centerx, rect.top + 28), text.HUGE, theme.WHITE, anchor="center")
        # Counting helpers: paw dots for each number, crossed out when taking away.
        size, gap = 10, 4
        dots = a + (b if sign == "+" else 0)
        total_w = dots * (size + gap) + (12 if sign == "+" else 0)
        x = rect.centerx - total_w // 2
        y = rect.top + 56
        for i in range(dots):
            second = sign == "+" and i >= a
            dx = x + i * (size + gap) + (12 if second else 0)
            color = theme.BLUE if second else theme.ORANGE
            pygame.draw.circle(surface, color, (dx + size // 2, y + size // 2), size // 2)
            if sign == "-" and i >= a - b:
                pygame.draw.line(surface, theme.RED, (dx - 1, y - 1), (dx + size, y + size), 2)
                pygame.draw.line(surface, theme.RED, (dx + size, y - 1), (dx - 1, y + size), 2)


class MoreGame(QuizGame):
    key, title, subject = "more", "Which Has More?", "Math"

    def make_round(self, level):
        high = {1: 5, 2: 8, 3: 10}[level]
        min_diff = {1: 2, 2: 1, 3: 1}[level]
        if self.rng.random() < 0.2:
            left = right = self.rng.randint(1, high)
        else:
            while True:
                left, right = self.rng.randint(1, high), self.rng.randint(1, high)
                if abs(left - right) >= min_diff:
                    break
        answer = 0 if left > right else 2 if right > left else 1
        explain = (f"They both have {left}!" if left == right
                   else f"{max(left, right)} is more than {min(left, right)}!")
        size = max(ball_image().get_size())
        half_w = (self.VISUAL.w - 30) // 2
        lrect = pygame.Rect(self.VISUAL.x + 10, self.VISUAL.y + 10, half_w - 10, self.VISUAL.h - 40)
        rrect = lrect.move(half_w + 10, 0)
        return Round("Which side has more?", ["Left", "Same", "Right"], answer,
                     {"left": place(self.rng, left, lrect, size), "right": place(self.rng, right, rrect, size)},
                     explain=explain)

    def draw_visual(self, surface, rect, rnd):
        pygame.draw.line(surface, theme.LAVENDER, (rect.centerx, rect.top + 6), (rect.centerx, rect.bottom - 6), 2)
        img = ball_image()
        for x, y in rnd.data["left"] + rnd.data["right"]:
            surface.blit(img, (x, y))
