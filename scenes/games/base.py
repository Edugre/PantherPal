"""Shared engine for the learning games.

Each game is a short quiz: ROUNDS questions with 2-3 answer buttons.
  * a wrong first try gets a second try for half credit, then the answer is shown
  * difficulty level (1-3) goes up after two right answers in a row, down after a miss
  * results: 1-3 stars (never zero, effort counts), converted to points, plus
    Fun for Sunny; the result is logged for the parent panel

Subclasses implement make_round(level) and draw_visual(surface, rect, rnd).
"""
import random
from dataclasses import dataclass, field

import pygame

import config
from scenes.care import CareScene
from ui import icons, text, theme
from ui.sunny import draw_sunny, make_sunny_renderer
from ui.widgets import Button, panel

ROUNDS = 6
FIRST_TRY, SECOND_TRY = 2, 1
POINTS_PER_STAR = 2
GAME_FUN, GAME_ENERGY = 15, 8
FEEDBACK_SECONDS = 1.2
REVEAL_SECONDS = 2.0

PRAISE = ["Great job!", "You got it!", "Awesome!", "Rawr-some!", "Super!", "Way to go!"]
TRY_AGAIN = ["Almost! Try again!", "Not quite, try once more!", "Oops! One more try!"]

OPTION_COLOR = (70, 90, 150)


@dataclass
class Round:
    prompt: str
    options: list                   # button labels
    answer: int                     # index of the right option
    data: dict = field(default_factory=dict)
    option_icons: list = None       # optional surfaces drawn above labels
    explain: str = ""               # shown after the round (a little lesson)


def stars_for(score, max_score):
    ratio = score / max_score
    return 3 if ratio >= 0.8 else 2 if ratio >= 0.5 else 1


class OptionButton(Button):
    def __init__(self, rect, on_click):
        super().__init__(rect, "", on_click, OPTION_COLOR, text.LARGE)
        self.icon = None
        self.enabled = True

    def handle_event(self, event):
        return self.enabled and super().handle_event(event)

    def draw(self, surface):
        if not self.icon:
            super().draw(surface)
            return
        # Icon and word side by side, centred together.
        label, self.label = self.label, ""
        super().draw(surface)
        self.label = label
        body = self.rect.move(0, 2 if self.pressed else 0)
        word = text.render(label, self.text_size)
        gap = 4
        x = body.centerx - (self.icon.get_width() + gap + word.get_width()) // 2
        surface.blit(self.icon, self.icon.get_rect(midleft=(x, body.centery)))
        text.draw(surface, label, (x + self.icon.get_width() + gap, body.centery), self.text_size, anchor="midleft")


class QuizGame(CareScene):
    key = ""            # id used for best scores and the game log
    subject = ""        # "Math" or "Science"
    captures_keyboard = True      # number keys answer (and don't trigger debug keys)
    VISUAL = pygame.Rect(8, 62, 384, 112)

    def __init__(self, app):
        super().__init__(app)
        self.rng = random.Random()
        self.sunny = make_sunny_renderer(cell=2)
        sw, sh = self.sunny.size
        self.sunny_rect = pygame.Rect(34 - sw // 2, 234 - sh, sw, sh)
        self.level = 1
        self.streak = 0
        self.round_no = 0
        self.score = 0
        self.history = []           # per round: 2, 1 or 0
        self.state = "question"     # question | feedback | results
        self.feedback = ""
        self.feedback_color = theme.TEXT
        self._timer = 0.0
        self.option_buttons = []
        self.back_button.on_click = self.leave
        self.again_button = Button((110, 186, 100, 36), "Play again", self.restart, theme.DARK_GREEN)
        self.menu_button = Button((220, 186, 100, 36), "Games", self.to_menu, theme.BLUE)
        self.next_round()

    # --- to implement ---
    def make_round(self, level):
        raise NotImplementedError

    def draw_visual(self, surface, rect, rnd):
        pass

    # --- flow ---
    def to_menu(self):
        from scenes.games.menu import GamesMenuScene
        self.app.switch(GamesMenuScene(self.app))

    def leave(self):
        self.to_menu()

    def restart(self):
        self.app.switch(type(self)(self.app))

    def next_round(self):
        self.round_no += 1
        self.tries = 0
        self.rnd = self.make_round(self.level)
        count = len(self.rnd.options)
        width, gap = (96, 8) if count == 3 else (130, 16)
        total = count * width + (count - 1) * gap
        x0 = 70 + (324 - total) // 2
        self.option_buttons = []
        for i, label in enumerate(self.rnd.options):
            button = OptionButton((x0 + i * (width + gap), 186, width, 44), lambda i=i: self.choose(i))
            button.label = label
            if self.rnd.option_icons:
                button.icon = self.rnd.option_icons[i]
            self.option_buttons.append(button)
        self.buttons = [self.back_button] + self.option_buttons
        self.state = "question"
        self.feedback = ""

    def choose(self, index):
        if self.state != "question":
            return
        self.tries += 1
        button = self.option_buttons[index]
        if index == self.rnd.answer:
            earned = FIRST_TRY if self.tries == 1 else SECOND_TRY
            self.score += earned
            self.history.append(earned)
            button.color = theme.DARK_GREEN
            self._set_feedback(self.rng.choice(PRAISE), theme.GREEN)
            self.app.pet.react("love", FEEDBACK_SECONDS)
            self._adjust_level(correct=self.tries == 1)
            self._finish_round(FEEDBACK_SECONDS)
        elif self.tries == 1:
            button.color, button.enabled = theme.RED, False
            self._set_feedback(self.rng.choice(TRY_AGAIN), theme.ORANGE)
        else:
            button.color = theme.RED
            self.option_buttons[self.rnd.answer].color = theme.DARK_GREEN
            self.history.append(0)
            self._set_feedback(f"The answer is {self.rnd.options[self.rnd.answer]}!", theme.YELLOW)
            self._adjust_level(correct=False)
            self._finish_round(REVEAL_SECONDS)
        for b in self.option_buttons:
            b.enabled = b.enabled and self.state == "question"

    def _set_feedback(self, message, color):
        self.feedback, self.feedback_color = message, color

    def _finish_round(self, seconds):
        if self.rnd.explain:
            self.feedback = f"{self.feedback} {self.rnd.explain}"
            seconds += 1.5
        self.state = "feedback"
        self._timer = seconds

    def _adjust_level(self, correct):
        if correct:
            self.streak += 1
            if self.streak >= 2 and self.level < 3:
                self.level += 1
                self.streak = 0
        else:
            self.streak = 0
            self.level = max(1, self.level - 1)

    def _show_results(self):
        max_score = ROUNDS * FIRST_TRY
        self.stars = stars_for(self.score, max_score)
        self.earned_points = self.stars * POINTS_PER_STAR
        self.app.add_points(self.earned_points)
        self.app.store.log_game(self.key, self.score, max_score, self.earned_points)
        best = self.app.store.get("game_best", {})
        self.new_best = self.stars > best.get(self.key, 0)
        if self.new_best:
            best[self.key] = self.stars
            self.app.store.set("game_best", best)
        self.app.pet.play(GAME_FUN, GAME_ENERGY)
        self.app.pet.say({3: "You're a superstar!", 2: "Great playing!", 1: "Good try! Let's play again!"}[self.stars], 5)
        self.state = "results"
        self.buttons = [self.back_button, self.again_button, self.menu_button]

    # --- events / update ---
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and self.state == "question":
            index = event.key - pygame.K_1
            if 0 <= index < len(self.option_buttons) and self.option_buttons[index].enabled:
                self.choose(index)
                return True
        return super().handle_event(event)

    def update(self, dt):
        super().update(dt)
        if self.state == "feedback":
            self._timer -= dt
            if self._timer <= 0:
                if self.round_no >= ROUNDS:
                    self._show_results()
                else:
                    self.next_round()

    # --- drawing ---
    def draw(self, surface):
        surface.fill((40, 55, 95))
        self.draw_header(surface)
        if self.state == "results":
            self._draw_results(surface)
        else:
            text.draw(surface, self.rnd.prompt, (200, 48), text.LARGE, theme.YELLOW, anchor="center")
            panel(surface, self.VISUAL, (30, 42, 75))
            surface.set_clip(self.VISUAL.inflate(-4, -4))
            self.draw_visual(surface, self.VISUAL, self.rnd)
            surface.set_clip(None)
            self._draw_progress(surface)
            if self.feedback:
                self._draw_feedback(surface)
        draw_sunny(surface, self.sunny, self.app.pet, self.sunny_rect, self.t)
        super().draw(surface)

    def _draw_feedback(self, surface):
        """Banner across the bottom of the picture area."""
        lines = text.wrap(self.feedback, self.VISUAL.w - 20, text.MEDIUM)[:2]
        band = pygame.Rect(self.VISUAL.x + 2, 0, self.VISUAL.w - 4, len(lines) * 13 + 8)
        band.bottom = self.VISUAL.bottom - 2
        shade = pygame.Surface(band.size, pygame.SRCALPHA)
        shade.fill((0, 0, 0, 190))
        surface.blit(shade, band)
        for i, line in enumerate(lines):
            text.draw(surface, line, (band.centerx, band.top + 10 + i * 13), text.MEDIUM,
                      self.feedback_color, anchor="center")

    def _draw_progress(self, surface):
        top = self.VISUAL.top + 5
        for i in range(ROUNDS):
            x = self.VISUAL.right - 8 - (ROUNDS - i) * 10
            done = i < len(self.history)
            color = (theme.GREEN if self.history[i] == FIRST_TRY else theme.YELLOW if self.history[i] else theme.RED) \
                if done else (theme.WHITE if i == self.round_no - 1 else theme.DARK_GREY)
            pygame.draw.rect(surface, theme.BLACK, (x - 1, top - 1, 9, 9))
            pygame.draw.rect(surface, color, (x, top, 7, 7))
        text.draw(surface, self.subject, (self.VISUAL.left + 6, top + 4), text.SMALL, theme.MUTED, anchor="midleft")

    def _draw_results(self, surface):
        box = panel(surface, (70, 44, 260, 136))
        text.draw(surface, "All done!", (box.centerx, box.top + 16), text.LARGE, theme.YELLOW, anchor="center")
        for i in range(3):
            star = icons.icon(icons.STAR if i < self.stars else icons.STAR_EMPTY, 5)
            surface.blit(star, star.get_rect(center=(box.centerx - 50 + i * 50, box.top + 56)))
        text.draw(surface, f"You got {self.history.count(FIRST_TRY)} of {ROUNDS} on the first try!",
                  (box.centerx, box.top + 90), text.MEDIUM, anchor="center")
        text.draw(surface, f"+{self.earned_points} stars" + ("   New best!" if self.new_best else ""),
                  (box.centerx, box.top + 110), text.MEDIUM, theme.GREEN, anchor="center")


def spread_positions(rng, count, rect, size, tries=200):
    """Up to `count` top-left positions for size x size items inside rect, not overlapping."""
    placed = []
    for _ in range(tries):
        if len(placed) == count:
            break
        x = rng.randint(rect.left, rect.right - size)
        y = rng.randint(rect.top, rect.bottom - size)
        if all(abs(x - px) >= size + 2 or abs(y - py) >= size + 2 for px, py in placed):
            placed.append((x, y))
    return placed


def number_options(rng, answer, low=0, high=20, count=3):
    """`count` shuffled distinct numbers near `answer`, including it."""
    options = {answer}
    while len(options) < count:
        candidate = answer + rng.choice([-3, -2, -1, 1, 2, 3])
        if low <= candidate <= high:
            options.add(candidate)
    options = sorted(options)
    return [str(o) for o in options], options.index(answer)
