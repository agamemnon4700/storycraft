# storycraft

**Build a short story backwards from its point, so it's funny and it lands.**

Most generated humor is a pile of jokes. Comedians who tell stories do something different: they know what true thing the story is *for*, give the narrator a wrong idea about it, and let the evidence pile up until he half sees it. The laugh is recognition. storycraft is that method as a small library: a seven-beat structure, a prompt that makes a language model follow it, checks that keep the result short, clean and honest, and delivery hints for a voice. It also tells authored stories with **no model at all**.

- **No dependencies.** Standard library only. Python 3.8+ on Windows, macOS and Linux.
- **Any model, or none.** You pass a function `generate(prompt) -> text`. Adapters for OpenAI-compatible servers (OpenAI, LM Studio, llama.cpp, vLLM, Groq, OpenRouter...), Anthropic and Ollama are included; or paste the prompt into any chat tool.
- **Any language.** The story format is plain JSON with a schema, and the method is plain text. See [docs/PORTING.md](docs/PORTING.md).
- **MIT licensed.** Use it, change it, publish it, sell it.

## Try it (no model needed)

```
pip install .
storycraft demo
```

```
Okay, a story. Update on the tile. It's coming from Italy, which the contractor says like it's a place you can drive to.
Tuesday, the tile is in customs. Thursday, the tile is on a boat. A different boat. Friday, the boat has a name now, it's a very
nice name, and I don't like where this is going. Then you made yourself a cup of tea and sat down next to me, and I forgot
about the tile for an hour. Waiting's not so bad with company. Don't tell the tile.
```

## The seven beats

| beat | job |
|---|---|
| `hook` | One sentence. What kind of story is this. |
| `specific` | One concrete detail. Specifics make it believable. |
| `test1` `test2` `test3` | Three pieces of evidence that the narrator's belief is false. Each funnier than the last. |
| `turn` | The narrator half sees the point. |
| `button` | The point, short, in the narrator's own wrong-footed words, last. |

The point is never lectured. See [docs/METHOD.md](docs/METHOD.md) for the whole method (point, frame, engine, beats, checks, delivery).

## Use it in code

```python
from storycraft import Storyteller, check
from storycraft.adapters import openai_compatible      # or anthropic, ollama, from_env

gen = openai_compatible("http://localhost:1234/v1", model="your-model")   # any OpenAI-shaped server; api_key optional for local ones
teller = Storyteller(generate=gen, persona="a grumpy lighthouse keeper", cast={"Mabel"})

story = teller.make("the seagull that stole my hat", facts=["The keeper's hat is yellow."])
if story:                                   # None means the model's story failed the checks twice
    print(teller.text(story))               # the spoken story
    for text, heat, pause, pace, mood in teller.delivery(story):   # hints for a voice
        ...
```

Your own authored serial works the same way without a model: pass `episodes=[...]` (see `src/storycraft/examples/fifth_street.py` for a complete example you can copy) and call `teller.handle("tell me a story")`.

### Command line

```
storycraft demo -n 3                       # the example serial
storycraft prompt --point "Be kind." --fact "The dog is Luna."    # a prompt to paste into any chat tool
storycraft check story.json --cast Mabel   # run the checks on a story from anywhere
storycraft write "the vacuum"              # needs STORYCRAFT_PROVIDER / STORYCRAFT_MODEL / STORYCRAFT_API_KEY
storycraft schema                          # JSON schema for a story
```

## The checks (what they do and don't do)

Before a story is spoken: every beat present; short (14 sentences, 210 words at most); nothing cruel; nothing that explains the joke ("get it?"); no invented people or places beyond the cast and the facts you give; a real fact used when you give facts. They keep a story clean and honest. **They can't make it funny**: that's a person's call, and a good reason to read what it writes. The invented-name check is a heuristic and will miss some.

## Honest limits

- Whether a story is funny depends on the model, the facts, and your ear. Start with the authored examples to hear the shape.
- Don't use it to write jokes at someone's expense. The checks catch obvious cruelty, not everything.
- The example serial is a running gag. If a real person asks a serious question, give a plain answer.

## Layout

```
src/storycraft/engine.py      the method: beats, checks, prompt, delivery, Storyteller
src/storycraft/adapters.py    openai-compatible, anthropic, ollama, from_env
src/storycraft/cli.py         the command line
src/storycraft/examples/      a complete authored serial to copy
docs/METHOD.md                the story system
docs/CRAFT-NOTES.md           what the stand-up craft sources say, and where the method comes from
docs/PORTING.md               use it from another language or tool
schema/story.schema.json      the story format
prompts/story-prompt.txt      the prompt as a plain template
tests/                        standard-library tests (no network, no keys)
```

## License

MIT. See [LICENSE](LICENSE).
