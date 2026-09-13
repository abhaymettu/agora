# discovery sweep

The core was built against Arrow and Gibbard-Satterthwaite, so reproducing them
tests the encoding and little else. This is what happens when you point the same
machinery at axiom sets nobody aimed it at: more axioms in the library, every
subset of that library asked at every electorate size the encoding survives, and
a literature check on anything that came back looking unusual.

Everything below is reproducible from this repo. Each run writes one JSON record
per question asked, under `notes/discovery/`, carrying the axiom set, the size,
the elapsed seconds, and either an unsat core with a witness rule for every
proper subset of it, or a satisfying rule. Timeouts are written down as timeouts.

## what changed in the library

Seven axioms went in, six stayed. All of them are stated in the literature; the
point of choosing them was that they are rarely the ones a solver gets pointed at.

| axiom | modes | what it says |
|---|---|---|
| `unanimity` | swf, scf | a candidate every voter puts first comes out on top |
| `majority` | swf, scf | a candidate put first by more than half the voters comes out on top |
| `condorcetloser` | swf, scf | a candidate who loses every head to head comes out last |
| `topsonly` | scf | only first choices count; the rest of every ballot is ignored |
| `maskinmonotone` | scf | a winner nobody has demoted against anyone is still the winner |
| `reversal` | scf | turning every ballot upside down never leaves the same candidate winning |

They needed four new ground facts (`condorcetloser`, `majoritytop`, `sametops`,
`improves`) and one new profile term (`rev`), all decided in Python before the
solver sees anything, in the style of the ones already there. Each new axiom has
a second, deliberately different implementation in `tests/l3_reference.py`, and
the two readings are checked against each other on hand-built rules.

`noveto` (Maskin's no veto power: if every voter but one puts c first, c wins)
was written, swept, and then dropped. With two voters "every voter but one" means
"some one voter", so both voters' first choices have to win at once and the axiom
is self-contradictory. That is the size the project's own formalisation gate runs
at, so the library would have been shipping an axiom its own front door rejects.
With three voters it is not merely consistent but identical to `majority`, in both
directions, so it says nothing new until four voters, where the encoding is
already expensive. Its rows are excluded from everything below.

## how the sweep works

Four questions, one script, `notes/discover.py`. `frontier` is the fourth: it
walks one axiom set up through electorate sizes, one record per size, which is
where most of the tables below come from.

`mus` enumerates minimal inconsistent subsets level by level. Every subset of
size 1, then every subset of size 2 that is not a superset of an impossibility
already found, and so on. Because unsatisfiability is upward closed, the pruning
is free: any set that reaches the solver and comes back unsat has had all its
proper subsets resolved, so it is minimal by construction. Sets whose subsets did
not all resolve are flagged, and none occurred.

`count` enumerates every rule satisfying a set, by blocking each model found and
asking again. When the count comes back small and exhaustive, that is a
characterisation and not a witness.

`implies` asks, for each ordered pair of axioms, whether the first plus the
negation of the second is unsatisfiable. This matters more than it sounds. Half
of any raw list of minimal impossibilities is one theorem restated with a stronger
hypothesis, and the implication order is what tells you which half.

## the cells swept

| mode | size | profiles | variables | subsets asked | impossible | unresolved | solver seconds |
|---|---|---|---|---|---|---|---|
| scf | 2v3c | 36 | 108 | 1,203 | 44 | 0 | 56 |
| scf | 3v3c | 216 | 648 | 881 | 37 | 0 | 519 |
| swf | 2v3c | 36 | 216 | 464 | 14 | 0 | 23 |
| swf | 3v3c | 216 | 1,296 | 198 | 9 | 0 | 100 |

Subsets were enumerated to size four everywhere except swf at 3v3c, which stopped
at size three.

Two cells were started and abandoned on budget rather than on a result. The full
size-two sweep at scf 4v3c got through 37 of its 105 questions in 162 solver
seconds, the slowest single question taking 50.9s, and was cut in favour of the
targeted walks below. The full 14-axiom implication matrix at the same size was
cut after roughly half an hour with an empty log, and replaced by a seven-axiom
slice. Both are reported here as not done, not as empty.

## the map

`notes/reduce_map.py` splits each list of minimal impossibilities into the ones
that stand on their own and the ones that are another entry restated with a
stronger hypothesis, using the implication matrix for that size. Axioms that imply
each other in both directions are folded together first, so `strategyproof` and
`maskinmonotone` do not make each other's results look derived.

**scf, three voters, three candidates.** 37 minimal impossibilities, 23 once
equivalent axioms are folded, 9 that stand on their own:

    anonymous + neutral
    condorcetloser + topsonly
    majority + maskinmonotone                  (also as majority + strategyproof)
    anonymous + reversal + topsonly
    majority + reversal + topsonly
    maskinmonotone + nondictatorial + surjective   (also as nondictatorial + strategyproof + surjective)
    monotone + nondictatorial + reversal + topsonly
    neutral + nondictatorial + reversal + topsonly
    nondictatorial + reversal + topsonly + unanimity

The other 14 are each of those with an axiom swapped for a stronger one.
`maskinmonotone` + `nondictatorial` + `surjective` is Gibbard-Satterthwaite and
Muller-Satterthwaite arriving as one entry, because the two axioms turn out to be
equivalent at this size.

**swf, three voters, three candidates.** 9 minimal impossibilities, 5 that stand
on their own:

    anonymous + neutral
    condorcetloser + iia
    iia + majority
    anonymous + iia + surjective
    iia + nondictatorial + unanimity

Arrow itself, `iia` + `nondictatorial` + `pareto`, is one of the four that do not:
it is the last line with `unanimity` strengthened to `pareto`. `condorcet` + `iia`
is `iia` + `majority` strengthened the same way.

**scf, two voters, three candidates.** 44 minimal impossibilities, 11 that stand
on their own, dominated by `topsonly` combinations and by the fact that with two
voters a Condorcet winner is just a unanimous favourite, which collapses four
axioms into near-synonyms.

**swf, two voters, three candidates.** 14 minimal impossibilities. `anonymous` +
`neutral` and the Arrow family, with `nondictatorial` still needed everywhere
because at two voters `condorcet` does not yet rule out a dictator.

## the implication order, by size

The order is not stable across sizes, and reading a list of impossibilities
without it produces phantom results.

Holding at both 2v3c and 3v3c, scf: `pareto` gives `surjective` and `unanimity`;
`unanimity` gives `surjective`; `neutral` gives `surjective`; `anonymous` gives
`nondictatorial`; `condorcet` gives `unanimity` and `majority`; `strategyproof`
and `maskinmonotone` give each other, and both give `monotone`.

Appearing only at two voters: `pareto`, `unanimity` and `majority` each give
`condorcet`, and `pareto` also gives `majority` and `condorcetloser`. With two
voters a Condorcet winner is exactly a candidate both voters put first, which
collapses that end of the order.

Appearing only at three voters: `condorcet` gives `pareto`, `monotone`,
`nondictatorial` and `condorcetloser`; `majority` gives `pareto` and
`nondictatorial`; `condorcetloser` gives `nondictatorial`. The Condorcet loser
one is a three-candidate fact: with an odd number of voters and three candidates,
a Condorcet loser forces a Condorcet winner to exist, so Condorcet consistency
already rules the loser out.

That `strategyproof` and `maskinmonotone` imply each other in both directions, at
both sizes, is the Muller-Satterthwaite equivalence falling out of the sweep
rather than being asserted. See below.

At four voters and three candidates a seven-axiom slice of the matrix took 584s
and returned four edges: `condorcet` gives `majority` and `unanimity`, `majority`
gives `unanimity`, `pareto` gives `unanimity`. The equivalence of `strategyproof`
and `maskinmonotone` came back unresolved in both directions against a 200s budget
per edge. `condorcet` gives neither `pareto` nor `condorcetloser` at four voters,
which is what makes those two three-voter rows artifacts rather than facts.

## what came back that the core was not built for

All of this is known. Two of the four were already targets, and what the sweep
adds to those is a count or a pattern rather than a verdict; the other two the
core had never been pointed at.

**Wilson's theorem, now with the count.** The repo already knew that `iia` +
`surjective` + `nondictatorial` comes back satisfiable with an inverse dictator,
and there is a golden test asserting it (`tests/test_golden.py`). What that test
does not say is how many rules there are. Enumerating them: `iia` + `surjective`
at swf 3v3c has exactly six models, found in 2.20s, the three dictatorships and
the three inverse dictatorships, and adding `nondictatorial` leaves exactly the
three inverse dictatorships, in 2.11s. Wilson (1972) states it as dictatorial,
inversely dictatorial, or null; the null rule is universal social indifference,
which this frame cannot express because the social outcome is forced to be a
strict linear order, so the trichotomy arrives here as a dichotomy, and the
enumeration confirms there is nothing else hiding in the gap. Satisfiable with an
inverse-dictatorship witness at 2v3c (0.10s), 3v3c (2.19s), 4v3c (64.55s) and
2v4c (39.92s).
Source: Wilson, "Social choice theory without the Pareto principle", JET 5(3),
1972, 478-486, https://doi.org/10.1016/0022-0531(72)90051-8

**Arrow with a weaker top condition.** That `iia` + `pareto` leaves the dictator
was already a golden row; enumerating gives exactly the three dictatorships and
nothing else (1.96s). The new part is that `iia` + `unanimity` gives exactly the
same three (1.86s), where unanimity only constrains a candidate every voter puts
first and says nothing about any other pair. `iia` + `unanimity` + `nondictatorial` is impossible
at 2v3c (0.13s), 3v3c (3.05s), 4v3c (97.30s) and 2v4c (57.72s). This is not a new
theorem: it is Wilson's, plus the observation that an inverse dictator ranks the
unanimous favourite last, so the top condition alone deletes the inverse branch.
No source states it in this form; it is one line from Wilson.

**Muller-Satterthwaite.** `maskinmonotone` + `surjective` + `nondictatorial` is
impossible at 2v3c (0.12s), 3v3c (2.66s) and 4v3c (65.21s in the frontier walk,
124.80s when re-timed later under a heavier load), and
`maskinmonotone` + `surjective` has exactly the three dictatorships as models
(2.37s), the same three that `strategyproof` + `surjective` has (0.91s). The two
axioms imply each other at 2v3c and 3v3c, and the question was still open against a
200s budget at 4v3c. Timed back to back on the same machine at 4v3c, the
Maskin-monotone route costs about nine times the Gibbard-Satterthwaite route,
124.80s against 13.79s, because `improves` quantifies over pairs of profiles and
the grounder is quadratic there. Both of those numbers are inflated by other work
running at the time; the ratio is the point.

**Moulin's anonymity-and-neutrality condition.** A resolute anonymous neutral rule
exists exactly when the number of candidates cannot be written as a sum of
divisors of the number of voters greater than one (Moulin, *The Strategy of Social
Choice*, 1983; quoted and used in Xia, "Most Equitable Voting Rules",
https://arxiv.org/abs/2205.14838, and Bubboloni and Gori,
https://arxiv.org/abs/1506.06069). Two cells of this were already golden rows:
`tests/test_l3_reproduce.py` asserts scf 2v3c satisfiable and scf 3v3c impossible,
with hand reasons rather than the arithmetic. Filling in the grid is what makes the
arithmetic visible. Every cell the encoding resolved agrees with it:

| voters \ candidates | 2 | 3 | 4 | 5 |
|---|---|---|---|---|
| 2 | unsat 0.00s | sat 0.02s | unsat 1.20s | sat 530.43s |
| 3 | sat 0.01s | unsat 0.16s | sat 34.40s | |
| 4 | unsat 0.02s | sat 1.93s | | |
| 5 | sat 0.11s | sat 66.38s | | |
| 6 | unsat 1.30s | | | |

The two cells at 5v3c and 2v5c needed the grounder's two-million-clause ceiling
raised to forty million for the run; both then resolved, at 66.38s and 530.43s.
The empty cells are past the variable ceiling. At 6v3c the encoding did not fit
even with the ceiling raised.

The ranking side behaves as if the same arithmetic applies with the number of
strict rankings, m!, in place of the number of candidates. `anonymous` +
`neutral` for an swf is impossible at 2v3c (0.05s), 3v3c (0.40s), 4v3c (5.86s)
and 2v4c (5.11s), which are exactly the cells where m! is a sum of divisors of n
greater than one: 6 = 2+2+2, 6 = 3+3, 6 = 2+4, and 24 even. Five voters and three
candidates is the first cell where it is not, since the only divisor of 5 above
one is 5 itself, so the substitution predicts a rule exists there. It does, found
in 244.60s with the ceiling raised. That is a confirmed prediction and not a
proof: neutrality on rankings acts through the m! permutations of candidates, not
through the full symmetric group on the m! outcomes, so Moulin's counting argument
does not transfer for free.

**The quota rules.** `strategyproof` + `anonymous` at 3v3c has exactly twelve
models (1.19s): the three constant rules, and for each of the three pairs of
candidates, three rules that elect the second candidate when at least one, at
least two, or all three voters prefer it. That is the textbook shape of a
strategyproof anonymous rule on a two-element range, arrived at by enumeration.

**Borda and the Condorcet loser.** The added axioms were pinned against hand-known
rules before any of this ran. Borda with alphabetical tie-breaking satisfies
`condorcetloser` and fails `majority`; plurality does the reverse. Both are in
`tests/test_axioms_added.py`.

## candidates for something new

Three rows did not match anything in the literature on the first pass. One of
them turned out to be published, one is elementary enough that its absence is
probably just nobody writing it down, and one I could not place.

### tops-only rules and the Condorcet loser

`topsonly` + `condorcetloser` is a two-axiom impossibility. Solver receipts, core
`['topsonly', 'condorcetloser']`, minimal and verified, with a witness rule for
each axiom dropped:

| size | verdict | seconds |
|---|---|---|
| 2v3c | sat, and the witness is a rule with three outcomes | 0.02 |
| 3v3c | unsat, minimal core, both witnesses verified | 0.39 |
| 4v3c | sat, and the witness is plurality with alphabetical tie-breaking | 10.12 |
| 5v3c | unsat, minimal core, both witnesses verified | 351.08 |
| 2v4c | sat, witness plurality with alphabetical tie-breaking | 4.08 |
| 3v4c | unresolved: the `topsonly` quantifier over pairs of profiles passed the clause ceiling at 13,824 profiles | 139.19 |

The encoding gives out at three voters and four candidates. The argument does not.
A tops-only rule returns the same winner at every profile sharing a vector of
first choices, so if one such vector admits, for each candidate in turn, a
completion of the ballots making that candidate the Condorcet loser, the two
axioms cannot both hold, and the proof is those profiles. `notes/topsonly_check.py`
searches for such a vector directly, with no solver, and writes the profiles to
`notes/discovery/topsonly-condorcetloser.json`. At three voters and three
candidates the vector is ABC and the three profiles are:

    A is the Condorcet loser at  A > B > C | B > C > A | C > B > A
    B is the Condorcet loser at  A > C > B | B > A > C | C > A > B
    C is the Condorcet loser at  A > B > C | B > A > C | C > A > B

Whatever a tops-only rule elects at first choices ABC, one of those three profiles
elects a Condorcet loser.

Run over thirteen sizes, the vector exists at 3v3c, 5v3c, 6v3c, 7v3c, 3v4c, 4v4c,
5v4c, 3v5c and 3v6c, and does not exist at 2v3c, 4v3c, 2v4c or 2v5c. It agrees
with the solver at every size where both ran, and it settles 3v4c, where the
encoding gave up. Not finding a forcing vector is not a possibility proof, but at
2v3c, 4v3c and 2v4c the solver independently returns a rule.

Literature: not found. The adjacent facts are documented, that plurality can elect
the Condorcet loser (https://en.wikipedia.org/wiki/Condorcet_loser_criterion) and
that Borda is the only scoring rule that never does (Doi,
https://arxiv.org/abs/2604.05916). Neither is stated as an impossibility over the
whole class of tops-only rules. Searches across the tops-only literature and the
SAT-based impossibility literature returned nothing. Given how short the argument
is, the likely reading is that it is folklore nobody wrote down, not that it is
new mathematics.

### IIA and the Condorcet loser, for ranking rules

`condorcetloser` + `iia` for a social welfare function, with no efficiency or
non-dictatorship condition at all:

| size | verdict | seconds | detail |
|---|---|---|---|
| 2v3c | sat | 0.08 | witness: a dictatorship. Exactly two models, both dictatorships, enumerated exhaustively in 0.13s |
| 3v3c | unsat | 1.90 | core `['condorcetloser', 'iia']`, minimal, both witnesses verified |
| 4v3c | unsat | 63.57 | core `['condorcetloser', 'iia']`, minimal, both witnesses verified |
| 2v4c | sat | 37.47 | witness: a dictatorship |

Two voters is the exception because a Condorcet loser there has to be last on both
ballots, so a dictator never ranks it first. From three voters up the pair is
inconsistent on its own. `iia` + `majority` and `iia` + `condorcet` behave
identically across the same four sizes (2.26s / 69.49s and 2.34s / 69.78s at
3v3c and 4v3c), which puts the Condorcet loser criterion, a much weaker
requirement than either, in the same place.

Literature: not found. The Condorcet loser criterion is documented only as a
property of single-winner methods, not as an Arrovian condition on ranking rules.
The nearest published impossibility using it pairs it with positive involvement
and resolvability rather than IIA (https://arxiv.org/pdf/2601.10506). Campbell and
Kelly's survey of Arrovian weakenings is where it would be if it existed and
nothing citing it surfaced this.

What is claimed: unsatisfiable at 3v3c and 4v3c, with a minimal core and a witness
for each axiom dropped. There is no proof here for general n and m, and the
encoding does not reach far enough to suggest one.

### anonymity and reversal symmetry

`anonymous` + `reversal` is a two-axiom impossibility whenever the number of
voters is even, and has a rule at every odd size the encoding reached, in both
cases independent of the number of candidates:

| size | verdict | seconds |
|---|---|---|
| 2v3c | unsat | 0.02 |
| 3v3c | sat | 0.12 |
| 4v3c | unsat | 2.24 |
| 5v3c | unresolved: `anonymous` passed the clause ceiling at 7,776 profiles | 12.14 |
| 6v3c | unresolved: same, at 46,656 profiles | 14.18 |
| 2v4c | unsat | 0.30 |
| 3v4c | sat | 11.01 |

The even case has a two-line argument, and it is the direction that generalises.
Pair each ballot with its own reverse; the resulting profile is a permutation of
its own reversal, so anonymity forces the same winner at the profile and at its
reverse, which is what reversal symmetry forbids. The odd side is an observation
at three voters and nothing more, since five and six did not resolve.

This one is published. Bubboloni and Gori prove exactly this parity obstruction
inside the proof of Theorem 7(ii) of "Resolute refinements of social choice
correspondences", Mathematical Social Sciences 84 (2016) 37-49,
https://arxiv.org/abs/1506.06069, constructing the same self-reversing profile.
Their headline condition, gcd(n, lcm(m!, 2)) = 1, is for rules that are anonymous
and neutral and reversal-immune together, which is a stronger object than the pair
swept here, so the satisfiable odd cells above are not in tension with it. Adding
`neutral` to the pair reproduces it: `anonymous` + `neutral` + `reversal` is
impossible at 3v3c (0.22s) and 3v4c (68.48s), both cells where their gcd is 3 and
not 1, and both cells where `anonymous` + `reversal` on its own has a rule.
Reversal symmetry itself is Saari's immunity to the reversal bias, *Geometry of
Voting*, 1994.

## where it stops

The ceiling is the grounder, not the solver. Quantifiers over pairs of profiles
(`iia`, `topsonly`, `maskinmonotone`) are quadratic in the profile count, and the
symmetry axioms multiply the profile count by n! or m!. The clause ceiling is two
million by default; `notes/discover.py --max-clauses` raises it for a deliberate
push, which is how 5v3c and 2v5c got answered above and what the 530-second run
cost.

Resolved: scf up to 5 voters at 3 candidates and 3 voters at 4 candidates, swf up
to 5 voters at 3 candidates and 2 voters at 4 candidates, plus 2 voters at 5
candidates for the symmetry pair with the ceiling raised. Not resolved and
reported as such: every cell listed as unresolved above.

One more cell was cut rather than finished. The size-two sweep at swf 2v4c
answered 53 questions in 671 solver seconds, none of them an impossibility, and
was stopped with the remaining `iia` pairs still to go at about 68s each. Its records are in
`notes/discovery/mus-swf-2v4c.jsonl`; it is a partial cell and nothing here treats
it as a complete one.

## verdict

**JOSS software paper, not a research paper.**

Nothing in the social choice content is new. The two rows I could not place in the
literature are a three-profile argument and a finite-size solver verdict, and
neither is a theorem worth a paper: the tops-only result is elementary once
stated, and the IIA one is verified at two sizes with no general proof and no
prospect of one from this encoding. The rest of the interesting output is Wilson,
Muller-Satterthwaite, Moulin and the quota rules, arrived at honestly but arrived
at second.

What is worth writing up is the software. The prior art on SAT-based social choice
is a decade of one-paper-one-encoding work: Tang and Lin 2009
(https://www.sciencedirect.com/science/article/pii/S0004370209000320), Geist and Endriss 2011
(https://jair.org/index.php/jair/article/view/10686), Brandt and Geist on
strategyproofness (https://jair.org/index.php/jair/article/view/10988), Brandt,
Geist and Peters on the no-show paradox (https://arxiv.org/pdf/1602.08063),
Kluiving et al. 2020 on multiwinner rules, Boixel and Endriss 2020 on justifying
decisions, surveyed in Geist and Peters, "Computer-aided methods for social choice
theory" (https://dominik-peters.de/publications/sat-chapter.pdf). Almost none of
it shipped installable software. The adjacent maintained packages, `pref_voting`,
`abcvoting`, `preflibtools`, `votekit`, implement known rules and check a given
rule against axioms on given profiles; none takes an axiom set and returns a rule
or an impossibility. `comsoc-amsterdam/comsoc` is the closest, and it justifies a
given outcome rather than searching the space of rules.

The level-by-level enumeration of every minimal inconsistent subset of an axiom
library also did not turn up in the prior art as a general exercise. Geist and
Endriss do report all 84 impossibilities in a fixed space of twenty
preference-extension principles, which is the nearest precedent, but for one axiom
family and not framed as a procedure.

JOSS wants substantial scholarly effort, tests, documentation, and a repository
with more than six months of visible development
(https://joss.readthedocs.io/en/latest/submitting.html). The first three are here.
The last is a calendar problem, not a work problem. JORS and SoftwareX are the
alternatives if that becomes binding.

What the paper would be about: the axiom DSL, grounding facts in Python so false
guards leave the formula before Z3 sees it, verifying every returned rule against
its axioms without the solver, minimising unsat cores and producing a witness for
every proper subset, and the sweep modes above. What it would not be about is a
new theorem.
