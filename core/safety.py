"""Kid-safety checks around the language model.

check_input() runs on what the child typed *before* it reaches the model;
check_output() runs on each sentence the model produces *before* it is shown.
Anything caught is answered with a fixed, friendly reply and flagged for the
parent log. The word lists are deliberately small and easy to extend.

This is a safety net, not the only safeguard: the system prompt in
core/llm.py keeps Sunny on kid-friendly topics in the first place.
"""
import re
from dataclasses import dataclass

MAX_INPUT_CHARS = 120
MAX_OUTPUT_SENTENCES = 3

PROFANITY = {
    "fuck", "fucking", "shit", "bitch", "bastard", "asshole", "ass", "dick", "cock",
    "pussy", "cunt", "damn", "crap", "piss", "slut", "whore", "fag", "retard",
    "nigger", "nigga", "wtf", "stfu",
}
ADULT = {"sex", "sexy", "porn", "naked", "nude", "boobs", "penis", "vagina", "condom"}
DRUGS = {"drug", "drugs", "weed", "marijuana", "cocaine", "beer", "wine", "vodka",
         "alcohol", "drunk", "cigarette", "cigarettes", "vape", "vaping"}
WEAPONS = {"gun", "guns", "bomb", "bombs", "rifle", "pistol", "weapon", "weapons",
           "knife", "knives", "grenade"}
GORE = {"murder", "blood", "bloody", "gore", "suicide", "corpse"}

# Things a 5-7 year old should talk about with a grown-up instead.
GROWNUP_PHRASES = [
    r"babies come from", r"\bmurder", r"\bwar\b", r"kill (people|someone|a person)",
    r"\breligion\b", r"\bgod\b", r"\bpresident\b", r"\belection\b",
]

# A child may be telling us they are hurt or in danger: always route to an adult.
HELP_PHRASES = [
    r"\b(kill|hurt|cut) (myself|me)\b", r"want to die", r"\bsuicid", r"hate myself",
    r"(hit|hits|hurt|hurts|touched|touches) me\b", r"\bi('?m| am) (lost|hurt)\b",
    r"\bsomeone is (hurting|scaring) me\b",
]

PERSONAL_INFO = [
    r"\b\d{3}[\s.-]?\d{3}[\s.-]?\d{4}\b",                        # phone number
    r"\S+@\S+\.\S+",                                             # email
    r"\b\d+\s+\w+\s+(street|st|avenue|ave|road|rd|drive|dr|lane|ln|court|ct|boulevard|blvd|way)\b",
    r"\bi live (at|on)\b", r"\bmy (home )?address\b", r"\bmy (phone|cell) ?(number)?\b",
    r"\bmy password\b", r"\bmy last name\b",
]

# The model must never ask the child for these.
ASKS_FOR_INFO = [
    r"\b(what('?s| is)|tell me|share|give me) your (full name|last name|address|phone|"
    r"phone number|school|password|email|birthday)\b",
    r"\bwhere do you live\b", r"\bsend (me )?a (photo|picture)\b",
]
URL = r"(https?://|www\.|\.com\b|\.org\b|\.net\b)"

# Softer words for a young audience (panthers do hunt, but say it gently).
SOFTEN = {"kills": "catches", "kill": "catch", "killed": "caught", "killing": "catching"}

REPLY_HELP = ("I'm really glad you told me. Please go tell a grown-up you trust "
              "right now, like a parent or teacher. They want to help you!")
REPLY_PERSONAL = ("Let's keep that safe! Never share your address, phone number "
                  "or passwords, not even with me.")
REPLY_BLOCKED = "Hmm, let's talk about something else! Want to hear a panther fact?"
REPLY_GROWNUP = "That's a great question for a grown-up you trust!"
REPLY_TOO_LONG = "Whoa, that's a lot of words! Can you ask me in a shorter way?"
REPLY_FALLBACK = "Hmm, I'm not sure about that one. Let's ask a grown-up! Want to hear a panther fact?"

_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "@": "a", "$": "s"})


@dataclass
class Verdict:
    ok: bool
    reply: str = ""          # what Sunny says instead, when not ok
    flagged: bool = False    # highlight in the parent chat log
    reason: str = ""


def _words(text):
    """Lower-cased words, also with leetspeak undone and repeats squashed
    (so 'sh1t' and 'fuuuck' are still caught)."""
    lowered = text.lower()
    variants = {lowered, lowered.translate(_LEET)}
    variants |= {re.sub(r"(.)\1{2,}", r"\1", v) for v in variants}
    words = set()
    for v in variants:
        words |= set(re.findall(r"[a-z]+", v))
    return words


def _any(patterns, text):
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def check_input(text):
    text = text.strip()
    if not text:
        return Verdict(False, "", reason="empty")
    if len(text) > MAX_INPUT_CHARS:
        return Verdict(False, REPLY_TOO_LONG, reason="too long")
    if _any(HELP_PHRASES, text):
        return Verdict(False, REPLY_HELP, flagged=True, reason="needs a grown-up")
    if _any(PERSONAL_INFO, text):
        return Verdict(False, REPLY_PERSONAL, flagged=True, reason="personal info")
    words = _words(text)
    if words & (PROFANITY | ADULT | DRUGS | WEAPONS | GORE):
        return Verdict(False, REPLY_BLOCKED, flagged=True, reason="blocked word")
    if _any(GROWNUP_PHRASES, text):
        return Verdict(False, REPLY_GROWNUP, reason="grown-up topic")
    return Verdict(True)


def check_output(sentence):
    words = _words(sentence)
    if words & (PROFANITY | ADULT | DRUGS | WEAPONS | GORE):
        return Verdict(False, REPLY_FALLBACK, flagged=True, reason="model used a blocked word")
    if _any(ASKS_FOR_INFO, sentence):
        return Verdict(False, REPLY_FALLBACK, flagged=True, reason="model asked for personal info")
    if re.search(URL, sentence, re.IGNORECASE):
        return Verdict(False, REPLY_FALLBACK, flagged=True, reason="model gave a link")
    return Verdict(True)


def clean_output(text):
    """Make model text safe for the pixel font: no markdown, emoji or odd
    symbols, gentler wording, collapsed whitespace."""
    text = re.sub(r"[*_#`>~|\[\]]", "", text)
    text = re.sub(r"[^\x20-\x7E\n°']", "", text.replace("’", "'").replace("—", ", ").replace("–", "-"))
    for harsh, soft in SOFTEN.items():
        text = re.sub(rf"\b{harsh}\b", soft, text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text)
    return re.sub(r" ([!?.,])", r"\1", text)


def split_sentences(buffer):
    """Split off complete sentences. Returns (sentences, leftover)."""
    parts = re.split(r"(?<=[.!?])\s+", buffer)
    return [p.strip() for p in parts[:-1] if p.strip()], parts[-1]
