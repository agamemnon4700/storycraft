import json
import random
import unittest

from storycraft import BEATS, DELIVERY, POINTS, Storyteller, check, invented_names
from storycraft.examples import fifth_street

E = fifth_street.EPISODES
BASE = {b: E[0][b] for b in BEATS}


class Checks(unittest.TestCase):
    def test_every_authored_episode_passes_its_own_checks(self):
        for e in E:
            ok, why = check({b: e[b] for b in BEATS}, cast=fifth_street.CAST)
            self.assertTrue(ok, (e["title"], why))

    def test_catches_cruelty(self):
        self.assertFalse(check(dict(BASE, test2="You're a stupid idiot about the floor."), cast=fifth_street.CAST)[0])

    def test_catches_explaining_the_joke(self):
        self.assertFalse(check(dict(BASE, test1=BASE["test1"] + " Which is funny, get it?"), cast=fifth_street.CAST)[0])

    def test_catches_invented_people(self):
        ok, why = check(dict(BASE, specific="The contractor, Bartholomew Quigley, picks up on the ninth ring."), cast=fifth_street.CAST)
        self.assertFalse(ok)
        self.assertTrue(any("invented" in w for w in why))

    def test_sentence_opening_name_with_a_verb_is_caught_but_ordinary_openers_are_not(self):
        self.assertIn("Bartholomew", invented_names("Bartholomew picks up the phone."))
        self.assertEqual(invented_names("Almost done is a place. Waiting is hard. Honest to God, it is."), set())

    def test_missing_beat_and_ramble(self):
        self.assertFalse(check({k: v for k, v in BASE.items() if k != "turn"})[0])
        self.assertFalse(check(dict(BASE, test3=" ".join(["and then another thing happened, which was long"] * 20)), cast=fifth_street.CAST)[0])

    def test_requires_a_real_fact_when_given(self):
        facts = ["The dog is named Luna."]
        self.assertFalse(check(BASE, facts, fifth_street.CAST)[0])
        self.assertTrue(check(dict(BASE, hook="So I called about Luna and the Fifth Street place."), facts, fifth_street.CAST)[0])

    def test_the_point_is_not_stated_flatly_before_the_button(self):
        for e in E:
            self.assertNotIn(e["point"].lower().rstrip("."), " ".join(e[b] for b in BEATS[:5]).lower(), e["title"])


class Serial(unittest.TestCase):
    def test_episodes_in_order_and_round_again(self):
        st = fifth_street.build()
        told = [st.handle("tell me a story") for _ in range(len(E) + 1)]
        for i, e in enumerate(E):
            self.assertTrue(told[i].split("Okay, a story. ")[1].startswith(e["hook"]))
            self.assertTrue(told[i].endswith(e["button"]))
        self.assertTrue(told[len(E)].split("Okay, a story. ")[1].startswith(E[0]["hook"]))

    def test_triggers(self):
        st = fifth_street.build()
        for q in ["tell me a story", "got any stories?", "what's the latest on the tile", "any news on the contractor", "how's the Fifth Street place", "story time"]:
            self.assertIsNotNone(st.handle(q), q)
        for q in ["turn on the light", "what time is it", "the story of Rome", "where is my pencil"]:
            self.assertIsNone(st.handle(q), q)

    def test_no_episodes_no_model_means_nothing_to_say(self):
        self.assertIsNone(Storyteller().handle("tell me a story"))


class Model(unittest.TestCase):
    def test_a_good_model_story_is_returned_and_the_prompt_carries_the_method(self):
        seen = []

        def gen(p):
            seen.append(p)
            return "Sure.\n" + json.dumps({b: E[1][b] for b in BEATS})
        st = fifth_street.build(gen, rng=random.Random(3))
        m = st.make("the tile", ["the tile is on a boat"])
        self.assertEqual(set(m["beats"]), set(BEATS))
        self.assertIn(m["point"], POINTS)
        for w in ("POINT", "FRAME", "ENGINE", "Invent no other person", "the tile is on a boat"):
            self.assertIn(w, seen[0])

    def test_garbage_and_cruelty_fall_back(self):
        self.assertIsNone(Storyteller(lambda p: "not json at all").make("x"))
        cruel = json.dumps(dict(BASE, test1="You are a stupid idiot."))
        tries = []
        st = fifth_street.build(lambda p: tries.append(1) or cruel)
        self.assertIsNone(st.make("x"))
        self.assertEqual(len(tries), 2)
        self.assertTrue(st.handle("tell me a story about my dog").split("Okay, a story. ")[1].startswith(E[0]["hook"]))

    def test_model_that_raises_is_survived(self):
        def boom(p):
            raise RuntimeError("down")
        self.assertIsNone(Storyteller(boom).make("x"))


class Delivery(unittest.TestCase):
    def test_heat_builds_then_drops_and_the_turn_gets_the_longest_pause(self):
        d = Storyteller.delivery({"beats": BASE})
        self.assertEqual([x[0] for x in d], [BASE[b] for b in BEATS])
        self.assertTrue(d[2][1] < d[3][1] < d[4][1])
        self.assertEqual((d[5][1], d[6][1]), (0, 0))
        self.assertEqual(d[5][2], max(x[2] for x in d))
        self.assertEqual(set(DELIVERY), set(BEATS))


if __name__ == "__main__":
    unittest.main()
