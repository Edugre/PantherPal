"""Chat with Sunny: clickable question bubbles plus a text box.

Every question goes through core.safety before the model sees it, and every
answer sentence is checked before it appears. All messages are written to
the chat log for the parent panel, with flagged ones marked.
"""
import random
import time

import pygame

import config
from core import llm, safety
from scenes.care import CareScene
from ui import text, theme
from ui.sunny import draw_sunny, make_sunny_renderer
from ui.widgets import Button

SUGGESTIONS = [
    "Why is the sky blue?", "What do you eat?", "Why do cats purr?", "How do fish breathe?",
    "What is a rainbow?", "Why is the sun hot?", "Tell me a joke!", "Why do leaves fall?",
    "How do birds fly?", "How are you?", "Where do you sleep?", "What is an alligator?",
    "Why does it rain?", "Is it hot in here?", "How big are you?", "What is a volcano?",
    "Why is snow cold?", "What is the moon?",
]
CHIP_TEXT = 14
LIMIT_REPLY = "I'm all talked out for today! Let's play a game or take a nap instead."
MAX_INPUT = safety.MAX_INPUT_CHARS
LINE_H = 13
BUBBLE_W = 200


def today_start():
    now = time.localtime()
    return time.mktime((now.tm_year, now.tm_mon, now.tm_mday, 0, 0, 0, 0, 0, -1))


class ChatScene(CareScene):
    title = "Chat with Sunny"
    captures_keyboard = True
    AREA = pygame.Rect(100, 36, 294, 138)

    def __init__(self, app):
        super().__init__(app)
        self.sunny = make_sunny_renderer(cell=3)
        sw, sh = self.sunny.size
        self.sunny_rect = pygame.Rect(50 - sw // 2, 172 - sh, sw, sh)
        self.client = app.chat_client
        # Conversation survives leaving and re-entering the screen (until restart).
        self.state = app.__dict__.setdefault("chat_state", {"messages": [], "history": []})
        self.input = ""
        self.scroll = 0
        self.pending = None

        self.send_button = Button((340, 202, 54, 30), "Send", self.send_typed, theme.DARK_GREEN)
        self.chips = []
        for i in range(3):
            chip = Button((6 + i * 130, 177, 126, 22), "", None, (70, 90, 150), CHIP_TEXT)
            chip.on_click = lambda c=chip: self.send(c.label)
            self.chips.append(chip)
        self.buttons += [self.send_button] + self.chips
        self._shuffle_chips()

    def _shuffle_chips(self):
        for chip, question in zip(self.chips, random.sample(SUGGESTIONS, len(self.chips))):
            chip.label = question

    # --- lifecycle ---
    def on_enter(self):
        pygame.key.start_text_input()
        pygame.key.set_repeat(400, 40)
        if not self.state["messages"]:
            self._add("sunny", "Hi! I'm Sunny. Ask me anything, or click a question!")

    def on_exit(self):
        self.client.cancel()
        if self.pending is not None:
            self._finish("Oops, I lost my thought!")
        pygame.key.stop_text_input()
        pygame.key.set_repeat()

    # --- sending ---
    def send_typed(self):
        self.send(self.input)

    def send(self, question):
        question = question.strip()
        if not question or self.pending is not None:
            return
        self.input = ""
        self.scroll = 0
        self._shuffle_chips()

        store = self.app.store
        if store.chat_count_since(today_start()) >= self.app.settings["daily_chat_limit"]:
            self._add("child", question)
            self._add("sunny", LIMIT_REPLY)
            return

        verdict = safety.check_input(question)
        store.log_chat("child", question, verdict.flagged)
        self._add("child", question)
        if not verdict.ok:
            store.log_chat("sunny", verdict.reply, verdict.flagged)
            self._add("sunny", verdict.reply)
            return

        self.pending = self._add("sunny", "")
        self.pending["question"] = question
        note = llm.context_note(self.app.pet, self.app.sensor.latest(), self.app.settings["temp_unit"], question)
        self.client.ask(self.state["history"], question, note)

    def _add(self, role, message):
        entry = {"role": role, "text": message}
        self.state["messages"].append(entry)
        del self.state["messages"][:-40]
        return entry

    def _finish(self, replacement=None, flagged=False):
        entry, self.pending = self.pending, None
        if replacement is not None:
            entry["text"] = replacement
        self.app.store.log_chat("sunny", entry["text"], flagged)
        if replacement is None:
            self.state["history"] += [{"role": "user", "content": entry["question"]},
                                      {"role": "assistant", "content": entry["text"]}]
            self.app.pet.chat()

    # --- events ---
    def handle_event(self, event):
        if event.type == pygame.TEXTINPUT:
            typed = "".join(ch for ch in event.text if ch.isprintable())
            self.input = (self.input + typed)[:MAX_INPUT]
            return True
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.input = self.input[:-1]
                return True
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.send_typed()
                return True
        if event.type == pygame.MOUSEWHEEL:
            self.scroll = max(0, self.scroll + event.y * 12)
            return True
        return super().handle_event(event)

    def update(self, dt):
        super().update(dt)
        while not self.client.events.empty():
            kind, payload = self.client.events.get_nowait()
            if self.pending is None:
                continue
            if kind == "sentence":
                self.pending["text"] = f"{self.pending['text']} {payload}".strip()
            elif kind == "done":
                self._finish(None if self.pending["text"] else llm.FALLBACK_OFFLINE)
            elif kind == "blocked":
                self._finish(payload, flagged=True)
            elif kind == "error":
                self._finish(payload)
        busy = self.pending is not None
        for chip in self.chips:
            chip.color = theme.DARK_GREY if busy else (70, 90, 150)
        self.send_button.color = theme.DARK_GREY if busy or not self.input.strip() else theme.DARK_GREEN

    # --- drawing ---
    def draw(self, surface):
        w, h = config.LOGICAL_SIZE
        surface.fill((40, 55, 95))
        pygame.draw.rect(surface, theme.DARK_GREEN, (0, 172, 98, 4))
        self.draw_header(surface)
        draw_sunny(surface, self.sunny, self.app.pet, self.sunny_rect, self.t)
        if self.pending is not None:
            text.draw(surface, "thinking" + "." * (int(self.t * 3) % 4), (50, self.sunny_rect.top - 8),
                      text.SMALL, theme.YELLOW, anchor="center")
        self._draw_messages(surface)
        self._draw_input(surface)
        super().draw(surface)

    def _draw_messages(self, surface):
        area = self.AREA
        pygame.draw.rect(surface, (30, 42, 75), area)
        surface.set_clip(area)
        bubbles = []
        for entry in self.state["messages"]:
            message = entry["text"] or "." * (1 + int(self.t * 3) % 3)
            lines = text.wrap(message, BUBBLE_W - 12)
            width = max(text.font(text.MEDIUM).size(line)[0] for line in lines) + 12
            bubbles.append((entry["role"], lines, width, len(lines) * LINE_H + 8))

        total = sum(b[3] + 4 for b in bubbles)
        self.scroll = min(self.scroll, max(0, total - area.h + 4))
        y = area.bottom - 4 + self.scroll
        for role, lines, width, height in reversed(bubbles):
            y -= height
            if y + height < area.top:
                break
            child = role == "child"
            box = pygame.Rect(area.right - 4 - width if child else area.left + 4, y, width, height)
            pygame.draw.rect(surface, theme.BLUE if child else theme.WHITE, box, border_radius=4)
            pygame.draw.rect(surface, theme.BLACK, box, 1, border_radius=4)
            for i, line in enumerate(lines):
                text.draw(surface, line, (box.x + 6, box.y + 4 + i * LINE_H), text.MEDIUM,
                          theme.WHITE if child else theme.BLACK, shadow=child)
            y -= 4
        surface.set_clip(None)
        pygame.draw.rect(surface, theme.BLACK, area, 1)

    def _draw_input(self, surface):
        box = pygame.Rect(6, 202, 330, 30)
        pygame.draw.rect(surface, theme.BLACK, box.inflate(2, 2))
        pygame.draw.rect(surface, theme.WHITE, box)
        f = text.font(text.MEDIUM)
        shown = self.input
        while shown and f.size(shown)[0] > box.w - 16:
            shown = shown[1:]
        if shown:
            text.draw(surface, shown, (box.x + 6, box.centery), text.MEDIUM, theme.BLACK, anchor="midleft", shadow=False)
        else:
            text.draw(surface, "Type a question...", (box.x + 6, box.centery), text.MEDIUM,
                      theme.LIGHT_GREY, anchor="midleft", shadow=False)
        if int(self.t * 2) % 2 == 0:
            cx = box.x + 7 + f.size(shown)[0]
            pygame.draw.rect(surface, theme.BLACK, (cx, box.y + 7, 2, box.h - 14))
