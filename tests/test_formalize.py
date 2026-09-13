"""The formalisation gates.

The point of these is that the model is not on trial here. Everything below runs
without one, because everything that decides whether a formalisation is accepted
runs without one. The two tests that do need a local backend say so and skip.
"""

import unittest

from core import library
from formalize import formalize, vet
from formalize.grammar import ATOMS, SortError, check, gbnf
from formalize.model import health, reference


class TheLibraryIsTheCorpus(unittest.TestCase):
    """Whatever the checker does, it must not reject the axioms that ship."""

    def test_every_library_axiom_typechecks_in_every_mode_it_claims(self):
        for name, ax in library().items():
            for mode in ax.modes:
                with self.subTest(axiom=name, mode=mode):
                    check(ax.bodies[mode], mode)

    def test_every_library_axiom_passes_every_gate(self):
        from formalize.model import _flatten

        for name, ax in library().items():
            for mode in ax.modes:
                with self.subTest(axiom=name, mode=mode):
                    p = vet(_flatten(ax, mode), mode, name=name, english=ax.english)
                    self.assertTrue(p.accepted, f"{name}/{mode} rejected at {p.failed}: {p.why}")

    def test_the_reference_shown_to_the_model_names_only_this_modes_atoms(self):
        for mode in ("scf", "swf"):
            text = reference(mode)
            for head, (m, _) in ATOMS.items():
                self.assertEqual(m == mode, f"{head}(" in text, f"{head} in {mode} reference")


class Sorts(unittest.TestCase):
    def reject(self, formula, mode, fragment):
        with self.assertRaises(SortError) as caught:
            from core import parse_formula

            check(parse_formula(formula), mode)
        self.assertIn(fragment, str(caught.exception))

    def test_a_voter_where_a_candidate_belongs(self):
        self.reject("forall p:profile, i:voter, b:cand. unanimous(p,i,b) -> wins(p,b)",
                    "scf", "should be a candidate")

    def test_a_name_that_was_never_introduced(self):
        self.reject("forall p:profile, c:cand. wins(q,c)", "scf", "never introduced")

    def test_an_inner_quantifier_reusing_a_name(self):
        self.reject("forall p:profile. exists p:profile. wins(p,p)", "scf", "already in use")

    def test_one_quantifier_binding_a_name_twice(self):
        self.reject("forall p:profile, p:cand. wins(p,p)", "scf", "introduced twice")

    def test_an_atom_from_the_other_rule_kind(self):
        self.reject("forall p:profile, a:cand. prefers(p,a,a)", "scf", "only exists for")

    def test_applying_something_that_is_not_a_permutation(self):
        self.reject("forall p:profile, a:cand, b:cand. wins(p, a(b))", "scf",
                    "only a relabelling")

    def test_a_term_used_as_a_statement(self):
        self.reject("forall p:profile, i:voter. top(p,i)", "scf", "does not state anything")

    def test_the_wrong_number_of_arguments(self):
        self.reject("forall p:profile, c:cand. wins(p,c,c)", "scf", "takes 2 arguments")


class Grammar(unittest.TestCase):
    def test_each_mode_offers_only_its_own_atoms(self):
        self.assertIn('"wins("', gbnf("scf"))
        self.assertNotIn('"prefers("', gbnf("scf"))
        self.assertIn('"prefers("', gbnf("swf"))
        self.assertNotIn('"wins("', gbnf("swf"))

    def test_rule_names_avoid_the_underscore_llama_cpp_will_not_parse(self):
        for line in gbnf("swf").splitlines():
            head = line.split("::=")[0].strip()
            if head:
                self.assertNotIn("_", head, line)


class Gates(unittest.TestCase):
    def test_a_self_contradictory_axiom_is_refused(self):
        p = vet("forall p:profile, c:cand. wins(p,c) and not wins(p,c)", "scf")
        self.assertEqual(p.failed, "satisfiable")
        self.assertIn("self-contradictory", p.why)

    def test_an_axiom_that_rules_nothing_out_is_refused(self):
        p = vet("forall p:profile, a:cand, b:cand. neq(a,b) -> neq(a,b)", "scf")
        self.assertEqual(p.failed, "non-vacuous")

    def test_an_accepted_axiom_reports_which_named_rules_it_rejects(self):
        p = vet("forall p:profile, c:cand. condorcet(p,c) -> wins(p,c)", "scf")
        self.assertTrue(p.accepted, p.why)
        failing = [b["rule"] for b in p.behaviour if not b["holds"]]
        self.assertIn("the constant rule that always elects A", failing)
        self.assertIn("plurality with alphabetical tie-breaking",
                      [b["rule"] for b in p.behaviour if b["holds"]])

    def test_a_rejected_axiom_never_comes_back_with_an_axiom_attached(self):
        for bad in ("forall p:profile. wins(p,q)",
                    "forall p:profile, c:cand. wins(p,c) and not wins(p,c)"):
            self.assertIsNone(vet(bad, "scf").axiom)

    def test_the_gate_report_stops_at_the_gate_that_failed(self):
        p = vet("forall p:profile. wins(p,q)", "scf")
        self.assertEqual([g["step"] for g in p.gates], ["parse", "sorts"])
        self.assertFalse(p.gates[-1]["passed"])


class WithALocalModel(unittest.TestCase):
    """Skipped unless llama-server or ollama is up. Nothing else here needs one."""

    @classmethod
    def setUpClass(cls):
        if health().get("backend") is None:
            raise unittest.SkipTest("no local model backend is running")

    def test_a_property_the_library_already_has_comes_back_accepted(self):
        p = formalize("the outcome should not depend on who cast which ballot", "scf")
        self.assertTrue(p.accepted, f"failed at {p.failed}: {p.why}")
        self.assertTrue(p.formula)

    def test_a_rejected_draft_is_kept_and_explained(self):
        p = formalize("aaaaa bbbbb ccccc", "scf")
        for attempt in p.attempts:
            self.assertTrue(attempt["why"], "a rejected attempt must carry a reason")
        if not p.accepted:
            self.assertIn(p.failed, ("parse", "sorts", "ground", "satisfiable", "non-vacuous"))


if __name__ == "__main__":
    unittest.main()
