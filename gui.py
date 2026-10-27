
import tkinter as tk
from tkinter import font
from datetime import datetime

import board
import adafruit_dht

# Sensor connected to GPIO4
sensor = adafruit_dht.DHT22(board.D4, use_pulseio=False)

BG = "#101827"
CARD = "#1C293B"
WHITE = "#F1F5F9"
MUTED = "#94A3B8"
ORANGE = "#F59E0B"
BLUE = "#38BDF8"
GREEN = "#34D399"

root = tk.Tk()
root.title("Climate Monitor")
root.configure(bg=BG)
root.geometry("800x480")
root.attributes("-fullscreen", True)

def make_label(parent, text, size, color, bold=False):
    f = font.Font(
        family="DejaVu Sans",
        size=size,
        weight="bold" if bold else "normal"
    )
    return tk.Label(
        parent, text=text, font=f,
        fg=color, bg=parent["bg"]
    )

# Header
make_label(root, "CLIMATE MONITOR", 24, WHITE, True).pack(pady=(25, 4))
make_label(root, "LIVE ENVIRONMENTAL READINGS", 10, MUTED).pack()

# Reading cards
cards = tk.Frame(root, bg=BG)
cards.pack(fill="both", expand=True, padx=35, pady=25)
cards.columnconfigure((0, 1), weight=1)
cards.rowconfigure(0, weight=1)

temp_card = tk.Frame(cards, bg=CARD)
temp_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

hum_card = tk.Frame(cards, bg=CARD)
hum_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

make_label(temp_card, "TEMPERATURE", 13, MUTED, True).pack(pady=(35, 12))
temp_value = make_label(temp_card, "--.-", 48, ORANGE, True)
temp_value.pack()
make_label(temp_card, "°C", 18, ORANGE).pack()

make_label(hum_card, "HUMIDITY", 13, MUTED, True).pack(pady=(35, 12))
hum_value = make_label(hum_card, "--.-", 48, BLUE, True)
hum_value.pack()
make_label(hum_card, "% RH", 18, BLUE).pack()

status = make_label(root, "Connecting to sensor...", 11, GREEN)
status.pack(pady=(0, 5))

clock = make_label(root, "", 10, MUTED)
clock.pack(pady=(0, 15))


def update_display():
    clock.config(
        text="Last check: " + datetime.now().strftime("%H:%M:%S")
    )

    try:
        temperature = sensor.temperature
        humidity = sensor.humidity

        if temperature is not None and humidity is not None:
            temp_value.config(text=f"{temperature:.1f}")
            hum_value.config(text=f"{humidity:.1f}")
            status.config(text="● SENSOR CONNECTED", fg=GREEN)

    except RuntimeError:
        # DHT22 readings can occasionally fail.
        status.config(text="Waiting for sensor reading...", fg=ORANGE)

    root.after(2500, update_display)


def close_app(event=None):
    try:
        sensor.exit()
    finally:
        root.destroy()


root.bind("<Escape>", close_app)
root.protocol("WM_DELETE_WINDOW", close_app)

update_display()
root.mainloop()
