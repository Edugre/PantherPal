"""Helper tools: timers, alarms, "is it hot inside?" and bedtime info."""
import time

import pygame

from core.reminders import (ALARM_LABELS, MAX_ALARMS, MAX_TIMERS, TIMER_PRESETS, format_clock,
                            format_duration, parse_hhmm)
from scenes.care import CareScene
from ui import text, theme
from ui.widgets import Button, panel

TABS = ["Timer", "Alarms", "Room", "Bedtime"]
TAB_COLOR, TAB_ACTIVE = (70, 90, 150), theme.ORANGE
AREA = pygame.Rect(94, 38, 300, 198)


def short_duration(seconds):
    return f"{seconds} sec" if seconds < 60 else f"{seconds // 60} min"


def room_words(reading):
    """(temperature words, humidity words) a 5-7 year old understands."""
    c = reading.temp_c
    if c >= 28:
        temp = "It's hot! Drink some water."
    elif c >= 25:
        temp = "It's warm. T-shirt weather!"
    elif c >= 18:
        temp = "It's just right!"
    else:
        temp = "It's chilly. Wear a sweater!"
    h = reading.humidity
    if h > 60:
        air = "The air is muggy, like the Everglades!"
    elif h < 30:
        air = "The air is dry."
    else:
        air = "The air feels comfy."
    return temp, air


class HelperScene(CareScene):
    title = "Helper"

    def __init__(self, app):
        super().__init__(app)
        self.reminders = app.reminders
        self.tab = "Timer"
        self.custom_minutes = 5
        self.alarm_hour, self.alarm_minute, self.alarm_pm = 7, 0, False
        self.alarm_label = 0
        self.note = ""
        self._note_left = 0.0
        self._counts = None
        self._build()

    # --- layout ---
    def _build(self):
        self.buttons = [self.back_button]
        for i, name in enumerate(TABS):
            color = TAB_ACTIVE if name == self.tab else TAB_COLOR
            self.buttons.append(Button((6, 40 + i * 36, 82, 30), name, lambda n=name: self._set_tab(n), color))
        getattr(self, f"_build_{self.tab.lower()}")()
        self._counts = (len(self.reminders.timers), len(self.reminders.alarms))

    def _set_tab(self, name):
        self.tab = name
        self.note = ""
        self._build()

    def _say(self, message):
        self.note, self._note_left = message, 3.0

    def _build_timer(self):
        for i, (label, seconds) in enumerate(TIMER_PRESETS):
            rect = (AREA.x + 4 + (i % 2) * 148, AREA.y + 4 + (i // 2) * 32, 144, 28)
            self.buttons.append(Button(rect, f"{label} {short_duration(seconds)}",
                                       lambda l=label, s=seconds: self._start_timer(l, s), theme.DARK_GREEN))
        y = AREA.y + 72
        self.buttons += [
            Button((AREA.x + 4, y, 28, 26), "-", lambda: self._step_custom(-1), theme.BLUE),
            Button((AREA.x + 96, y, 28, 26), "+", lambda: self._step_custom(1), theme.BLUE),
            Button((AREA.x + 132, y, 80, 26), "Start", lambda: self._start_timer("Timer", self.custom_minutes * 60),
                   theme.DARK_GREEN),
        ]
        for i in range(len(self.reminders.timers)):
            self.buttons.append(Button((AREA.right - 58, AREA.y + 112 + i * 28, 52, 24), "Stop",
                                       lambda i=i: self._stop_timer(i), theme.RED))

    def _build_alarms(self):
        y = AREA.y + 4
        self.buttons += [
            Button((AREA.x + 4, y, 26, 26), "-", lambda: self._step_alarm(hour=-1), theme.BLUE),
            Button((AREA.x + 66, y, 26, 26), "+", lambda: self._step_alarm(hour=1), theme.BLUE),
            Button((AREA.x + 106, y, 26, 26), "-", lambda: self._step_alarm(minute=-5), theme.BLUE),
            Button((AREA.x + 168, y, 26, 26), "+", lambda: self._step_alarm(minute=5), theme.BLUE),
            Button((AREA.x + 202, y, 44, 26), "PM" if self.alarm_pm else "AM", self._toggle_pm, theme.LAVENDER),
            Button((AREA.x + 4, y + 32, 150, 26), ALARM_LABELS[self.alarm_label], self._next_label, theme.PINK),
            Button((AREA.x + 160, y + 32, 96, 26), "Add alarm", self._add_alarm, theme.DARK_GREEN),
        ]
        for i in range(len(self.reminders.alarms)):
            self.buttons.append(Button((AREA.right - 32, AREA.y + 72 + i * 24, 26, 20), "X",
                                       lambda i=i: self._remove_alarm(i), theme.RED))

    def _build_room(self):
        pass

    def _build_bedtime(self):
        pass

    # --- actions ---
    def _start_timer(self, label, seconds):
        if self.reminders.add_timer(label, seconds):
            self._say("Timer started!" if label == "Timer" else f"{label} timer started!")
        else:
            self._say(f"You can only have {MAX_TIMERS} timers at once.")
        self._build()

    def _stop_timer(self, index):
        self.reminders.cancel_timer(index)
        self._build()

    def _step_custom(self, delta):
        self.custom_minutes = max(1, min(60, self.custom_minutes + delta))

    def _step_alarm(self, hour=0, minute=0):
        self.alarm_hour = (self.alarm_hour - 1 + hour) % 12 + 1
        self.alarm_minute = (self.alarm_minute + minute) % 60

    def _toggle_pm(self):
        self.alarm_pm = not self.alarm_pm
        self._build()

    def _next_label(self):
        self.alarm_label = (self.alarm_label + 1) % len(ALARM_LABELS)
        self._build()

    def _alarm_hhmm(self):
        hour = self.alarm_hour % 12 + (12 if self.alarm_pm else 0)
        return f"{hour:02d}:{self.alarm_minute:02d}"

    def _add_alarm(self):
        hhmm = self._alarm_hhmm()
        if self.reminders.add_alarm(hhmm, ALARM_LABELS[self.alarm_label]):
            self._say(f"Alarm set for {format_clock(parse_hhmm(hhmm))}!")
        else:
            self._say(f"That alarm is already set, or there are {MAX_ALARMS} already.")
        self._build()

    def _remove_alarm(self, index):
        self.reminders.remove_alarm(index)
        self._build()

    # --- loop ---
    def update(self, dt):
        super().update(dt)
        if self._note_left > 0:
            self._note_left -= dt
            if self._note_left <= 0:
                self.note = ""
        if (len(self.reminders.timers), len(self.reminders.alarms)) != self._counts:
            self._build()       # a timer finished elsewhere

    def draw(self, surface):
        surface.fill((40, 55, 95))
        self.draw_header(surface)
        panel(surface, AREA, (30, 42, 75))
        getattr(self, f"_draw_{self.tab.lower()}")(surface)
        super().draw(surface)
        if self.note:
            text.draw(surface, self.note, (AREA.centerx, AREA.bottom - 10), text.MEDIUM, theme.YELLOW, anchor="center")

    def _draw_timer(self, surface):
        y = AREA.y + 72
        text.draw(surface, f"{self.custom_minutes} min", (AREA.x + 64, y + 13), text.LARGE, anchor="center")
        timers = self.reminders.timers
        if not timers:
            text.draw(surface, "No timers running.", (AREA.centerx, AREA.y + 124), text.MEDIUM, theme.MUTED,
                      anchor="center")
        now = time.time()
        for i, timer in enumerate(timers):
            row = pygame.Rect(AREA.x + 4, AREA.y + 110 + i * 28, AREA.w - 8, 28)
            left = timer["end"] - now
            progress = 1 - left / timer["seconds"]
            pygame.draw.rect(surface, (50, 70, 120), (row.x, row.y + 2, int((row.w - 66) * progress), row.h - 4))
            text.draw(surface, timer["label"], (row.x + 6, row.centery), text.MEDIUM, anchor="midleft")
            text.draw(surface, format_duration(left), (row.right - 70, row.centery), text.LARGE, theme.YELLOW,
                      anchor="midright")

    def _draw_alarms(self, surface):
        y = AREA.y + 17
        text.draw(surface, str(self.alarm_hour), (AREA.x + 48, y), text.LARGE, anchor="center")
        text.draw(surface, ":", (AREA.x + 99, y), text.LARGE, anchor="center")
        text.draw(surface, f"{self.alarm_minute:02d}", (AREA.x + 150, y), text.LARGE, anchor="center")
        alarms = self.reminders.alarms
        if not alarms:
            text.draw(surface, "No alarms yet.", (AREA.centerx, AREA.y + 100), text.MEDIUM, theme.MUTED, anchor="center")
        for i, alarm in enumerate(alarms):
            row_y = AREA.y + 82 + i * 24
            text.draw(surface, format_clock(parse_hhmm(alarm["time"])), (AREA.x + 10, row_y), text.MEDIUM,
                      theme.YELLOW, anchor="midleft")
            text.draw(surface, alarm["label"], (AREA.x + 90, row_y), text.MEDIUM, anchor="midleft")

    def _draw_room(self, surface):
        reading = self.app.sensor.latest()
        if reading is None:
            text.draw(surface, "Checking the room...", AREA.center, text.LARGE, theme.MUTED, anchor="center")
            return
        unit = self.app.settings["temp_unit"]
        temp = reading.temp_f if unit == "F" else reading.temp_c
        # thermometer
        cx, top, bottom = AREA.x + 36, AREA.y + 20, AREA.bottom - 40
        pygame.draw.rect(surface, theme.WHITE, (cx - 7, top, 14, bottom - top), border_radius=7)
        pygame.draw.circle(surface, theme.WHITE, (cx, bottom), 13)
        level = max(0.1, min(1.0, (reading.temp_c - 10) / 25))
        fill_top = bottom - int((bottom - top - 8) * level)
        pygame.draw.rect(surface, theme.RED, (cx - 4, fill_top, 8, bottom - fill_top))
        pygame.draw.circle(surface, theme.RED, (cx, bottom), 10)

        temp_words, air_words = room_words(reading)
        x = AREA.x + 74
        text.draw(surface, f"{temp:.0f}°{unit}", (x, AREA.y + 30), text.HUGE, theme.YELLOW, anchor="midleft")
        for i, line in enumerate(text.wrap(temp_words, AREA.right - x - 8)):
            text.draw(surface, line, (x, AREA.y + 60 + i * 14), text.MEDIUM, anchor="midleft")
        text.draw(surface, f"Humidity {reading.humidity:.0f}%", (x, AREA.y + 104), text.LARGE, theme.BLUE,
                  anchor="midleft")
        for i, line in enumerate(text.wrap(air_words, AREA.right - x - 8)):
            text.draw(surface, line, (x, AREA.y + 128 + i * 14), text.MEDIUM, anchor="midleft")

    def _draw_bedtime(self, surface):
        settings = self.app.settings
        x = AREA.x + 14
        bed = format_clock(parse_hhmm(settings["bedtime"]))
        wake = format_clock(parse_hhmm(settings["wake_time"]))
        text.draw(surface, f"Bedtime:  {bed}", (x, AREA.y + 24), text.LARGE, theme.PINK, anchor="midleft")
        text.draw(surface, f"Wake up:  {wake}", (x, AREA.y + 52), text.LARGE, theme.YELLOW, anchor="midleft")
        if not settings.get("bedtime_enabled", True):
            status = "Bedtime is turned off."
        elif self.reminders.quiet_hours():
            status = "It's nighttime now. Shh!"
        else:
            minutes = self.reminders.minutes_until_bedtime()
            hours, mins = divmod(minutes, 60)
            parts = ([f"{hours} hour{'s' * (hours != 1)}"] if hours else []) + \
                    ([f"{mins} minute{'s' * (mins != 1)}"] if mins else [])
            status = "Bedtime is in " + " and ".join(parts) + "."
        text.draw(surface, status, (x, AREA.y + 90), text.MEDIUM, anchor="midleft")
        for i, line in enumerate(text.wrap("At bedtime Sunny goes to sleep until morning. "
                                           "A grown-up can change these times in Parent settings.", AREA.w - 28)):
            text.draw(surface, line, (x, AREA.y + 120 + i * 14), text.MEDIUM, theme.MUTED, anchor="midleft")
