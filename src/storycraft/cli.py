"""Command line: storycraft demo | prompt | check | write | schema.   python -m storycraft ...

  storycraft demo [-n 3]                         tell the example serial (no model needed)
  storycraft prompt --point P --frame F          print the prompt, to paste into any chat tool
  storycraft check story.json [--cast A,B] [--fact F]   run the checks on a story you or a model wrote
  storycraft write "the vacuum"                  write one with a model chosen by STORYCRAFT_* environment variables (see adapters.from_env)
  storycraft schema                              print the JSON schema for a story"""
import argparse
import json
import sys

from . import BEATS, ENGINES, POINTS, Storyteller, check
from .adapters import from_env
from .examples import fifth_street


def _out(text):
    try:
        sys.stdout.write(text + "\n")
    except UnicodeEncodeError:                                  # old Windows consoles
        sys.stdout.write(text.encode("ascii", "replace").decode("ascii") + "\n")


SCHEMA = {"$schema": "http://json-schema.org/draft-07/schema#", "title": "Storycraft story", "type": "object",
          "required": BEATS, "additionalProperties": True,
          "properties": {b: {"type": "string", "minLength": 1, "description": d} for b, d in zip(BEATS, [
              "One sentence that opens the story.", "One concrete, specific detail.", "First piece of evidence the narrator's belief is false.",
              "Second piece, funnier than the first.", "Third piece, the most absurd.", "The narrator half sees the point.",
              "The point, short, said in the narrator's own wrong-footed way, as the last words."])}}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="storycraft", description="Build a short story backwards from its point.")
    sub = ap.add_subparsers(dest="cmd")
    d = sub.add_parser("demo", help="tell the example serial")
    d.add_argument("-n", type=int, default=1)
    p = sub.add_parser("prompt", help="print a story prompt")
    p.add_argument("--point", default=None)
    p.add_argument("--frame", default="everything is almost done")
    p.add_argument("--engine", default="denial", choices=ENGINES)
    p.add_argument("--topic", default="")
    p.add_argument("--fact", action="append", default=[])
    p.add_argument("--cast", default="")
    p.add_argument("--persona", default="a dry, warm narrator")
    c = sub.add_parser("check", help="check a story JSON file")
    c.add_argument("file")
    c.add_argument("--cast", default="")
    c.add_argument("--fact", action="append", default=[])
    w = sub.add_parser("write", help="write a story with a model from the environment")
    w.add_argument("topic", nargs="?", default="")
    w.add_argument("--fact", action="append", default=[])
    w.add_argument("--cast", default="")
    w.add_argument("--persona", default="a dry, warm narrator")
    sub.add_parser("schema", help="print the story JSON schema")
    a = ap.parse_args(argv)

    if a.cmd == "demo":
        st = fifth_street.build()
        for _ in range(max(1, a.n)):
            _out(st.handle("tell me a story"))
            _out("")
        return 0
    if a.cmd == "prompt":
        st = Storyteller(persona=a.persona, cast=[x for x in a.cast.split(",") if x])
        _out(st.prompt(a.point or POINTS[0], a.frame, a.engine, a.fact, a.topic))
        return 0
    if a.cmd == "check":
        with open(a.file, encoding="utf-8") as f:
            story = json.load(f)
        story = story.get("beats", story) if isinstance(story, dict) else story
        ok, why = check(story, a.fact, [x for x in a.cast.split(",") if x])
        _out("OK" if ok else "PROBLEMS: " + "; ".join(why))
        return 0 if ok else 1
    if a.cmd == "write":
        gen = from_env()
        if not gen:
            _out("No model configured. Set STORYCRAFT_PROVIDER (openai|anthropic|ollama) and STORYCRAFT_MODEL (and STORYCRAFT_API_KEY if needed), or use `storycraft prompt` and paste it into any chat tool.")
            return 2
        st = Storyteller(generate=gen, persona=a.persona, cast=[x for x in a.cast.split(",") if x])
        story = st.make(a.topic, a.fact)
        if not story:
            _out("The model's story did not pass the checks twice. Try again, or loosen the cast/facts.")
            return 1
        _out(st.text(story))
        return 0
    if a.cmd == "schema":
        _out(json.dumps(SCHEMA, indent=2))
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
