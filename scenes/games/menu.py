"""Pick a learning game. Shows each game's best result in stars."""
import pygame

from scenes.care import CareScene
from scenes.games.math_games import CountFishGame, MoreGame, PounceGame
from scenes.games.science_games import EatsGame, HotColdGame
from ui import icons, text, theme
from ui.sunny import draw_sunny, make_sunny_renderer
from ui.widgets import Button, panel

GAMES = [CountFishGame, PounceGame, MoreGame, EatsGame, HotColdGame]
SUBJECT_COLORS = {"Math": theme.BLUE, "Science": theme.DARK_GREEN}
TOO_TIRED = 15      # energy below this: Sunny wants a nap first


class GameCard(Button):
    def __init__(self, rect, game, best, on_click):
        super().__init__(rect, game.title, on_click, theme.PANEL)
        self.game, self.best = game, best

    def draw(self, surface):
        offset = 2 if self.pressed else 0
        body = self.rect.move(0, offset)
        if not self.pressed:
            pygame.draw.rect(surface, theme.BLACK, self.rect.move(0, 2))
        panel(surface, body, (45, 60, 100) if self.hover else theme.PANEL)
        tag = pygame.Rect(body.x + 6, body.y + 6, 50, 12)
        pygame.draw.rect(surface, SUBJECT_COLORS[self.game.subject], tag)
        text.draw(surface, self.game.subject, tag.center, text.SMALL, anchor="center")
        text.draw(surface, self.label, (body.centerx, body.y + 32), text.MEDIUM, theme.YELLOW, anchor="center")
        for i in range(3):
            star = icons.icon(icons.STAR if i < self.best else icons.STAR_EMPTY, 2)
            surface.blit(star, star.get_rect(center=(body.centerx - 18 + i * 18, body.bottom - 12)))


class GamesMenuScene(CareScene):
    title = "Games"

    def __init__(self, app):
        super().__init__(app)
        self.sunny = make_sunny_renderer(cell=3)
        sw, sh = self.sunny.size
        self.sunny_rect = pygame.Rect(10, 232 - sh, sw, sh)
        best = app.store.get("game_best", {})
        self.cards = []
        cw, ch, gap = 120, 66, 8
        for i, game in enumerate(GAMES):
            col, row = i % 3, i // 3
            per_row = min(3, len(GAMES) - row * 3)
            x0 = (400 - (per_row * cw + (per_row - 1) * gap)) // 2
            rect = (x0 + col * (cw + gap), 40 + row * (ch + gap), cw, ch)
            self.cards.append(GameCard(rect, game, best.get(game.key, 0), lambda g=game: self.start(g)))
        self.buttons += self.cards

    def on_enter(self):
        pet = self.app.pet
        if pet.stats["energy"] < TOO_TIRED:
            pet.say("I'm too sleepy to play... Can I take a nap first?", 4)
        else:
            pet.say("Let's play! Pick a game!", 3)

    def start(self, game):
        if self.app.pet.stats["energy"] < TOO_TIRED:
            self.app.pet.say("*yawn* Too sleepy! Let's nap first.", 3)
            return
        self.app.switch(game(self.app))

    def draw(self, surface):
        surface.fill((40, 55, 95))
        self.draw_header(surface)
        draw_sunny(surface, self.sunny, self.app.pet, self.sunny_rect, self.t)
        self.draw_speech(surface, (self.sunny_rect.right + 10, 190), 200,
                         (self.sunny_rect.right - 10, self.sunny_rect.top + 20))
        super().draw(surface)
