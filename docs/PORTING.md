# Using storycraft from another language or tool

You don't need Python to use the method. Three levels:

1. **Paste the prompt.** `storycraft prompt --point "..." --frame "..." --fact "..."` prints a complete prompt. Paste it into any chat tool; it returns a JSON object with seven keys. Or copy [`prompts/story-prompt.txt`](../prompts/story-prompt.txt) and fill in the fields.
2. **Use the JSON format.** A story is an object with the seven string keys `hook`, `specific`, `test1`, `test2`, `test3`, `turn`, `button` ([schema](../schema/story.schema.json)). Any language can read and write that. `storycraft check story.json` validates one from anywhere.
3. **Port the checks.** They are small and plain: all seven beats present and non-empty; at most 14 sentences and 210 words, no beat over 40 words; no unkind words; nothing that explains the joke ("which is funny", "get it?", "just kidding", "lol"); the button ends with `.` or `!`; no proper names outside the fixed cast and the facts you supplied; if facts are supplied, at least one word of 4+ letters from a fact appears in the story. The reference implementation is `src/storycraft/engine.py` (about 100 lines of logic).

## Model providers

`storycraft.adapters` covers OpenAI-compatible servers (the shape used by OpenAI, LM Studio, llama.cpp's server, vLLM, Groq, OpenRouter and many others), Anthropic's Messages API and Ollama. For anything else, any function `generate(prompt) -> str` works:

```python
def generate(prompt):
    return my_client.complete(prompt)          # whatever your provider offers
teller = Storyteller(generate=generate)
```

The model must return the JSON object; text around it is ignored. If a story fails the checks, `make()` retries once, then returns `None` so your app can fall back to something authored.

## Voices and screens

`Storyteller.delivery(story)` returns `(text, heat, pause_before_seconds, pace, mood)` per beat. Map them to whatever your output can do: SSML `<break time="...">` and `<prosody rate="...">` for a text-to-speech engine, typing delays and emphasis for a chat UI, or ignore them.

## Notes for embedders

- Nothing is stored, logged or sent anywhere by the library except the prompt you pass to your own `generate` function. Facts you pass go into the prompt, so don't send private details to a hosted model unless that's your intent.
- The checks reduce risk; they don't remove it. If a story reaches a real person, review the output, or at least keep the cast and facts you supply under your control.
