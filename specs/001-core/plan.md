# Plan 001: derivation core

## Shape

Text in, Z3 in the middle, English out.

    axioms.agora --parse--> AST --ground(electorate)--> Z3 formulas
                                                            |
                            selector literal per axiom -----+
                                                            v
                                                    solve + minimise
                                                    /             \
                                              model                unsat core
                                                |                      |
                                              Rule                 English proof

## Modules

| file | job |
|---|---|
| `core/domain.py` | Electorate: ballots, profiles, permutations, ground predicates. No Z3. |
| `core/dsl.py` | Tokeniser, AST, recursive-descent parser for the axiom language. No Z3. |
| `core/ground.py` | AST plus Electorate to Z3 expression. The only place quantifiers are expanded. |
| `core/solve.py` | Frame constraints, selector literals, check, minimal core, timeout degradation. |
| `core/rules.py` | Rule object extracted from a model; recogniser for named rules. |
| `core/render.py` | Result to English. |
| `core/axioms.agora` | The axiom library, as data. |
| `core/cli.py` | `python -m core` |

## Key decisions

1. **Selector literals over `assert_and_track`.** One boolean per axiom, asserted
   as `sel_i -> body`. `check(sel_1, ..., sel_k)` gives an unsat core over axiom
   names directly, and dropping an axiom is just dropping an assumption, so
   minimisation needs no re-encoding.

2. **Grounding is eager and total.** Every quantifier is expanded over the finite
   electorate at encode time. Ground predicates (`unanimous`, `condorcet`, `pref`)
   evaluate to Python booleans during expansion, so false guards vanish before Z3
   sees them. This is what keeps the formula small.

3. **`prefers(p, a, a)` grounds to false.** Strict preference is irreflexive.
   Axioms that quantify over candidate pairs must guard with `neq` where they mean
   distinct candidates. Documented, and the parser does not silently fix it.

4. **Frame constraints are separate from axioms.** Exactly-one-winner for scf;
   asymmetry plus transitivity for swf. Asserted unconditionally so they can never
   land in a core and be rendered as "the impossibility is that rankings are
   transitive".

5. **Minimality is demonstrated, not asserted.** After the greedy pass, each axiom
   in the core is dropped once more and the resulting model is kept as the witness
   that the remaining axioms are jointly satisfiable.

## Risks

- **Blowup at 4 candidates.** swf at 3 voters and 4 candidates is 13,824 profiles.
  IIA is quantified over profile pairs, so grounding is quadratic. Mitigation:
  measure, and if Python grounding dominates, bucket profiles by pairwise signature
  before expanding. Do not pre-optimise.
- **Wrong axiom formalisation.** The failure mode that looks like success. Mitigation
  is the golden suite: if a formalisation is wrong, a known theorem stops reproducing.
