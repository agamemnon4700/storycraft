"""Storycraft engine: tell a short story that is funny and lands a point, by building it backwards from the point.

The method (full write-up in docs/METHOD.md):

  1. POINT   a true thing the story must land ("waiting is easier with company"). Never stated flatly until the end.
  2. FRAME   the false belief the narrator holds at the start ("the tile comes Tuesday"). The comedy is the gap between the frame and the truth.
  3. ENGINE  how the gap widens: denial, escalation, literalism, scale.
  4. BEATS   hook -> specific -> test1 -> test2 -> test3 -> turn -> button. Each test is evidence the frame is false and is funnier than the last.
             The turn is where the narrator half sees the point. The button is the point, said in the narrator's own wrong-footed way, as the last words.
  5. CHECKS  before it is spoken: every beat present, short, nothing explains the joke, nothing cruel, no invented people, a real fact used when facts are given.
  6. DELIVERY  per-beat heat, pause, pace and mood hints for a voice (or for stage directions in text).

The engine has no dependencies (standard library only) and no opinion about which language model, if any, writes the story: pass any function that takes a prompt string and returns text.
Humour is a person's call. The checks keep a story short, clean and honest; they cannot make it funny."""
import json
import random
import re
from collections import deque

BEATS = ["hook", "specific", "test1", "test2", "test3", "turn", "button"]

# Delivery hints per beat: (heat 0..1, pause_before_seconds, pace_factor, mood). Heat builds across the tests, then drops for the turn and the button.
DELIVERY = {
    "hook": (0.10, 0.0, 1.00, None),
    "specific": (0.10, 0.10, 1.00, None),
    "test1": (0.20, 0.15, 1.00, None),
    "test2": (0.45, 0.15, 1.03, "sarcastic"),
    "test3": (0.70, 0.20, 1.06, "sarcastic"),
    "turn": (0.0, 0.55, 0.90, "serious"),
    "button": (0.0, 0.35, 0.92, None),
}

POINTS = ["Waiting is easier with company.", "Almost done is a place, and people live there.", "Good enough is a decision.",
          "Soon is a mood, not a time.", "A home is where you stop counting.", "Small things matter more than they look.",
          "Asking straight is worth the awkward."]
ENGINES = ["denial", "escalation", "literalism", "scale"]
ENGINE_HELP = {"denial": "the narrator keeps believing the frame while the evidence piles up",
               "escalation": "each piece of evidence is bigger or more absurd than the last",
               "literalism": "someone takes a phrase or an instruction exactly literally, with ridiculous results",
               "scale": "a gap in size or importance between the narrator and the thing he is dealing with"}

_CRUEL = re.compile(r"\b(stupid|idiot|ugly|fat|dumb|loser|worthless|shut up|hate you|die|dead|cancer|broke|poor)\b", re.I)
_EXPLAIN = re.compile(r"\b(which is funny|that's the joke|the joke is|get it\??|because it's funny|ha ha|just kidding|lol)\b", re.I)
STORY_RE = re.compile(r"\b(?:tell|give)\s+(?:me\s+)?(?:a|another|one)\s+(?:story|tale|yarn)\b|\bstory\s*time\b|\bgot any stories\b|\bany stories\b", re.I)

_VERBISH = re.compile(r"^(?:says|said|picks|picked|calls|called|comes|came|tells|told|asks|asked|walks|walked|looks|looked|laughs|laughed|stood|sits|sat|shows|showed|gives|gave|thinks|thought|has|had|was|is|does|did|got|gets|goes|went|wants|wanted|knows|knew|takes|took|lives|lived|works|worked|owns|owned)$", re.I)
_COMMON = set("""i a an and as at be but by do for from get go got had has have he her him his how if in is it its just like me my no not of on one or our out she so some than that the their them then there they this to too up us was we well were what when where which who why will with would yes you your
okay oh look listen honest alright right now here here's there's that's it's i'm i've i'd i'll don't doesn't didn't can't won't wasn't weren't isn't aren't couldn't wouldn't shouldn't
update two god monday tuesday wednesday thursday friday saturday sunday
""".split())


def sentences(text):
    return [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]


def invented_names(text, allowed=()):
    """Proper names that are neither in `allowed` nor ordinary words. Capitals in the middle of a sentence count; a sentence-opening word counts only when a verb
    or a surname follows it ("Bartholomew picks", "Bartholomew Quigley"). Heuristic: it catches the usual inventions, not every one."""
    ok = {w.lower() for w in allowed} | _COMMON
    found = set()
    for s in sentences(text):
        toks = re.findall(r"[A-Za-z]+(?:'[a-z]+)?", s)
        for i, t in enumerate(toks):
            w = re.sub(r"'s$", "", t)
            if not w[:1].isupper() or w.lower() in ok or w.lower().endswith("ing"):
                continue
            nxt = toks[i + 1] if i + 1 < len(toks) else ""
            if i > 0 or nxt[:1].isupper() or _VERBISH.match(nxt):
                found.add(w)
    return found


def check(beats, facts=(), cast=()):
    """(ok, problems). `cast` is the fixed set of names the story may use besides what `facts` mention."""
    if not isinstance(beats, dict) or any(not str(beats.get(b, "")).strip() for b in BEATS):
        return False, ["a beat is missing"]
    bad = []
    text = " ".join(str(beats[b]).strip() for b in BEATS)
    n_s, n_w = len(sentences(text)), len(text.split())
    if n_s > 14 or n_w > 210:
        bad.append("too long (%d sentences, %d words)" % (n_s, n_w))
    if any(len(str(beats[b]).split()) > 40 for b in BEATS):
        bad.append("a beat runs long")
    if _CRUEL.search(text):
        bad.append("unkind word")
    if _EXPLAIN.search(text):
        bad.append("explains the joke")
    if str(beats["button"]).strip()[-1:] not in ".!":
        bad.append("button must be a finished sentence")
    allowed = set(cast) | {w for f in facts for w in re.findall(r"[A-Za-z']+", f)}
    inv = invented_names(text, allowed)
    if inv:
        bad.append("invented names: " + ", ".join(sorted(inv)))
    if facts and not any(re.search(r"\b" + re.escape(w) + r"\b", text, re.I) for f in facts for w in re.findall(r"[A-Za-z]{4,}", f)):
        bad.append("uses none of the real facts")
    return (not bad), bad


class Storyteller:
    """persona   one line describing the narrator, put in the model prompt ("a small household robot with a big New York voice").
    cast      names the story may use besides the facts (set of strings).
    episodes  optional authored serial: a list of dicts with the BEATS keys plus "title" and "point". Told in order, round and round.
    points    the points a model-written story may be built around.
    triggers  optional compiled regex: extra phrases that call for the next episode (e.g. "what's the latest on the tile").
    generate  function(prompt) -> text for a language model, or None. Without it, only authored episodes can be told."""

    def __init__(self, generate=None, persona="a dry, warm narrator", cast=(), episodes=(), points=None, triggers=None, rng=None, intro="Okay, a story. "):
        self.generate, self.persona, self.cast = generate, persona, set(cast)
        self.episodes, self.points = list(episodes), list(points or POINTS)
        self.triggers, self.rng, self.intro = triggers, rng or random.Random(), intro
        self.told = deque(maxlen=max(1, len(self.episodes)))
        self.next_ep = 0

    def episode(self):
        """The next authored episode in order; when they run out they go round again."""
        if not self.episodes:
            return None
        ep = self.episodes[self.next_ep % len(self.episodes)]
        self.next_ep += 1
        self.told.append(ep.get("title", ""))
        return ep

    def prompt(self, point, frame, engine, facts, topic=""):
        facts_txt = "\n".join("- " + f for f in facts) or "- (none)"
        cast_txt = ", ".join(sorted(self.cast)) or "nobody besides the narrator"
        return (f"Write a short spoken story told by {self.persona}. Seven beats, exactly, as JSON with these keys: " + ", ".join(BEATS) + ".\n"
                f"POINT (never stated until the button, then said in the narrator's own wrong-footed way, as the last words): {point}\n"
                f"FRAME (the false belief the narrator holds at the start): {frame}\n"
                f"ENGINE ({engine}: {ENGINE_HELP.get(engine, '')})\n"
                f"TOPIC: {topic or 'whatever fits the facts'}\n"
                "Rules: hook = one sentence. specific = one concrete detail. test1, test2, test3 = three pieces of evidence the frame is false, each funnier than the last. "
                "turn = he half sees the point. button = the point, short, last. One to two sentences per beat. Plain words, contractions, no explaining the joke, "
                "never cruel, never at anyone's expense but the narrator's own. "
                f"Use only these facts and these people: {cast_txt}. Invent no other person or place.\n"
                f"FACTS:\n{facts_txt}\nReturn only the JSON object.")

    def make(self, topic="", facts=(), point=None, frame=None):
        """A checked story {beats, point, title}, or None (no model, or two tries failed the checks)."""
        if not self.generate:
            return None
        point = point or self.rng.choice(self.points)
        frame = frame or "everything is almost done"
        engine = self.rng.choice(ENGINES)
        for _ in range(2):
            try:
                raw = self.generate(self.prompt(point, frame, engine, list(facts), topic))
                m = re.search(r"\{.*\}", raw or "", re.S)
                beats = json.loads(m.group(0)) if m else None
            except Exception:
                continue
            ok, _why = check(beats, facts, self.cast)
            if ok:
                return {"beats": {b: str(beats[b]).strip() for b in BEATS}, "point": point, "title": topic or "story"}
        return None

    @staticmethod
    def text(story):
        return " ".join(story["beats"][b].strip() for b in BEATS)

    @staticmethod
    def delivery(story):
        """[(text, heat, pause_before, pace, mood)] per beat, for a voice or for stage directions."""
        return [(story["beats"][b],) + DELIVERY[b] for b in BEATS]

    def handle(self, request, facts=()):
        """Spoken story for a request, or None when the request is not for one.
        'tell me a story about X' tries a model-written story (if a model is set), then falls back to the next authored episode."""
        raw = (request or "").strip()
        if not raw or len(raw) > 160 or not (STORY_RE.search(raw) or (self.triggers and self.triggers.search(raw))):
            return None
        m = re.search(r"\bstory (?:about|on)\b\s*(.+)$", raw, re.I)
        if m and self.generate:
            made = self.make(m.group(1).strip(), facts)
            if made:
                return self.intro + self.text(made)
        ep = self.episode()
        if not ep:
            return None
        return (self.intro if re.search(r"\bstory\b", raw, re.I) else "") + " ".join(ep[b] for b in BEATS)
