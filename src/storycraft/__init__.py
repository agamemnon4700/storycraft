"""Storycraft: build a short story backwards from its point, so it is funny and lands. See README.md and docs/METHOD.md."""
from .engine import (BEATS, DELIVERY, ENGINES, POINTS, STORY_RE, Storyteller, check, invented_names, sentences)

__all__ = ["BEATS", "DELIVERY", "ENGINES", "POINTS", "STORY_RE", "Storyteller", "check", "invented_names", "sentences"]
__version__ = "0.1.0"
