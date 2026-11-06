import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from storycraft import adapters
from storycraft.cli import main

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEEN = []


class Stub(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        SEEN.append((self.path, {k.lower(): v for k, v in self.headers.items()}, body))
        if self.path.endswith("/chat/completions"):
            out = {"choices": [{"message": {"content": "openai-shape"}}]}
        elif self.path.endswith("/v1/messages"):
            out = {"content": [{"type": "text", "text": "anthropic-"}, {"type": "text", "text": "shape"}]}
        elif self.path.endswith("/api/chat"):
            out = {"message": {"content": "ollama-shape"}}
        else:
            self.send_response(404)
            self.end_headers()
            return
        data = json.dumps(out).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class Adapters(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), Stub)
        cls.url = "http://127.0.0.1:%d" % cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def test_openai_compatible(self):
        SEEN.clear()
        self.assertEqual(adapters.openai_compatible(self.url + "/v1", "m", "KEY")("hi"), "openai-shape")
        path, hdr, body = SEEN[0]
        self.assertEqual(path, "/v1/chat/completions")
        self.assertEqual(hdr["authorization"], "Bearer KEY")
        self.assertEqual(body["messages"][1]["content"], "hi")

    def test_anthropic(self):
        SEEN.clear()
        self.assertEqual(adapters.anthropic("m", "KEY", self.url)("hi"), "anthropic-shape")
        path, hdr, body = SEEN[0]
        self.assertEqual(path, "/v1/messages")
        self.assertEqual(hdr["x-api-key"], "KEY")
        self.assertEqual(body["messages"][0]["content"], "hi")

    def test_ollama(self):
        self.assertEqual(adapters.ollama("m", self.url)("hi"), "ollama-shape")

    def test_from_env(self):
        self.assertIsNone(adapters.from_env({}))
        self.assertIsNone(adapters.from_env({"STORYCRAFT_PROVIDER": "anthropic", "STORYCRAFT_MODEL": "m"}))   # no key, no adapter
        self.assertEqual(adapters.from_env({"STORYCRAFT_PROVIDER": "ollama", "STORYCRAFT_MODEL": "m", "STORYCRAFT_BASE_URL": self.url})("x"), "ollama-shape")
        self.assertEqual(adapters.from_env({"STORYCRAFT_PROVIDER": "openai", "STORYCRAFT_MODEL": "m", "STORYCRAFT_BASE_URL": self.url + "/v1"})("x"), "openai-shape")

    def test_the_key_is_never_in_the_body(self):
        SEEN.clear()
        adapters.openai_compatible(self.url, "m", "SECRET-KEY")("hi")
        self.assertNotIn("SECRET-KEY", json.dumps(SEEN[0][2]))


class Cli(unittest.TestCase):
    def run_cli(self, *args):
        env = dict(os.environ, PYTHONPATH=os.path.join(ROOT, "src"), PYTHONIOENCODING="utf-8")
        return subprocess.run([sys.executable, "-m", "storycraft", *args], capture_output=True, text=True, env=env, encoding="utf-8")

    def test_demo_runs_without_a_model(self):
        r = self.run_cli("demo")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Fifth Street", r.stdout)

    def test_prompt_and_schema(self):
        r = self.run_cli("prompt", "--point", "Be kind.", "--fact", "The dog is Luna.")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("POINT", r.stdout)
        self.assertIn("The dog is Luna.", r.stdout)
        self.assertEqual(json.loads(self.run_cli("schema").stdout)["required"][0], "hook")

    def test_check_good_and_bad(self):
        from storycraft.examples import fifth_street
        from storycraft import BEATS
        e = fifth_street.EPISODES[0]
        with tempfile.TemporaryDirectory() as d:
            good, bad = os.path.join(d, "g.json"), os.path.join(d, "b.json")
            with open(good, "w", encoding="utf-8") as f:
                json.dump({b: e[b] for b in BEATS}, f)
            with open(bad, "w", encoding="utf-8") as f:
                json.dump({b: e[b] for b in BEATS[:3]}, f)
            self.assertEqual(self.run_cli("check", good, "--cast", ",".join(fifth_street.CAST)).returncode, 0)
            self.assertEqual(self.run_cli("check", bad).returncode, 1)

    def test_write_without_a_model_explains_itself(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("STORYCRAFT_")}
        r = subprocess.run([sys.executable, "-m", "storycraft", "write", "x"], capture_output=True, text=True, encoding="utf-8",
                           env=dict(env, PYTHONPATH=os.path.join(ROOT, "src")))
        self.assertEqual(r.returncode, 2)
        self.assertIn("No model configured", r.stdout)

    def test_main_returns_zero_for_help(self):
        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main([]), 0)


if __name__ == "__main__":
    unittest.main()
