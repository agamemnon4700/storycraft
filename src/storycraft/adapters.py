"""Model adapters: each returns a `generate(prompt) -> text` function you can hand to Storyteller. Standard library only (urllib), so they work anywhere Python does.

    from storycraft import Storyteller
    from storycraft.adapters import openai_compatible, anthropic, ollama, from_env

    gen = openai_compatible("https://api.openai.com/v1", api_key="...", model="...")   # also LM Studio, llama.cpp server, vLLM, Together, Groq, OpenRouter, Azure-style gateways
    gen = anthropic(api_key="...", model="...")                                         # Anthropic Messages API
    gen = ollama(model="...")                                                           # a local Ollama server
    story = Storyteller(generate=gen).make("my dog and the vacuum")

You choose the model name; none is assumed. Keys are used only in the request header and are never logged or stored. Any other model works too: write your own
function that takes a prompt string and returns text, or run `storycraft prompt` and paste the prompt into any chat tool."""
import json
import os
import urllib.request

SYSTEM = "You write short spoken stories. Follow the instructions exactly and return only what they ask for."


def _post(url, headers, body, timeout):
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def openai_compatible(base_url, model, api_key=None, max_tokens=700, timeout=60, system=SYSTEM):
    """Any server that speaks the OpenAI /chat/completions shape."""
    url = base_url.rstrip("/") + "/chat/completions"
    hdr = {"Authorization": "Bearer " + api_key} if api_key else {}

    def generate(prompt):
        r = _post(url, hdr, {"model": model, "max_tokens": max_tokens,
                             "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]}, timeout)
        return r["choices"][0]["message"]["content"]
    return generate


def anthropic(model, api_key, base_url="https://api.anthropic.com", max_tokens=700, timeout=60, system=SYSTEM):
    """The Anthropic Messages API."""
    url = base_url.rstrip("/") + "/v1/messages"
    hdr = {"x-api-key": api_key, "anthropic-version": "2023-06-01"}

    def generate(prompt):
        r = _post(url, hdr, {"model": model, "max_tokens": max_tokens, "system": system, "messages": [{"role": "user", "content": prompt}]}, timeout)
        return "".join(b.get("text", "") for b in r.get("content", []) if b.get("type", "text") == "text")
    return generate


def ollama(model, host="http://localhost:11434", timeout=120, system=SYSTEM):
    """A local Ollama server (no key)."""
    url = host.rstrip("/") + "/api/chat"

    def generate(prompt):
        r = _post(url, {}, {"model": model, "stream": False,
                            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]}, timeout)
        return r["message"]["content"]
    return generate


def from_env(environ=None):
    """Pick an adapter from environment variables, or return None if none is configured.

    STORYCRAFT_PROVIDER = openai | anthropic | ollama     STORYCRAFT_MODEL = the model name
    STORYCRAFT_API_KEY  = the key (not needed for ollama or most local servers)
    STORYCRAFT_BASE_URL = the server (openai: default https://api.openai.com/v1; ollama: default http://localhost:11434)"""
    e = os.environ if environ is None else environ
    kind, model = (e.get("STORYCRAFT_PROVIDER") or "").lower(), e.get("STORYCRAFT_MODEL")
    if not kind or not model:
        return None
    key, base = e.get("STORYCRAFT_API_KEY"), e.get("STORYCRAFT_BASE_URL")
    if kind == "openai":
        return openai_compatible(base or "https://api.openai.com/v1", model, key)
    if kind == "anthropic":
        return anthropic(model, key or "", base or "https://api.anthropic.com") if key else None
    if kind == "ollama":
        return ollama(model, base or "http://localhost:11434")
    return None
