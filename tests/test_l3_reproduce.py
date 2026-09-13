"""L3: independent re-derivation of the core's golden results.

Separate from `tests/test_golden.py`, which is L1 checking its own work. These
tests trust nothing the core says. Every verdict it returns is re-derived from
`tests/l3_reference.py`, a second implementation that shares no code with
`core/`, and every rule it mints is checked against every axiom on every
profile of its electorate by hand.

Three things get checked, in the order the brief puts them:

1. Reproduction. The known-impossible sets come back unsat with a core that my
   own solver agrees is unsatisfiable and minimal. The known-possible
   relaxations come back sat with a rule of the shape the theory predicts.
2. Property tests. Every minted rule, and every witness rule attached to an
   impossibility, is checked exhaustively. Zero violations accepted.
3. Renderer. For each unsat case, the axioms the English proof names are
   exactly the axioms in the minimal core.

A disagreement here is a BLOCKER against the core, not a failing test to
adjust.

    PYTHONPATH=. .venv/bin/python -m unittest tests.test_l3_reproduce -v
"""

import re
import unittest
from dataclasses import dataclass

from core import axiom_names, derive, library, render

from tests import l3_reference as ref

NAME_OF = {c: i for i, c in enumerate(ref.NAMES)}

LIBRARY_NAMES = frozenset(ref.AXIOMS["swf"]) | frozenset(ref.AXIOMS["scf"])


@dataclass(frozen=True)
class Row:
    """One question, and what the theory says the answer is."""

    axioms: tuple
    mode: str
    voters: int
    candidates: int
    expect: str                      # "sat" | "unsat"
    core: tuple = None               # named in the golden table, where it names one
    shape: str = None                # "dictatorship" | "inverse dictatorship"
    why: str = ""

    @property
    def label(self):
        return f"{self.mode} {self.voters}v{self.candidates}c {', '.join(self.axioms)}"


ARROW = ("pareto", "iia", "nondictatorial")
GS = ("strategyproof", "surjective", "nondictatorial")

# The eleven rows of the golden table in notes/BUILD-CORE.md, in its order.
MATRIX = [
    Row(ARROW, "swf", 2, 3, "unsat", core=ARROW, why="Arrow, base case"),
    Row(ARROW, "swf", 3, 3, "unsat", core=ARROW, why="Arrow, one voter up"),
    Row(("pareto", "iia"), "swf", 2, 3, "sat", shape="dictatorship",
        why="Arrow without nondictatorship is the dictator"),
    Row(("iia", "surjective", "nondictatorial"), "swf", 2, 3, "sat",
        shape="inverse dictatorship",
        why="Wilson: without pareto the inverse dictator survives"),
    Row(GS, "scf", 2, 3, "unsat", core=GS, why="Gibbard-Satterthwaite, base case"),
    Row(GS, "scf", 3, 3, "unsat", core=GS, why="Gibbard-Satterthwaite, one voter up"),
    Row(("strategyproof", "surjective"), "scf", 2, 3, "sat", shape="dictatorship",
        why="GS without nondictatorship is the dictator"),
    Row(("anonymous", "neutral"), "scf", 3, 3, "unsat",
        why="three voters can cycle, and no tie-break is allowed"),
    Row(("anonymous", "neutral"), "scf", 2, 3, "sat",
        why="two voters, so majority decides and relabelling is safe"),
    Row(("condorcet", "strategyproof"), "scf", 3, 3, "unsat",
        core=("condorcet", "strategyproof"), why="Condorcet rules are manipulable"),
    Row(("condorcet", "strategyproof", "surjective"), "scf", 3, 3, "unsat",
        core=("condorcet", "strategyproof"), why="surjectivity is spare here"),
]

# Rows L3 adds. The golden table does not claim these; the theory does, and
# they widen what the property tests cover to every axiom in the library.
EXTRA = [
    Row(("pareto", "monotone", "anonymous", "neutral"), "scf", 2, 3, "unsat",
        why="two voters cannot break the A-against-B tie neutrally; monotone is spare"),
    Row(("condorcet", "monotone"), "scf", 3, 3, "sat",
        why="Condorcet and monotonicity are compatible"),
    Row(("pareto", "monotone", "surjective", "nondictatorial"), "swf", 2, 3, "sat",
        why="everything Arrow asks for except IIA"),
    Row(("pareto", "nondictatorial"), "scf", 3, 3, "sat",
        why="the weakest interesting pair"),
    Row(("iia", "pareto", "surjective"), "swf", 2, 3, "sat", shape="dictatorship",
        why="surjectivity does not save you from the dictator"),
]

ROWS = MATRIX + EXTRA


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def electorate(row):
    return ref.Elec(row.voters, row.candidates)


def table_of(rule, E):
    """The core's rule, read through the public interface into my own table.

    Built by asking the rule about each of *my* profiles, so an electorate that
    does not line up shows as a KeyError rather than quietly agreeing.
    """
    return {p: rule.outcome(p) for p in E.profiles}


def first_block(text):
    """The axiom names in the leading indented block of a rendered proof."""
    names, started = [], False
    for line in text.splitlines():
        m = re.match(r"^  (\S+)(?:\s|$)", line)
        if m and m.group(1) in LIBRARY_NAMES:
            names.append(m.group(1))
            started = True
        elif started and not line.strip():
            break
    return names


def rendered_rows(E, text):
    """The (profile, outcome) rows a rendered existence shows, parsed back.

    Parsed rather than string-matched, so the check is that the table shown is
    the table the rule holds, not that L3 guessed the core's layout.
    """
    out = {}
    for line in text.splitlines():
        m = re.match(r"^  (v1:.*?)  ->  (.+)$", line)
        if not m:
            continue
        ballots = tuple(
            tuple(NAME_OF[c] for c in re.sub(r"v\d+:", "", b).replace(">", " ").split())
            for b in m.group(1).split("|")
        )
        shown = m.group(2).strip()
        if ">" in shown:
            outcome = tuple(NAME_OF[c] for c in shown.replace(">", " ").split())
        else:
            outcome = NAME_OF[shown]
        out[ballots] = outcome
    return out


def without_block(text):
    """The axioms the proof says can be given up, one witness rule each."""
    return re.findall(r"^  without (\S+)", text, re.M)


# --------------------------------------------------------------------------


class Reproduction(unittest.TestCase):
    """Every row of the matrix, answered twice and compared."""

    maxDiff = None

    def check(self, row):
        E = electorate(row)
        mine, my_table = ref.solve(E, row.mode, list(row.axioms))
        theirs = derive(list(row.axioms), row.voters, row.candidates, mode=row.mode)

        self.assertEqual(mine, row.expect, f"my own solver disagrees with the theory on {row.label}")
        self.assertEqual(
            theirs.status, row.expect,
            f"BLOCKER {row.label}: core says {theirs.status}, theory and my solver say {row.expect}",
        )
        if row.expect == "unsat":
            self.assertIsNotNone(theirs.core, "an impossibility with no core")
            self.assertTrue(theirs.core_minimal, f"BLOCKER {row.label}: core not claimed minimal")
            self.assertLessEqual(set(theirs.core), set(row.axioms), "core is not a subset of the question")
            if row.core is not None:
                self.assertEqual(
                    sorted(theirs.core), sorted(row.core),
                    f"BLOCKER {row.label}: golden table names {row.core}",
                )
            check = ref.verify_minimal_unsat(E, row.mode, list(theirs.core))
            self.assertEqual(check["problems"], [], f"BLOCKER {row.label}: {check['problems']}")
        else:
            self.assertIsNotNone(theirs.rule, "an existence with no rule")
            own_bad, _ = ref.violations(E, row.mode, my_table, list(row.axioms))
            self.assertEqual(own_bad, [], f"my own rule for {row.label} breaks {own_bad[:3]}")
            bad, _ = ref.violations(E, row.mode, table_of(theirs.rule, E), list(row.axioms))
            self.assertEqual(bad, [], f"BLOCKER {row.label}: minted rule violates {bad[:3]}")
            if row.shape == "dictatorship":
                d = ref.dictators(E, row.mode, table_of(theirs.rule, E))
                self.assertTrue(d, f"BLOCKER {row.label}: expected a dictatorship, got {theirs.rule.describe()}")
            if row.shape == "inverse dictatorship":
                inv = ref.inverse_dictators(E, row.mode, table_of(theirs.rule, E))
                self.assertTrue(
                    inv, f"BLOCKER {row.label}: expected an inverse dictatorship, got {theirs.rule.describe()}"
                )
                self.assertEqual(
                    ref.dictators(E, row.mode, table_of(theirs.rule, E)), [],
                    "an inverse dictator that is also a dictator",
                )
        return theirs

    # the golden eleven, one test each so a failure names itself ------------

    def test_arrow_2v3c(self):
        self.check(MATRIX[0])

    def test_arrow_3v3c(self):
        self.check(MATRIX[1])

    def test_arrow_without_nondictatorship_is_a_dictator(self):
        self.check(MATRIX[2])

    def test_wilson_inverse_dictator(self):
        self.check(MATRIX[3])

    def test_gibbard_satterthwaite_2v3c(self):
        self.check(MATRIX[4])

    def test_gibbard_satterthwaite_3v3c(self):
        self.check(MATRIX[5])

    def test_gs_without_nondictatorship_is_a_dictator(self):
        self.check(MATRIX[6])

    def test_anonymous_and_neutral_fail_at_three_voters(self):
        self.check(MATRIX[7])

    def test_anonymous_and_neutral_hold_at_two_voters(self):
        self.check(MATRIX[8])

    def test_condorcet_rules_are_manipulable(self):
        self.check(MATRIX[9])

    def test_a_spare_axiom_stays_out_of_the_core(self):
        r = self.check(MATRIX[10])
        self.assertNotIn("surjective", r.core)

    def test_a_minimal_core_is_one_of_several(self):
        """The core returns *a* minimal core, and here there are two.

        At two voters, pareto + anonymous + neutral and monotone + anonymous +
        neutral are both unsatisfiable and both minimal. Pinning the expected
        answer to one of them would be testing which way a solver leans.
        """
        E = ref.Elec(2, 3)
        r = derive(["pareto", "monotone", "anonymous", "neutral"], 2, 3, mode="scf")
        self.assertEqual(r.status, "unsat")
        both = [["pareto", "anonymous", "neutral"], ["monotone", "anonymous", "neutral"]]
        for c in both:
            self.assertEqual(
                ref.verify_minimal_unsat(E, "scf", c)["problems"], [],
                f"my own check says {c} is not a minimal impossibility",
            )
        self.assertIn(sorted(r.core), [sorted(c) for c in both])
        self.assertEqual(ref.verify_minimal_unsat(E, "scf", list(r.core))["problems"], [])

    # the rows L3 adds ----------------------------------------------------

    def test_extra_rows(self):
        for row in EXTRA:
            with self.subTest(row.label):
                self.check(row)


class MintedRules(unittest.TestCase):
    """Property tests: every rule the core hands over, on every profile.

    A rule is a finite table, the electorates here are tiny, and the axioms are
    decidable by inspection. There is no reason to sample.
    """

    def test_every_minted_rule_satisfies_every_axiom_asked_for(self):
        total_rules = 0
        for row in ROWS:
            if row.expect != "sat":
                continue
            with self.subTest(row.label):
                E = electorate(row)
                r = derive(list(row.axioms), row.voters, row.candidates, mode=row.mode)
                self.assertEqual(r.status, "sat")
                bad, _ = ref.violations(E, row.mode, table_of(r.rule, E), list(row.axioms))
                self.assertEqual(bad, [], f"BLOCKER {row.label}: {bad[:3]}")
                total_rules += 1
        self.assertGreaterEqual(total_rules, 6)

    def test_every_witness_rule_satisfies_what_it_claims(self):
        """An impossibility ships a rule per dropped axiom. Check all of them."""
        for row in ROWS:
            if row.expect != "unsat":
                continue
            E = electorate(row)
            r = derive(list(row.axioms), row.voters, row.candidates, mode=row.mode)
            self.assertEqual(sorted(r.witnesses), sorted(r.core), "a core member with no witness")
            for dropped, rule in r.witnesses.items():
                rest = [a for a in r.core if a != dropped]
                with self.subTest(f"{row.label} without {dropped}"):
                    bad, _ = ref.violations(E, row.mode, table_of(rule, E), rest)
                    self.assertEqual(bad, [], f"BLOCKER {row.label}: witness breaks {bad[:3]}")
                    # and it must actually fail the axiom it was allowed to drop
                    broke, _ = ref.violations(E, row.mode, table_of(rule, E), [dropped])
                    self.assertTrue(
                        broke,
                        f"BLOCKER {row.label}: the witness for dropping {dropped} satisfies it too, "
                        f"so {dropped} was never load-bearing",
                    )

    def test_a_rule_is_a_function_of_the_profile_and_nothing_else(self):
        """Determinism, checked by asking twice and by asking in two spellings."""
        E = ref.Elec(2, 3)
        a = derive(["strategyproof", "surjective"], 2, 3, mode="scf").rule
        derive(["pareto", "iia", "nondictatorial"], 2, 3, mode="swf")  # unrelated work
        b = derive(["strategyproof", "surjective"], 2, 3, mode="scf").rule
        self.assertEqual(table_of(a, E), table_of(b, E))
        for p in E.profiles:
            self.assertEqual(a.outcome(p), a.outcome(E.show_profile(p)))


class Renderer(unittest.TestCase):
    """The English proof has to name the same axioms as the minimal core."""

    def test_the_proof_names_exactly_the_core(self):
        for row in ROWS:
            if row.expect != "unsat":
                continue
            with self.subTest(row.label):
                E = electorate(row)
                r = derive(list(row.axioms), row.voters, row.candidates, mode=row.mode)
                check = ref.verify_minimal_unsat(E, row.mode, list(r.core))
                self.assertEqual(check["problems"], [], "my own minimality check failed first")
                text = render(r)
                self.assertEqual(text, str(r), "render() and str() disagree")
                named = first_block(text)
                self.assertEqual(
                    sorted(named), sorted(check["core"]),
                    f"BLOCKER {row.label}: the proof names {named}, the minimal core is {check['core']}",
                )
                self.assertEqual(
                    sorted(without_block(text)), sorted(check["core"]),
                    f"BLOCKER {row.label}: the escape list does not match the core",
                )
                spare = set(row.axioms) - set(check["core"])
                for name in spare:
                    self.assertNotIn(
                        name, named, f"BLOCKER {row.label}: {name} is spare but listed as load-bearing"
                    )

    def test_the_proof_states_the_electorate_it_is_about(self):
        for voters, cands in [(2, 3), (3, 3)]:
            # rendered prose is hard-wrapped, so compare with one space
            text = re.sub(r"\s+", " ", render(derive(list(ARROW), voters, cands, mode="swf")))
            self.assertIn(f"{voters} voters and {cands} candidates", text)
            self.assertIn("base-case lemma", text)
            self.assertIn(f"all {len(ref.Elec(voters, cands).profiles)} profiles", text)

    def test_a_rendered_rule_is_the_rule_it_minted(self):
        """Whatever rows the proof prints have to agree with the rule object."""
        for axioms, mode in [
            (["strategyproof", "surjective"], "scf"),
            (["pareto", "iia"], "swf"),
        ]:
            with self.subTest(f"{mode} {axioms}"):
                r = derive(axioms, 2, 3, mode=mode)
                E = ref.Elec(2, 3)
                shown = rendered_rows(E, render(r))
                self.assertGreaterEqual(len(shown), 4, "an existence that shows no rows")
                table = table_of(r.rule, E)
                for p, outcome in shown.items():
                    self.assertEqual(table[p], outcome, f"printed row contradicts the rule at {p}")


class AgainstTheLibrary(unittest.TestCase):
    """My re-derivation has to cover the library, not a convenient corner of it."""

    def test_i_reimplemented_every_axiom(self):
        for mode in ("scf", "swf"):
            self.assertEqual(
                sorted(ref.AXIOMS[mode]), sorted(axiom_names(mode=mode)),
                f"L3 and the core disagree about which axioms exist in {mode}",
            )

    def test_the_library_and_my_reading_of_it_agree_on_hand_built_rules(self):
        """The one place the two implementations meet: a rule neither invented.

        If my reading of an axiom were wrong, `Rule.satisfies` and my own
        checker would disagree about a rule built by hand from the definition.
        """
        E = ref.Elec(2, 3)
        lib = library()
        for mode, built in [
            ("swf", {p: p[0] for p in E.profiles}),                      # dictator
            ("swf", {p: tuple(reversed(p[0])) for p in E.profiles}),     # inverse dictator
            ("scf", {p: p[0][0] for p in E.profiles}),                   # dictator
            ("scf", {p: 0 for p in E.profiles}),                         # constant A
        ]:
            core_rule = self._as_core_rule(mode, built)
            for name, ax in lib.items():
                if mode not in ax.modes:
                    continue
                mine = not ref.violations(E, mode, built, [name])[0]
                with self.subTest(f"{mode} {name}"):
                    self.assertEqual(
                        core_rule.satisfies(ax), mine,
                        f"BLOCKER: the core and L3 read {name} ({mode}) differently",
                    )

    def _as_core_rule(self, mode, built):
        """A rule object holding a table I chose, reached through the public API.

        Built by finding a question whose answer is that rule would be circular,
        so the table is installed directly on a rule the core made. Only the
        table is replaced; everything else is the core's own machinery.
        """
        from core import Rule

        seed = derive(["pareto"], 2, 3, mode=mode).rule
        return Rule(mode, seed.elec, dict(built))


if __name__ == "__main__":
    unittest.main(verbosity=2)
