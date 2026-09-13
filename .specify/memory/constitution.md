# AGORA Constitution

Version 1.0.0 | Ratified 2026-09-13 | Last amended 2026-09-13

AGORA is a fairness-existence machine. You name the properties a fair voting rule
should have; it either hands you a rule that provably has all of them, or a proof
that no such rule can exist.

## Core Principles

### I. Deterministic core (non-negotiable)
`/core` imports no model, calls no network, and consumes no paid API. Same input,
same output, every run. The only runtime dependency is `z3-solver`. Anything that
cannot be decided by the solver is reported as undecided, never guessed.

### II. Claims carry receipts
Every statement the machine makes about a rule or an impossibility is backed by an
object the caller can check: a satisfying rule that can be evaluated on any profile
in its electorate, or a minimal unsat core with a satisfying witness for each proper
subset. No output asserts more than the solver established.

### III. Axioms are data
Axioms live in a DSL file, not in Python control flow. Adding an axiom means adding
a definition, an English gloss, and nothing else. The grounder and the renderer are
written once and are axiom-agnostic.

### IV. Honest bounds
Results are scoped to the electorate they were proved over. A timeout degrades to a
stated partial bound naming the largest electorate that finished; it never silently
reports success, and it never claims an impossibility lifts to sizes that were not
checked.

### V. Golden theorems are the test suite
Known results are the regression tests. Arrow and Gibbard-Satterthwaite base cases
must come out unsatisfiable with the expected minimal core; dropping an axiom must
come out satisfiable with the expected witness shape. A change that breaks a golden
theorem is wrong until proven otherwise.

## Scope

Small electorates: 2 to 4 voters, 3 to 4 candidates. This is where the classical
theorems bite and where exhaustive search finishes in seconds. Results at this size
are base-case lemmas, stated as such.

## Governance

The constitution governs `/core`. Downstream lanes (web UI, independent
re-derivation) consume the core's public interface and may not reach past it.
Amendments are versioned here and reflected in `notes/BUILD-CORE.md`.
