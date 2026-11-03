#!/usr/bin/env python3
"""Sunny the Panther: entry point and scene manager.

Usage:
    python main.py              # fullscreen, real DHT22
    python main.py --windowed   # window, for development
    python main.py --fake-sensor

Keys: Esc = back to home, Ctrl+Shift+Q = quit (for grown-ups).
With --debug: 1-4 drain food/clean/fun/energy, 0 refills all, S toggles sleep,
T starts a 5-second test timer.
"""
import argparse
import signal
import sys

import pygame

import config
from core.llm import ChatClient
from core.pet import STATS, Pet
from core.reminders import Reminders
from core.save import SaveStore
from core.sensor import SensorService
from scenes.base import PlaceholderScene
from scenes.chat import ChatScene
from scenes.clean import CleanScene
from scenes.feed import FeedScene
from scenes.games.menu import GamesMenuScene
from scenes.helper import HelperScene
from scenes.home import HomeScene
from scenes.sleep import SleepScene
from ui import theme
from ui.alert import AlertOverlay

SCENES = {"Feed": FeedScene, "Clean": CleanScene, "Sleep": SleepScene, "Chat": ChatScene, "Games": GamesMenuScene,
          "Helper": HelperScene}
NEEDS_AWAKE = {"Feed", "Clean", "Games", "Chat"}

MOUSE_EVENTS = (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP)


class App:
    def __init__(self, windowed=False, fake_sensor=False, debug=False):
        pygame.init()
        pygame.display.set_caption(f"{config.PET_NAME} the Panther")
        flags = 0 if windowed else pygame.FULLSCREEN
        self.screen = pygame.display.set_mode(config.SCREEN_SIZE, flags)
        self.canvas = pygame.Surface(config.LOGICAL_SIZE)
        self.viewport = pygame.Rect((0, 0), config.SCREEN_SIZE)
        self.clock = pygame.time.Clock()
        self.running = True
        self.debug = debug

        self.store = SaveStore()
        self.settings = self.store.load_settings()
        self.points = self.store.get("points", 0)
        saved_pet = self.store.get("pet")
        self.pet = Pet.from_dict(saved_pet) if saved_pet else Pet()

        self.sensor = SensorService(fake=fake_sensor)
        self.sensor.start()

        self.chat_client = ChatClient()
        self.chat_client.warm_up()

        self.reminders = Reminders(self.store, self.settings)
        self.alert = AlertOverlay(self._alert_dismissed)
        self._reminder_timer = 0.0

        self.home = HomeScene(self)
        self.scene = self.home
        self._autosave_timer = 0.0

    # --- navigation ---
    def go_home(self):
        self.switch(self.home)

    def open_scene(self, name):
        if name in NEEDS_AWAKE and self.pet.asleep:
            self.pet.say("Zzz... (Wake Sunny up first!)", 3)
            return
        scene_class = SCENES.get(name)
        self.switch(scene_class(self) if scene_class else PlaceholderScene(self, name))

    def switch(self, scene):
        self.scene.on_exit()
        self.scene = scene
        scene.on_enter()

    # --- state ---
    def add_points(self, amount):
        self.points = max(0, self.points + amount)
        self.store.set("points", self.points)

    def save(self):
        self.store.set("points", self.points)
        self.store.set("pet", self.pet.to_dict())
        self.store.save_settings(self.settings)

    # --- timers, alarms, bedtime ---
    def check_reminders(self, now=None):
        for alert in self.reminders.check(now):
            if alert.kind == "bedtime" and not self.pet.asleep:
                self.pet.go_to_sleep()
            elif alert.kind == "wake" and self.pet.asleep:
                self.pet.wake_up()
            if not alert.silent:
                self.alert.push(alert)

    def _alert_dismissed(self, alert):
        if alert.kind == "bedtime":
            self.go_home()

    # --- main loop ---
    def _to_logical(self, event):
        """Map mouse coordinates from the real screen to the pixel canvas."""
        if event.type in MOUSE_EVENTS:
            lw, lh = config.LOGICAL_SIZE
            vp = self.viewport
            x = (event.pos[0] - vp.x) * lw // vp.w
            y = (event.pos[1] - vp.y) * lh // vp.h
            data = dict(event.dict, pos=(min(max(x, 0), lw - 1), min(max(y, 0), lh - 1)))
            return pygame.event.Event(event.type, data)
        return event

    def _present(self):
        """Scale the canvas onto whatever size the display surface really is.

        The window manager can hand us (or later resize us to) a surface that
        isn't exactly SCREEN_SIZE, so fit the canvas with letterboxing instead
        of assuming the size.
        """
        self.screen = pygame.display.get_surface()
        sw, sh = self.screen.get_size()
        lw, lh = config.LOGICAL_SIZE
        factor = min(sw / lw, sh / lh)
        w, h = int(lw * factor), int(lh * factor)
        self.viewport = pygame.Rect((sw - w) // 2, (sh - h) // 2, w, h)
        if (w, h) == (sw, sh):
            pygame.transform.scale(self.canvas, (sw, sh), self.screen)
        else:
            self.screen.fill(theme.BLACK)
            self.screen.blit(pygame.transform.scale(self.canvas, (w, h)), self.viewport)
        pygame.display.flip()

    def _handle_global(self, event):
        if event.type == pygame.QUIT:
            self.running = False
            return True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_q:
            mods = pygame.key.get_mods()
            if mods & pygame.KMOD_CTRL and mods & pygame.KMOD_SHIFT:
                self.running = False
                return True
        if self.debug and event.type == pygame.KEYDOWN and not self.scene.captures_keyboard:
            return self._handle_debug_key(event.key)
        return False

    def _handle_debug_key(self, key):
        drain = {pygame.K_1: "food", pygame.K_2: "clean", pygame.K_3: "fun", pygame.K_4: "energy"}
        if key in drain:
            self.pet.stats[drain[key]] = max(0.0, self.pet.stats[drain[key]] - 30)
        elif key == pygame.K_0:
            self.pet.stats.update({s: 100.0 for s in STATS})
        elif key == pygame.K_s:
            self.pet.wake_up() if self.pet.asleep else self.pet.go_to_sleep()
        elif key == pygame.K_t:
            self.reminders.add_timer("Test", 5)
        else:
            return False
        return True

    def run(self):
        try:
            while self.running:
                dt = self.clock.tick(config.FPS) / 1000.0
                for event in pygame.event.get():
                    event = self._to_logical(event)
                    if not self._handle_global(event):
                        (self.alert if self.alert.active else self.scene).handle_event(event)

                self._reminder_timer -= dt
                if self._reminder_timer <= 0:
                    self._reminder_timer = 1.0
                    self.check_reminders()
                self.pet.update(dt, self.sensor.latest())
                self.scene.update(dt)
                if self.alert.active:
                    self.alert.update(dt)
                self._autosave_timer += dt
                if self._autosave_timer >= config.AUTOSAVE_INTERVAL:
                    self._autosave_timer = 0.0
                    self.save()

                self.canvas.fill(theme.BG)
                self.scene.draw(self.canvas)
                if self.alert.active:
                    self.alert.draw(self.canvas)
                self._present()
        finally:
            self.shutdown()

    def shutdown(self):
        self.save()
        self.sensor.stop()
        self.store.close()
        pygame.quit()


def main():
    parser = argparse.ArgumentParser(description=f"{config.PET_NAME} the Panther")
    parser.add_argument("--windowed", action="store_true", help="run in a window instead of fullscreen")
    parser.add_argument("--fake-sensor", action="store_true", help="simulate the DHT22")
    parser.add_argument("--debug", action="store_true", help="enable stat/sleep test keys")
    args = parser.parse_args()

    app = App(windowed=args.windowed, fake_sensor=args.fake_sensor, debug=args.debug)
    # Let systemd's SIGTERM trigger a clean save + shutdown.
    signal.signal(signal.SIGTERM, lambda *_: setattr(app, "running", False))
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
