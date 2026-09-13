"""The web layer.

These run the real handler against a real socket on an ephemeral port. There is
no model in the loop: every endpoint tested here either reads the library or calls
the gates, both of which decide without one.
"""

import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from web.server import Handler


class Endpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.base = "http://127.0.0.1:%d" % cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=30) as r:
            return json.loads(r.read())

    def post(self, path, body):
        req = urllib.request.Request(
            self.base + path, data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read())

    # -- reading ------------------------------------------------------------

    def test_the_catalogue_carries_every_axiom_with_its_modes_and_gloss(self):
        cat = self.get("/api/axioms")
        self.assertEqual(len(cat["axioms"]), 9)
        for a in cat["axioms"]:
            self.assertTrue(a["english"] and a["modes"])
        self.assertTrue(cat["sizes"])

    def test_health_answers_whether_or_not_a_model_is_up(self):
        self.assertIn("backend", self.get("/api/health"))

    # -- deriving -----------------------------------------------------------

    def test_arrow_comes_back_unsat_with_a_minimal_core_and_a_witness_each(self):
        status, r = self.post("/api/derive", {
            "mode": "swf", "voters": 2, "candidates": 3,
            "axioms": ["pareto", "iia", "nondictatorial"]})
        self.assertEqual(status, 200)
        self.assertEqual(r["status"], "unsat")
        self.assertEqual(sorted(r["core"]), ["iia", "nondictatorial", "pareto"])
        self.assertTrue(r["core_minimal"])
        self.assertEqual(sorted(r["witnesses"]), sorted(r["core"]))
        self.assertTrue(r["text"].startswith("No social welfare function"))

    def test_a_satisfiable_ask_returns_a_whole_table_the_page_can_run(self):
        status, r = self.post("/api/derive", {
            "mode": "scf", "voters": 2, "candidates": 3,
            "axioms": ["strategyproof", "surjective"]})
        self.assertEqual(status, 200)
        self.assertEqual(r["status"], "sat")
        self.assertEqual(len(r["rule"]["table"]), 36)
        self.assertTrue(r["rule_named"])
        self.assertIn("dictatorship", r["rule_name"])
        self.assertEqual(r["rule"]["table"]["v1: A > B > C | v2: C > B > A"], "A")

    def test_every_axiom_asked_for_comes_back_with_its_english(self):
        _, r = self.post("/api/derive", {
            "mode": "scf", "voters": 2, "candidates": 3, "axioms": ["condorcet", "monotone"]})
        for name in r["axioms"]:
            self.assertTrue(r["glosses"][name], name)

    # -- the trust boundary -------------------------------------------------

    def test_an_inline_axiom_is_put_through_the_gates_here_not_taken_on_trust(self):
        status, r = self.post("/api/derive", {
            "mode": "scf", "voters": 2, "candidates": 3,
            "axioms": [{"name": "junk", "formula": "forall p:profile, c:cand. wins(p,c) and not wins(p,c)"}]})
        self.assertEqual(status, 400)
        self.assertIn("satisfiable gate", r["error"])

    def test_an_inline_axiom_that_passes_the_gates_is_derived_with(self):
        status, r = self.post("/api/derive", {
            "mode": "scf", "voters": 2, "candidates": 3,
            "axioms": ["surjective", {"name": "cw", "english": "a head to head winner wins",
                                      "formula": "forall p:profile, c:cand. condorcet(p,c) -> wins(p,c)"}]})
        self.assertEqual(status, 200)
        self.assertIn("cw", r["axioms"])
        self.assertEqual(r["glosses"]["cw"], "a head to head winner wins")

    def test_a_size_that_is_not_offered_is_refused_rather_than_attempted(self):
        status, r = self.post("/api/derive", {
            "mode": "scf", "voters": 9, "candidates": 3, "axioms": ["pareto"]})
        self.assertEqual(status, 400)
        self.assertIn("not one of the sizes", r["error"])

    def test_an_empty_ask_is_refused(self):
        self.assertEqual(self.post("/api/derive", {"mode": "scf", "axioms": []})[0], 400)

    def test_an_unknown_rule_kind_is_refused(self):
        self.assertEqual(self.post("/api/derive", {"mode": "xyz", "axioms": ["pareto"]})[0], 400)

    # -- vetting ------------------------------------------------------------

    def test_vet_accepts_a_hand_written_axiom_and_reports_its_behaviour(self):
        status, p = self.post("/api/vet", {
            "mode": "scf", "formula": "forall p:profile, i:voter, c:cand. wins(p,c) -> wins(lift(p,i,c),c)"})
        self.assertEqual(status, 200)
        self.assertTrue(p["accepted"], p["why"])
        self.assertEqual([g["step"] for g in p["gates"]],
                         ["parse", "sorts", "ground", "satisfiable", "non-vacuous"])
        self.assertTrue(p["behaviour"])

    def test_vet_explains_a_refusal_in_english(self):
        _, p = self.post("/api/vet", {"mode": "scf", "formula": "forall p:profile. wins(p,q)"})
        self.assertFalse(p["accepted"])
        self.assertEqual(p["failed"], "sorts")
        self.assertIn("never introduced", p["why"])

    def test_vet_with_nothing_to_check_is_refused(self):
        self.assertEqual(self.post("/api/vet", {"mode": "scf", "formula": "  "})[0], 400)

    def test_a_body_that_is_not_json_is_refused_without_a_traceback(self):
        req = urllib.request.Request(self.base + "/api/derive", data=b"not json",
                                     headers={"Content-Type": "application/json"})
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(req, timeout=10)
        self.assertEqual(caught.exception.code, 400)

    def test_the_page_and_its_assets_are_served(self):
        for path in ("/", "/app.js", "/style.css"):
            with urllib.request.urlopen(self.base + path, timeout=10) as r:
                self.assertEqual(r.status, 200, path)


if __name__ == "__main__":
    unittest.main()
