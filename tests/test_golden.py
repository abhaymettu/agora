"""Known theorems, used as regression tests.

If a formalisation drifts, a classical result stops reproducing. That is the
only alarm this project has against the failure mode that looks like success:
an axiom that is subtly the wrong axiom, encoded perfectly.

Every expected value here was measured, not assumed. Run with

    python -m unittest discover -s tests -t .
"""

import unittest

from core import Electorate, derive, library

ARROW = ["pareto", "iia", "nondictatorial"]
GS = ["strategyproof", "surjective", "nondictatorial"]


class Arrow(unittest.TestCase):
    """Pareto plus IIA plus nondictatorship is impossible for a ranking rule."""

    def test_base_case_is_impossible(self):
        r = derive(ARROW, 2, 3, mode="swf")
        self.assertEqual(r.status, "unsat")
        self.assertEqual(sorted(r.core), sorted(ARROW))
        self.assertTrue(r.core_minimal)
        self.assertTrue(r.verified)
        self.assertLess(r.elapsed, 30)

    def test_still_impossible_with_three_voters(self):
        r = derive(ARROW, 3, 3, mode="swf")
        self.assertEqual(r.status, "unsat")
        self.assertEqual(sorted(r.core), sorted(ARROW))

    def test_dropping_nondictatorship_gives_a_dictator(self):
        r = derive(["pareto", "iia"], 2, 3, mode="swf")
        self.assertEqual(r.status, "sat")
        self.assertTrue(
            any(m.startswith("dictatorship of voter") for m in r.rule.matches()),
            f"expected a dictatorship, got {r.rule.describe()}",
        )

    def test_every_axiom_in_the_core_is_load_bearing(self):
        r = derive(ARROW, 2, 3, mode="swf")
        self.assertEqual(set(r.witnesses), set(ARROW))
        for dropped, witness in r.witnesses.items():
            for name in ARROW:
                if name != dropped:
                    self.assertTrue(
                        witness.satisfies(library()[name]),
                        f"witness for dropping {dropped} fails {name}",
                    )

    def test_pareto_is_what_makes_it_arrow(self):
        """IIA, surjectivity and nondictatorship alone are satisfiable.

        Wilson's theorem: the inverse dictator survives them. This is why the
        library carries pareto and not only the eight axioms first asked for.
        """
        r = derive(["iia", "surjective", "nondictatorial"], 2, 3, mode="swf")
        self.assertEqual(r.status, "sat")
        self.assertTrue(
            any(m.startswith("inverse dictatorship") for m in r.rule.matches()),
            f"expected an inverse dictatorship, got {r.rule.describe()}",
        )


class GibbardSatterthwaite(unittest.TestCase):
    """Strategyproof plus onto plus nondictatorial is impossible for a voting rule."""

    def test_base_case_is_impossible(self):
        r = derive(GS, 2, 3, mode="scf")
        self.assertEqual(r.status, "unsat")
        self.assertEqual(sorted(r.core), sorted(GS))
        self.assertTrue(r.core_minimal)
        self.assertTrue(r.verified)
        self.assertLess(r.elapsed, 30)

    def test_still_impossible_with_three_voters(self):
        r = derive(GS, 3, 3, mode="scf")
        self.assertEqual(r.status, "unsat")
        self.assertEqual(sorted(r.core), sorted(GS))

    def test_dropping_nondictatorship_gives_a_dictator(self):
        r = derive(["strategyproof", "surjective"], 2, 3, mode="scf")
        self.assertEqual(r.status, "sat")
        self.assertTrue(
            any(m.startswith("dictatorship of voter") for m in r.rule.matches()),
            f"expected a dictatorship, got {r.rule.describe()}",
        )

    def test_the_witness_for_dropping_nondictatorship_is_a_dictator(self):
        r = derive(GS, 2, 3, mode="scf")
        self.assertIn("nondictatorial", r.witnesses)
        self.assertTrue(
            any(
                m.startswith("dictatorship of voter")
                for m in r.witnesses["nondictatorial"].matches()
            )
        )


class SmallerTheorems(unittest.TestCase):
    def test_no_resolute_anonymous_neutral_rule_at_three_voters(self):
        """Three voters can produce a cycle that a candidate relabelling fixes.

        Anonymity and neutrality then demand a tie that a rule electing one
        winner cannot break. Two voters cannot build that profile, so the same
        pair is satisfiable there: the theorem is about the size, not the axioms.
        """
        self.assertEqual(derive(["anonymous", "neutral"], 3, 3, mode="scf").status, "unsat")
        self.assertEqual(derive(["anonymous", "neutral"], 2, 3, mode="scf").status, "sat")

    def test_condorcet_rules_are_manipulable(self):
        r = derive(["condorcet", "strategyproof"], 3, 3, mode="scf")
        self.assertEqual(r.status, "unsat")
        self.assertEqual(sorted(r.core), ["condorcet", "strategyproof"])

    def test_irrelevant_axioms_are_dropped_from_the_core(self):
        r = derive(["condorcet", "strategyproof", "surjective"], 3, 3, mode="scf")
        self.assertEqual(r.status, "unsat")
        self.assertNotIn("surjective", r.core)


class Frame(unittest.TestCase):
    """The base constraints hold, and never turn up as somebody's axiom."""

    def test_every_profile_elects_exactly_one_candidate(self):
        r = derive(["pareto"], 2, 3, mode="scf")
        self.assertEqual(r.status, "sat")
        for p in Electorate(2, 3).profiles:
            self.assertIn(r.rule.winner(p), range(3))

    def test_every_social_ranking_is_a_strict_linear_order(self):
        r = derive(["pareto"], 2, 3, mode="swf")
        self.assertEqual(r.status, "sat")
        for p in Electorate(2, 3).profiles:
            self.assertEqual(sorted(r.rule.ranking(p)), [0, 1, 2])

    def test_frame_constraints_never_appear_in_a_core(self):
        r = derive(ARROW, 2, 3, mode="swf")
        self.assertTrue(set(r.core) <= set(library()))


class Interface(unittest.TestCase):
    def test_the_same_question_gives_the_same_rule(self):
        a = derive(["strategyproof", "surjective"], 2, 3, mode="scf")
        b = derive(["strategyproof", "surjective"], 2, 3, mode="scf")
        self.assertEqual(a.rule.table, b.rule.table)

    def test_a_returned_rule_runs_on_any_profile_of_its_electorate(self):
        r = derive(["anonymous", "neutral"], 2, 3, mode="scf")
        self.assertEqual(r.status, "sat")
        self.assertIn(r.rule.show_outcome("A>B>C | A>B>C"), "ABC")
        with self.assertRaises(ValueError):
            r.rule.winner("A>B>C")  # wrong number of ballots

    def test_an_axiom_used_in_the_wrong_mode_is_refused(self):
        with self.assertRaises(ValueError):
            derive(["iia"], 2, 3, mode="scf")

    def test_an_unknown_axiom_is_refused(self):
        with self.assertRaises(ValueError):
            derive(["fairness"], 2, 3, mode="scf")

    def test_every_axiom_in_the_library_grounds_in_every_mode_it_claims(self):
        for name, ax in library().items():
            for mode in ax.modes:
                r = derive([name], 2, 3, mode=mode)
                self.assertIn(r.status, ("sat", "unsat"), f"{name} in {mode}")

    def test_results_serialise(self):
        d = derive(ARROW, 2, 3, mode="swf").as_dict()
        self.assertEqual(d["status"], "unsat")
        self.assertEqual(sorted(d["core"]), sorted(ARROW))
        import json

        json.dumps(d)


class WithoutTheSolver(unittest.TestCase):
    """The verifier is an independent check, so test it on a rule we wrote."""

    def test_a_dictatorship_has_exactly_the_properties_it_should(self):
        from core.rules import Rule, reference_rules

        elec = Electorate(2, 3)
        table = dict(reference_rules(elec, "scf"))["dictatorship of voter 1"]
        rule = Rule("scf", elec, table)
        lib = library()
        for name in ("strategyproof", "surjective", "pareto", "monotone"):
            self.assertTrue(rule.satisfies(lib[name]), name)
        self.assertFalse(rule.satisfies(lib["nondictatorial"]))
        self.assertFalse(rule.satisfies(lib["anonymous"]))


if __name__ == "__main__":
    unittest.main()
