"""The axioms added for the discovery sweep, pinned against rules we can check by hand.

Same alarm as test_golden.py, one level down: before asking the solver about a
new axiom, fix what that axiom says about rules whose behaviour is already
known. Every entry below was measured, then checked against the textbook fact
named in the comment beside it.

    python -m unittest discover -s tests -t .
"""

import unittest

from core import Electorate, derive, library
from core.rules import Rule, reference_rules

ADDED = ("unanimity", "majority", "condorcetloser", "topsonly", "maskinmonotone", "reversal")

# rule name -> the added axioms it satisfies, at three voters and three candidates.
EXPECTED_3V3C = {
    "dictatorship of voter 1": {"unanimity", "topsonly", "maskinmonotone", "reversal"},
    "dictatorship of voter 2": {"unanimity", "topsonly", "maskinmonotone", "reversal"},
    "dictatorship of voter 3": {"unanimity", "topsonly", "maskinmonotone", "reversal"},
    "the constant rule that always elects A": {"topsonly", "maskinmonotone"},
    "the constant rule that always elects B": {"topsonly", "maskinmonotone"},
    "the constant rule that always elects C": {"topsonly", "maskinmonotone"},
    "plurality with alphabetical tie-breaking": {"unanimity", "majority", "topsonly"},
    "borda with alphabetical tie-breaking": {"unanimity", "condorcetloser"},
    "copeland with alphabetical tie-breaking": {"unanimity", "majority", "condorcetloser"},
}


class AddedAxiomsOnKnownRules(unittest.TestCase):
    def test_matrix_holds(self):
        elec, lib = Electorate(3, 3), library()
        for name, table in reference_rules(elec, "scf"):
            rule = Rule("scf", elec, table)
            got = {a for a in ADDED if rule.satisfies(lib[a])}
            self.assertEqual(got, EXPECTED_3V3C[name], name)

    def test_borda_never_elects_the_condorcet_loser(self):
        """Borda's oldest selling point, and the reason borda and plurality differ here."""
        self.assertIn("condorcetloser", EXPECTED_3V3C["borda with alphabetical tie-breaking"])
        self.assertNotIn("condorcetloser", EXPECTED_3V3C["plurality with alphabetical tie-breaking"])

    def test_borda_fails_the_majority_criterion(self):
        """A candidate can be first on a majority of ballots and still lose on points."""
        self.assertNotIn("majority", EXPECTED_3V3C["borda with alphabetical tie-breaking"])

    def test_dictatorship_is_maskin_monotone(self):
        """The direction that makes Muller-Satterthwaite an impossibility rather than a triviality."""
        for i in (1, 2, 3):
            self.assertIn("maskinmonotone", EXPECTED_3V3C[f"dictatorship of voter {i}"])


class AddedAxiomsAlone(unittest.TestCase):
    """Each one on its own has a rule, so an impossibility later is about the combination."""

    def test_each_is_satisfiable_by_itself(self):
        for name in ADDED:
            with self.subTest(name):
                self.assertEqual(derive([name], 3, 3, mode="scf", timeout=60).status, "sat")


if __name__ == "__main__":
    unittest.main()
