# 003 - discovery sweep

## What

Extend the axiom library past the nine it shipped with, then enumerate which
subsets of it are inconsistent and which are not, across every electorate size
the encoding survives. Record receipts for each verdict.

## Why

The core reproduces Arrow, Gibbard-Satterthwaite and friends. Those were the
targets it was built against, so reproducing them tests the encoding and not
much else. The question this spec answers is whether the same machinery says
anything that was not already the thing it was aimed at.

## Scope

In:

- New axioms, preferring properties that are stated in the literature but rarely
  run through a solver: no veto power, Maskin monotonicity, tops-only, the
  majority criterion, the Condorcet loser criterion, reversal symmetry,
  unanimity as distinct from Pareto.
- The ground facts and profile terms those axioms need, in the style of the ones
  already in `core/domain.py`.
- A sweep harness under `notes/` that enumerates minimal inconsistent subsets by
  level with upward pruning, counts satisfying rules where the count is small,
  and writes one JSON record per question asked.
- `notes/DISCOVERY.md`: the map, the candidate-novel outputs with literature
  evidence, a verdict.

Out:

- Any change to how `derive` works, to the renderer, or to the web demo.
- Variable electorate size. Participation, reinforcement, and homogeneity all
  need a rule defined over more than one voter count; this core fixes n.
- Coalitions. Group strategyproofness needs a coalition sort the DSL does not
  have.
- Paper drafting.

## Done when

- Every new axiom has a test that fixes its truth value against a rule whose
  behaviour is known by hand.
- Existing golden tests still pass unchanged.
- Every verdict in `DISCOVERY.md` names its axiom set, size, solve time, and
  either an unsat core or a witness rule.
- Timeouts are reported as timeouts, not as absences.
