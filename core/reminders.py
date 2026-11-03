"""Timers, daily alarms and the bedtime routine.

check() is called about once a second with the current time and returns the
alerts that are due. The app decides what to do with them (show a pop-up,
put Sunny to sleep, ...). Everything is saved so it survives a restart.

Bedtime ("quiet hours") runs from settings["bedtime"] to settings["wake_time"]
and may cross midnight.
"""
import time
from dataclasses import dataclass

MAX_TIMERS = 3
MAX_ALARMS = 5
BEDTIME_WARNING_MIN = 10
STALE_TIMER = 10 * 60      # a timer that ended this long ago while the app was off is dropped

TIMER_PRESETS = [("Brush teeth", 120), ("Wash hands", 20), ("Tidy up", 5 * 60), ("Reading", 10 * 60)]
ALARM_LABELS = ["Wake up", "Snack time", "Get ready", "Play time", "Homework", "Medicine"]


@dataclass
class Alert:
    kind: str            # timer | alarm | bedtime_warning | bedtime | wake
    title: str
    message: str
    silent: bool = False   # True: act on it but don't pop up


def parse_hhmm(value):
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def format_clock(minutes_of_day):
    t = time.struct_time((2000, 1, 1, minutes_of_day // 60, minutes_of_day % 60, 0, 0, 1, -1))
    return time.strftime("%-I:%M %p", t)


def format_duration(seconds):
    seconds = max(0, int(seconds))
    return f"{seconds // 60}:{seconds % 60:02d}"


def friendly_duration(seconds):
    if seconds < 60:
        return f"{seconds} seconds"
    minutes = seconds // 60
    return f"{minutes} minute{'s' * (minutes != 1)}"


class Reminders:
    def __init__(self, store, settings):
        self.store = store
        self.settings = settings
        self.timers = store.get("timers", [])        # [{"label", "end", "seconds"}]
        self.alarms = store.get("alarms", [])        # [{"time": "HH:MM", "label"}]
        self.fired = store.get("reminders_fired", {})

    def save(self):
        self.store.set("timers", self.timers)
        self.store.set("alarms", self.alarms)
        self.store.set("reminders_fired", self.fired)

    # --- timers ---
    def add_timer(self, label, seconds, now=None):
        if len(self.timers) >= MAX_TIMERS:
            return False
        now = now or time.time()
        self.timers.append({"label": label, "end": now + seconds, "seconds": seconds})
        self.save()
        return True

    def cancel_timer(self, index):
        if 0 <= index < len(self.timers):
            del self.timers[index]
            self.save()

    # --- alarms ---
    def add_alarm(self, hhmm, label):
        if len(self.alarms) >= MAX_ALARMS or any(a["time"] == hhmm and a["label"] == label for a in self.alarms):
            return False
        self.alarms.append({"time": hhmm, "label": label})
        self.alarms.sort(key=lambda a: a["time"])
        self.save()
        return True

    def remove_alarm(self, index):
        if 0 <= index < len(self.alarms):
            del self.alarms[index]
            self.save()

    # --- bedtime ---
    def _minute_of_day(self, now):
        t = time.localtime(now)
        return t.tm_hour * 60 + t.tm_min

    def quiet_hours(self, now=None):
        if not self.settings.get("bedtime_enabled", True):
            return False
        now = now or time.time()
        minute = self._minute_of_day(now)
        bed, wake = parse_hhmm(self.settings["bedtime"]), parse_hhmm(self.settings["wake_time"])
        if bed <= wake:
            return bed <= minute < wake
        return minute >= bed or minute < wake

    def minutes_until_bedtime(self, now=None):
        minute = self._minute_of_day(now or time.time())
        return (parse_hhmm(self.settings["bedtime"]) - minute) % (24 * 60)

    def _night_key(self, now):
        """Date the current/most recent night started on (so 2 AM belongs to yesterday's night)."""
        t = time.localtime(now)
        if self._minute_of_day(now) < parse_hhmm(self.settings["wake_time"]):
            t = time.localtime(now - 24 * 3600)
        return time.strftime("%Y-%m-%d", t)

    # --- the check ---
    def check(self, now=None):
        now = now or time.time()
        alerts = []
        timers_before = len(self.timers)
        today = time.strftime("%Y-%m-%d", time.localtime(now))

        for timer in [t for t in self.timers if now >= t["end"]]:
            self.timers.remove(timer)
            if now - timer["end"] <= STALE_TIMER:
                what = "The timer is done!" if timer["label"] == "Timer" else f"{timer['label']} time is over!"
                alerts.append(Alert("timer", "Time's up!", f"{what} ({friendly_duration(timer['seconds'])})"))

        minute = self._minute_of_day(now)
        for alarm in self.alarms:
            key = f"alarm:{alarm['time']}:{alarm['label']}"
            if minute == parse_hhmm(alarm["time"]) and self.fired.get(key) != today:
                self.fired[key] = today
                alerts.append(Alert("alarm", alarm["label"], f"It's {format_clock(minute)}. {alarm['label']}!"))

        if self.settings.get("bedtime_enabled", True):
            night = self._night_key(now)
            if self.quiet_hours(now):
                if self.fired.get("bedtime") != night:
                    self.fired["bedtime"] = night
                    alerts.append(Alert("bedtime", "Bedtime!",
                                        "It's bedtime. Sunny is going to sleep. Goodnight!"))
            else:
                if 0 < self.minutes_until_bedtime(now) <= BEDTIME_WARNING_MIN and self.fired.get("warning") != today:
                    self.fired["warning"] = today
                    alerts.append(Alert("bedtime_warning", "Almost bedtime",
                                        f"Bedtime is in {self.minutes_until_bedtime(now)} minutes. "
                                        "Time to get ready!"))
                if self.fired.get("bedtime") and self.fired.get("woke") != self.fired["bedtime"]:
                    self.fired["woke"] = self.fired["bedtime"]
                    alerts.append(Alert("wake", "Good morning!", "Good morning!", silent=True))

        if alerts or len(self.timers) != timers_before:
            self.save()
        return alerts
