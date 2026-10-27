"""Sunny's needs, mood and reactions.

All four stats run 0-100 where higher is better. They drain slowly in real
time; the design is deliberately forgiving for 5-7 year olds:
  * stats never drain below a floor, so Sunny can't "die" or get sick
  * while the device is off, draining runs at half speed and stops at a
    higher floor, so a child coming back the next day finds Sunny hungry,
    not miserable
"""
import random
import time

STATS = ("food", "clean", "fun", "energy")
STAT_LABELS = {"food": "Food", "clean": "Clean", "fun": "Fun", "energy": "Energy"}

DECAY_PER_HOUR = {"food": 6, "clean": 4, "fun": 8, "energy": 5}
SLEEP_DECAY_FACTOR = 0.3      # needs drain slower while asleep
SLEEP_ENERGY_PER_HOUR = 40
AWAKE_FLOOR = 10
OFFLINE_FACTOR = 0.5
OFFLINE_FLOOR = 30
MAX_CATCH_UP_HOURS = 48       # guards against big clock jumps (no RTC battery)
LOW = 25                      # below this a need drives Sunny's mood
FULL = 95                     # above this Sunny politely refuses more

HOT_C = 28
COLD_C = 16
MUGGY_RH = 75

PET_COOLDOWN = 5.0            # seconds between fun boosts from petting

NEED_MOODS = {"food": "hungry", "clean": "dirty", "fun": "bored", "energy": "sleepy"}

LINES = {
    "happy":    ["I feel great!", "You're my best friend!", "Let's play a game!", "Rawr! (that means hi)"],
    "ok":       ["Hi there!", "What should we do?", "Panthers love to explore!", "I live in Florida!"],
    "hungry":   ["My tummy is rumbling!", "Can I have a snack?", "I'm so hungry..."],
    "dirty":    ["I'm all muddy!", "Bath time, please?", "I rolled in the swamp!"],
    "bored":    ["I'm bored...", "Can we play a game?", "Let's do something fun!"],
    "sleepy":   ["*yawn* I'm sleepy...", "Can I take a nap?", "My eyes are heavy..."],
    "sleeping": ["Zzz...", "Zzz... fish... zzz"],
    "hot":      ["Phew, it's hot in here!", "I'm panting! It's warm!"],
    "cold":     ["Brrr! It's chilly!", "I need a warm blanket!"],
    "love":     ["Purrrr!", "Hee hee, that tickles!", "I love you too!"],
    "eating":   ["Yum yum yum!", "Crunch crunch!", "Delicious!"],
}
MUGGY_LINES = ["It's muggy, like the Everglades!", "So humid! Just like home!"]


class Pet:
    def __init__(self, stats=None, asleep=False, last_update=None):
        self.stats = {s: 80.0 for s in STATS}
        if stats:
            self.stats.update({k: float(v) for k, v in stats.items() if k in STATS})
        self.asleep = asleep
        self.last_update = last_update or time.time()

        # Transient state (not saved)
        self.reaction = None
        self._reaction_left = 0.0
        self.speech = None
        self._speech_left = 0.0
        self._speech_is_chatter = False
        self.climate = None          # "hot" | "cold" | "muggy" | None
        self._last_petted = 0.0
        self._last_mood = None

    # --- persistence ---
    @classmethod
    def from_dict(cls, data, now=None):
        pet = cls(data.get("stats"), data.get("asleep", False), data.get("last_update"))
        pet.catch_up(now or time.time())
        return pet

    def to_dict(self):
        return {"stats": self.stats, "asleep": self.asleep, "last_update": self.last_update}

    def catch_up(self, now):
        """Apply the time that passed while the app was not running."""
        hours = min(max(0.0, now - self.last_update) / 3600, MAX_CATCH_UP_HOURS)
        self._tick(hours, OFFLINE_FACTOR, OFFLINE_FLOOR)
        self.last_update = now

    # --- simulation ---
    def _tick(self, hours, factor, floor):
        if hours <= 0:
            return
        sleep_factor = SLEEP_DECAY_FACTOR if self.asleep else 1.0
        for stat in STATS:
            if stat == "energy" and self.asleep:
                continue
            current = self.stats[stat]
            drained = current - DECAY_PER_HOUR[stat] * factor * sleep_factor * hours
            # The floor stops draining; it never raises a stat that is already lower.
            self.stats[stat] = max(drained, min(current, floor))
        if self.asleep:
            self._change("energy", SLEEP_ENERGY_PER_HOUR * hours)

    def update(self, dt, reading=None):
        self._tick(dt / 3600, 1.0, AWAKE_FLOOR)
        self.last_update = time.time()

        if self.reaction:
            self._reaction_left -= dt
            if self._reaction_left <= 0:
                self.reaction = None
        if self.speech:
            self._speech_left -= dt
            if self._speech_left <= 0:
                self.speech = None

        self.climate = None
        if reading is not None:
            if reading.temp_c >= HOT_C:
                self.climate = "hot"
            elif reading.temp_c <= COLD_C:
                self.climate = "cold"
            elif reading.humidity >= MUGGY_RH:
                self.climate = "muggy"

        # Speak up whenever the mood changes (reactions already spoke in react()),
        # but never talk over something a scene deliberately said.
        mood = self.mood
        if mood != self._last_mood:
            self._last_mood = mood
            if mood != self.reaction and (not self.speech or self._speech_is_chatter):
                self.say(self.mood_line(), chatter=True)

    @property
    def mood(self):
        if self.asleep:
            return "sleeping"
        if self.reaction:
            return self.reaction
        lowest = min(STATS, key=self.stats.get)
        if self.stats[lowest] < LOW:
            return NEED_MOODS[lowest]
        if self.climate in ("hot", "cold"):
            return self.climate
        if sum(self.stats.values()) / len(STATS) >= 70:
            return "happy"
        return "ok"

    def mood_line(self):
        mood = self.mood
        if mood in ("happy", "ok") and self.climate == "muggy" and random.random() < 0.5:
            return random.choice(MUGGY_LINES)
        return random.choice(LINES[mood])

    # --- speech & reactions ---
    def say(self, text, seconds=4.0, chatter=False):
        """Show a speech bubble. Chatter (mood lines) may be replaced by
        later mood changes; anything else stays for its full time."""
        self.speech = text
        self._speech_left = seconds
        self._speech_is_chatter = chatter

    def react(self, reaction, seconds=2.0):
        self.reaction = reaction
        self._reaction_left = seconds
        self.say(random.choice(LINES[reaction]), seconds + 1, chatter=True)

    def _change(self, stat, amount):
        self.stats[stat] = max(0.0, min(100.0, self.stats[stat] + amount))

    # --- care actions (called by the care scenes) ---
    # Each returns True if Sunny accepted it, so scenes can award points.
    def can_eat(self):
        return not self.asleep and self.stats["food"] < FULL

    def feed(self, amount=25, fun=0):
        if self.asleep:
            self.say("Zzz... (Sunny is sleeping)")
            return False
        if self.stats["food"] >= FULL:
            self.say("I'm full! Thank you!")
            return False
        self._change("food", amount)
        self._change("fun", fun)
        self.react("eating")
        return True

    def wash(self, amount=40):
        if self.asleep:
            self.say("Zzz... (Sunny is sleeping)")
            return False
        if self.stats["clean"] >= FULL:
            self.say("I'm already squeaky clean!")
            return False
        self._change("clean", amount)
        self.react("love")
        return True

    def play(self, fun=20, energy_cost=8):
        if self.asleep:
            self.say("Zzz... (Sunny is sleeping)")
            return False
        self._change("fun", fun)
        self._change("energy", -energy_cost)
        self.react("love")
        return True

    def rest(self, amount):
        """Extra energy during a nap, on top of normal sleep recovery."""
        self._change("energy", amount)

    def go_to_sleep(self):
        self.asleep = True
        self.reaction = None
        self.say("Goodnight!", 2)

    def wake_up(self):
        self.asleep = False
        self.say("Good morning!" if self.stats["energy"] >= 60 else "*yawn* Still a bit tired...")

    def touch(self):
        """Child clicked on Sunny."""
        if self.asleep:
            self.say("Zzz... *snore*", 2)
            return
        now = time.time()
        if now - self._last_petted >= PET_COOLDOWN:
            self._last_petted = now
            self._change("fun", 2)
        self.react("love", 1.5)
