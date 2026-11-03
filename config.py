"""Central configuration for the Sunny the Panther app."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "sunny.db"
SUNNY_ART_DIR = BASE_DIR / "assets" / "sunny"
PROPS_DIR = BASE_DIR / "assets" / "props"

PET_NAME = "Sunny"

# Display: everything is drawn on a small "logical" canvas and scaled up
# with nearest-neighbour so every logical pixel becomes a chunky 2x2 block.
SCREEN_SIZE = (800, 480)
SCALE = 2
LOGICAL_SIZE = (SCREEN_SIZE[0] // SCALE, SCREEN_SIZE[1] // SCALE)
FPS = 30

# DHT22 on GPIO4 (physical pin 7)
DHT_PIN = "D4"
SENSOR_INTERVAL = 3.0        # seconds between reads (DHT22 needs >= 2s)
SENSOR_STALE_AFTER = 30.0    # treat readings older than this as missing

AUTOSAVE_INTERVAL = 30.0

# Local LLM (step 4)
OLLAMA_URL = "http://127.0.0.1:11434"
OLLAMA_MODEL = "llama3.2:3b"

# Defaults for parent-adjustable settings, stored in the save file.
DEFAULT_SETTINGS = {
    "parent_pin": "1234",
    "temp_unit": "F",          # "F" or "C"
    "bedtime": "19:30",
    "wake_time": "07:00",
    "daily_chat_limit": 30,    # messages per day
}
