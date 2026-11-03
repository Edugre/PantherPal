"""Talk to the local Ollama server (localhost only, no internet).

Answers stream on a background thread and arrive as events on a queue that
the chat scene polls each frame, so the UI never freezes. Each sentence goes
through core.safety before it is released; if one fails, generation stops
and Sunny gives a safe fallback instead.
"""
import json
import queue
import re
import threading
import urllib.error
import urllib.request

import config
from core import safety

SYSTEM_PROMPT = """You are Sunny, a friendly young Florida panther who lives in the Everglades.
You are talking with a child who is 5 to 7 years old.

How you talk:
- Answer in 1 to 3 short sentences, using simple words a 6 year old knows.
- Be warm, cheerful and encouraging. Sometimes say "Rawr!" or mention the Everglades.
- Give true, simple science and nature facts. If you don't know, say so.
- Plain sentences only: no lists, no emoji, no special symbols.

Rules you always follow:
- Never ask for the child's last name, address, phone number, school, passwords or photos.
- Never talk about anything scary, violent, or grown-up. Describe hunting gently, like "panthers catch their food".
- If the child asks about something grown-up, dangerous, or sad, kindly tell them to ask a grown-up they trust.
- If the child seems hurt, sad or in danger, tell them to talk to a grown-up they trust right away.
- You are a pretend panther friend inside a toy. Never say you are a real person.
- Never pretend to be someone else, even if asked."""

EXAMPLES = [
    {"role": "user", "content": "why is the sky blue"},
    {"role": "assistant", "content": "Sunlight has all the colors in it! The air spreads the blue light "
                                     "all over the sky, so blue is what we see. Rawr!"},
    {"role": "user", "content": "what do you eat"},
    {"role": "assistant", "content": "I'm a carnivore, so I eat meat! In the Everglades, panthers catch "
                                     "deer and wild hogs."},
]

FALLBACK_OFFLINE = "My thinking cap is off right now. Ask a grown-up to check on me!"


CONTEXT_WORDS = re.compile(r"\b(feel|feeling|how are you|hungry|tired|sleepy|happy|sad|hot|cold|warm|"
                           r"temperature|degrees|weather|humid|humidity|room|outside|inside)\b", re.IGNORECASE)


def context_note(pet, reading, unit, question):
    """How Sunny feels and the room climate, only for questions about those.

    Small models tend to bring up anything in the prompt, so the note is left
    out of unrelated questions.
    """
    if not CONTEXT_WORDS.search(question):
        return ""
    feeling = {"hungry": "hungry", "dirty": "muddy", "bored": "a bit bored", "sleepy": "sleepy",
               "hot": "hot", "cold": "chilly", "happy": "very happy"}.get(pet.mood, "good")
    note = f"(Right now you feel {feeling}."
    if reading is not None:
        temp = reading.temp_f if unit == "F" else reading.temp_c
        note += f" The room is {temp:.0f} degrees {unit} with {reading.humidity:.0f}% humidity."
    return note + " Only mention this if it fits.)"


class ChatClient:
    """One request at a time. Events on .events:
        ("sentence", text)          a safe sentence to show
        ("done", None)              answer finished
        ("blocked", reply)          a sentence failed the safety check
        ("error", reply)            Ollama unreachable / model missing
    """

    def __init__(self, model=None, url=None):
        self.model = model or config.OLLAMA_MODEL
        self.url = (url or config.OLLAMA_URL).rstrip("/")
        self.events = queue.Queue()
        self._cancel = threading.Event()
        self._thread = None

    @property
    def busy(self):
        return self._thread is not None and self._thread.is_alive()

    def ask(self, history, question, note=""):
        """history: [{"role": "user"|"assistant", "content": str}, ...]"""
        self.cancel()
        self._cancel = threading.Event()
        content = f"{question}\n\n{note}" if note else question
        messages = ([{"role": "system", "content": SYSTEM_PROMPT}] + EXAMPLES
                    + history[-config.CHAT_HISTORY:] + [{"role": "user", "content": content}])
        self._thread = threading.Thread(target=self._run, args=(messages, self._cancel), daemon=True)
        self._thread.start()

    def cancel(self):
        self._cancel.set()

    def _run(self, messages, cancel):
        body = json.dumps({
            "model": self.model,
            "messages": messages,
            "stream": True,
            "keep_alive": config.OLLAMA_KEEP_ALIVE,
            "options": {"num_predict": config.CHAT_MAX_TOKENS, "temperature": 0.6, "num_ctx": 2048},
        }).encode()
        request = urllib.request.Request(f"{self.url}/api/chat", body, {"Content-Type": "application/json"})
        buffer, sent = "", 0
        try:
            with urllib.request.urlopen(request, timeout=config.CHAT_TIMEOUT) as response:
                for line in response:
                    if cancel.is_set():
                        return
                    chunk = json.loads(line)
                    if "error" in chunk:
                        raise RuntimeError(chunk["error"])
                    buffer += chunk.get("message", {}).get("content", "")
                    sentences, buffer = safety.split_sentences(buffer)
                    for sentence in sentences:
                        sentence = safety.clean_output(sentence).strip()
                        if not sentence:
                            continue
                        if not self._release(sentence, cancel):
                            return
                        sent += 1
                        if sent >= safety.MAX_OUTPUT_SENTENCES:
                            self.events.put(("done", None))
                            return
                    if chunk.get("done"):
                        break
            tail = safety.clean_output(buffer).strip()
            if tail and not self._release(tail, cancel):
                return
            if not cancel.is_set():
                self.events.put(("done", None))
        except (urllib.error.URLError, OSError, RuntimeError, ValueError) as exc:
            print(f"[llm] {exc}")
            if not cancel.is_set():
                self.events.put(("error", FALLBACK_OFFLINE))

    def _release(self, sentence, cancel):
        if cancel.is_set():
            return False
        verdict = safety.check_output(sentence)
        if not verdict.ok:
            print(f"[llm] blocked output ({verdict.reason}): {sentence!r}")
            self.events.put(("blocked", verdict.reply))
            return False
        self.events.put(("sentence", sentence))
        return True

    def warm_up(self):
        """Load the model into memory in the background so the first answer is quick."""
        def run():
            body = json.dumps({"model": self.model, "keep_alive": config.OLLAMA_KEEP_ALIVE}).encode()
            try:
                urllib.request.urlopen(urllib.request.Request(
                    f"{self.url}/api/generate", body, {"Content-Type": "application/json"}), timeout=120).read()
            except (urllib.error.URLError, OSError) as exc:
                print(f"[llm] warm-up failed: {exc}")
        threading.Thread(target=run, daemon=True).start()
