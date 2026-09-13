# 002: the web demo

The core answers the question. This is the thing a stranger can walk up to and use.

Status: specified 2026-09-13, before any web code.

## The user

Someone who has never heard of Arrow's theorem, standing in front of a laptop for
five minutes. They should leave knowing what the machine did and be unable to accuse
it of hand-waving.

## What they can do

1. **Pick axioms.** The nine-axiom library as first-class choices, each with the
   plain-English gloss the core already carries. Pick a rule kind (elect a winner /
   produce a ranking) and an electorate size. Axioms not defined for the chosen kind
   are visibly unavailable rather than silently missing.

2. **Invent an axiom.** Type a fairness property in plain English. A local model
   formalises it into the axiom DSL. Nothing the model writes is trusted: every
   candidate formalisation passes through gates before it can be used, and a rejected
   one comes back with a plain-English reason, not a stack trace.

3. **Mint.** Send the set to the core. Two outcomes, both first-class:
   - a rule exists: show it, name it if it is a textbook rule, and open the playground
   - no rule exists: show the minimal core as an impossibility proof a stranger can read

4. **Stress-test the rule.** Type an election or generate one, and see what the minted
   rule elects, next to what plurality, Borda and the Condorcet winner would do. The
   rule is a complete table over the electorate, so this is a lookup, not a guess.

5. **Read the proof.** The unsat branch, rendered: the axioms to blame, the statement
   that none is spare, and for each one, the rule that appears the moment you give it up.

## Gates on a formalised axiom (all must pass)

| gate | what it catches | failure message |
|---|---|---|
| grammar | the model cannot emit an unparseable formula: generation is constrained by a GBNF built from the DSL grammar itself | n/a, structurally impossible |
| parse | anything the grammar still lets through | where the parser stopped |
| sorts | `unanimous(p, i, b)` with a voter where a candidate goes: arity and argument sort per head, plus unbound and shadowed names | which argument of which predicate, and what sort it wanted |
| ground | the formula expands over a real electorate in the chosen mode without error | the grounder's complaint, in English |
| satisfiable | the axiom is not self-contradictory: some rule satisfies it alone | "no rule at all satisfies this, so it cannot be combined with anything" |
| non-vacuous | the axiom rules something out: the solver finds a rule that breaks it | "every rule there is already satisfies this, so it constrains nothing" |
| behaviour | shown, not gated: which textbook rules pass and which fail | the user decides whether that is what they meant |

The behaviour table is the honest part. The model's paraphrase is a claim; the table of
which named rules the axiom accepts and rejects is a fact, and it is what the user reads
before accepting.

## Non-goals

- No accounts, no persistence, no deployment. It runs on localhost.
- No new solving. The web layer never reasons; it asks the core and renders.
- The model never touches the answer. It only proposes DSL text, which is then checked
  by code that does not involve it.

## Constraints

- Offline. No paid API, no network at request time.
- The core is read-only to this lane. A bug found there is reported, not patched.
- One viewport, works on a phone, colourblind-safe: outcome is never carried by hue
  alone. OLED black.
