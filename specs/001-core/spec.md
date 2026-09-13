# Spec 001: derivation core

## Problem

Social choice theory answers "is there a voting rule with properties X, Y, Z?" by
hand, one theorem at a time, over years. For small electorates the question is
finite and decidable. Nobody can currently type a set of axioms and get back either
a rule or a proof of impossibility in under a minute.

## What we are building

A deterministic Python package, `core`, that takes a set of named axioms and an
electorate size and returns one of:

- **sat**: a concrete voting rule satisfying every axiom, as an object the caller
  can evaluate on any profile over that electorate, plus a best-effort name if the
  rule matches a known one (dictatorship of voter i, constant rule, and so on).
- **unsat**: a minimal subset of the axioms that cannot be satisfied together,
  rendered as English prose, with a satisfying witness rule for every proper subset
  of that core so the minimality is checkable rather than asserted.
- **unknown**: the solver hit the time budget. The result states the budget, what
  was not decided, and the largest electorate at which the same axiom set did
  resolve.

## Users

- L2, a web UI that calls the core and stress-tests the returned rule on profiles a
  visitor types in.
- L3, an independent re-derivation that must reproduce the golden results without
  reading this implementation.
- A researcher at a terminal, through a CLI.

## Functional requirements

- FR-1 Two rule kinds. `scf` (profile to a single winner) and `swf` (profile to a
  social ranking). Each axiom declares which kinds it is defined for.
- FR-2 Axiom library of nine: nondictatorial, surjective, pareto, strategyproof,
  monotone, condorcet, iia, anonymous, neutral. Pareto is added to the eight named
  in the brief because Arrow needs it: IIA plus surjectivity plus nondictatorship
  is satisfiable (Wilson's inverse dictator), so without Pareto the machine would
  report the wrong thing for the flagship theorem.
- FR-3 Axioms are written in a DSL with quantifiers, connectives, ground predicates
  over the electorate, and profile-transforming terms. Parsed, not `eval`'d.
- FR-4 Frame constraints (exactly one winner; social ranking is a strict linear
  order) are always asserted and never appear in an unsat core.
- FR-5 Minimal core. Greedy deletion until no axiom can be dropped, each drop
  confirmed satisfiable.
- FR-6 English renderer for both branches.
- FR-7 Electorates from 2 to 4 voters and 3 to 4 candidates.
- FR-8 Configurable timeout, default 60s, degrading as described.

## Non-goals

- Irresolute rules (choice sets rather than single winners).
- Weak orders or indifference. Ballots and social rankings are strict.
- Domain restrictions (single-peaked and friends).
- Proving results at arbitrary n. The output is a base-case lemma and says so.

## Success criteria

- SC-1 Arrow: `{pareto, iia, nondictatorial}` over swf, 2 voters, 3 candidates,
  comes out unsat with all three in the minimal core.
- SC-2 Gibbard-Satterthwaite: `{strategyproof, surjective, nondictatorial}` over
  scf, 2 voters, 3 candidates, comes out unsat with all three in the minimal core.
- SC-3 Dropping nondictatorial from either yields sat, and the witness is
  recognised as a dictatorship.
- SC-4 Every golden case finishes in under 60s at 2 voters and 3 candidates.
- SC-5 Public interface is stable and documented for L2 and L3.
