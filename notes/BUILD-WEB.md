# L2: the web demo

Built 2026-09-13. Python 3.14, no new runtime dependency. macOS arm64.

The core answers the question. This is the thing a stranger can walk up to: pick the
properties a fair voting rule should have, get back a rule that provably has them or a
proof that none can exist, then stress-test the rule on elections typed in the room.

Nothing here reasons. It asks `core`, renders what it said, and refuses to pass along
anything the core has not checked.

## What was built

| file | lines | job |
|---|---|---|
| `web/app.js` | 473 | State and rendering. No dependencies, no build step. |
| `web/style.css` | 298 | OLED black, one viewport, colourblind-safe. |
| `formalize/grammar.py` | 239 | The DSL signature, the GBNF built from it, the sort checker. |
| `formalize/model.py` | 221 | llama.cpp client, ollama fallback, the prompt and its examples. |
| `web/server.py` | 192 | `http.server`: static files plus four JSON endpoints. |
| `formalize/__init__.py` | 191 | The gate pipeline. The only thing `web/` imports. |
| `tests/test_web.py` | 150 | The endpoints, against a real socket. |
| `tests/test_formalize.py` | 141 | The gates, with no model in the loop. |

1,905 lines, and the only import outside the standard library is the core's own `z3`.

Written before any of it: `specs/002-web/{spec,plan}.md`.

## Running it

Two processes. The app runs without the second one; free-form axiom entry is what needs it.

```bash
cd ~/code/agora
python -m venv .venv && .venv/bin/pip install z3-solver     # once

# 1. the local model, over the GGUF ollama already pulled
llama-server -m ~/.ollama/models/blobs/sha256-667b0c1932bc6ffc593ed1d03f895bf2dc8dc6df21db3042284a6f4416b06a29 \
  --port 8081 -c 4096 -ngl 99 --no-webui

# 2. the app
.venv/bin/python -m web            # http://127.0.0.1:8000
```

`AGORA_PORT` moves the app, `AGORA_LLAMA_URL` and `AGORA_OLLAMA_URL` move the backends.
With neither backend up the page says so plainly and disables free-form entry; the
library, the derivation, the playground and the proof view all still work.

Tests, 80 of them, 48s:

```bash
.venv/bin/python -m unittest discover -s tests -t .
```

The two model-dependent tests skip themselves when no backend answers.

## The demo, in the order it was driven

Each step below was run through the page in a real browser, not asserted from a test.

1. **The impossibility branch.** Ranking rule, 2 voters, 3 candidates, `pareto + iia +
   nondictatorial`. Comes back `No rule can exist` in 0.11s, with the minimal core, the
   statement that none of the three is spare, and the rule that appears when each one is
   given up. That is Arrow, derived in the browser. Shot 03.
2. **The constructive branch.** Winner rule, `strategyproof + surjective`. Comes back
   `A rule exists`, named: dictatorship of voter 1. Shot 04.
3. **The playground.** "Find a disagreement" walks the rule's own table for a profile
   where it parts company with plurality, Borda or the Condorcet winner, and finds one:
   v1 `B > A > C`, v2 `A > B > C`, the rule elects **B** while plurality and Borda elect A.
   That is the dictator, visible. Shot 04.
4. **Free-form entry.** Typed: "the outcome should not depend on which voter cast which
   ballot". The 8B formalises it to
   `forall p:profile, t:vperm, c:cand. wins(p,c) <-> wins(permv(p,t),c)`, all five gates
   pass, and the behaviour table shows it failing for both dictatorships and holding for
   plurality, Borda, Copeland and the constant rules. Shot 05.
5. **A rejection.** Typed: "if a voter moves the winning candidate up their own ballot,
   that candidate should still win". The model reaches for a permutation it never bound;
   the checker rejects it, tells the model exactly which name was never introduced and
   what is in scope, the model tries twice more and still fails. The page shows every
   attempt and its reason. Editing the formula by hand to
   `forall p:profile, i:voter, c:cand. wins(p,c) -> wins(lift(p,i,c),c)` and pressing
   "Check again" passes all five gates. Shot 06.
6. **Minting with an invented axiom.** Adding the accepted axiom to the list and asking
   for it together with `condorcet` returns a rule with no textbook name, 3 distinct
   outcomes over 36 profiles, runnable in the playground like any other. Shot 07.
7. **Mobile.** 390 x 844, no horizontal overflow, every panel readable. Shot 08.

## The formalisation pipeline

```
plain English
   -> llama.cpp /v1/chat/completions, generation constrained by a GBNF
      built from the DSL's own signature
   -> parse        the core's parser, on the string
   -> sorts        arity and argument sort per head, unbound names, reused names
   -> ground       expands over 2 voters and 3 candidates without complaint
   -> satisfiable  the solver finds a rule satisfying it alone
   -> non-vacuous  the solver finds a rule that breaks it
   -> behaviour    which textbook rules it accepts and rejects  (shown, not gated)
```

**The grammar is generated, not written.** `formalize/grammar.py` holds one table of
heads and their argument sorts, and gets two things out of it: the GBNF the model
generates under, and the sort checker that decides. They cannot drift, because there is
one table. A formula that does not parse is structurally impossible rather than merely
unlikely, and every head is applied with the right number of arguments by construction.

The grammar is deliberately bounded: at most five bindings per quantifier, at most one
quantifier prefix inside another, parentheses one level deep. Without those ceilings an
8B under a grammar with open repetition writes forty bindings and never returns. Every
axiom in the shipped library fits inside the bounds.

**Two gates are solver questions, and both matter.** Satisfiability catches an axiom
that contradicts itself. Vacuity asks the solver for a rule that *breaks* the axiom: if
there is none, the axiom is true of every rule there is and adding it changes no answer.
It has to be asked that way. An earlier version asked whether any of the eight rules we
can name fails the axiom, and that version rejected `monotone`, which every one of those
eight satisfies at two voters and three candidates and which is nonetheless a real
axiom. There is a test for exactly that: every library axiom must pass every gate.

**A rejected draft is not thrown away.** The gate's own complaint goes back to the model
as feedback and it tries again, twice. The first draft is greedy so the same question
gives the same answer; repairs raise the temperature, because at zero a model told it is
wrong will write the same thing again. Every attempt and its reason is kept and shown,
so what the page displays is the checker deciding, not the model asserting.

**What the gates cannot do.** They prove a formalisation is well formed, satisfiable and
not a tautology. They cannot prove it means what you said. That is what the behaviour
table is for: if a rule you would call fair fails, or one you would not call fair passes,
the formalisation is not what you meant, and the formula is editable in place with a
"Check again" button next to it. The page says this in those words.

**The browser is not trusted.** An axiom that arrives inline on `/api/derive` is put
through the gates again server-side before it reaches the solver. There is a test that
posts a self-contradictory axiom straight to the endpoint and expects a 400.

## Where the demo runs

The playground runs entirely in the browser. `Rule.as_dict()` already returns the whole
outcome table keyed by a printable profile, which is 36 to 1,296 rows at the sizes in
scope, so stress-testing a rule is a dictionary lookup with no round trip and nothing on
the page can drift from what was proved. Plurality, Borda and the Condorcet winner are
computed alongside it in a few lines of JavaScript, from the same ballots.

Endpoints:

```
GET  /api/axioms       the library, with modes and glosses
GET  /api/health       which model backend is up, if any
POST /api/derive       {axioms, mode, voters, candidates} -> the core's result, plus its English
POST /api/formalize    {text, mode} -> a proposal and its gate report
POST /api/vet          {formula, mode} -> the same gates, on a formula edited by hand
```

## The interface, and one place this lane reaches past it

The constitution says downstream lanes consume the core's public interface and may not
reach past it. This lane holds to that with one exception, named here rather than
hidden: `formalize/__init__.py` imports `Context` and `encode` from `core.ground`, which
are module-level but not in `core.__all__`. They are what makes "does this ground?" a
gate of its own, with its own message, instead of an exception surfacing from inside a
derivation. `formalize/model.py` reads `core.solve.AXIOM_FILE` to quote the library's own
formulas as worked examples for the model, so the examples cannot drift from the library.
Everything else goes through `core`'s public names.

## Notes for L1

**No core bug found.** Everything the interface promised behaved as `BUILD-CORE.md` says,
including the two golden results this lane leans on hardest (Arrow at 2v3c unsat with a
three-axiom minimal core in 0.11s, `strategyproof + surjective` sat and recognised as a
dictatorship). Two observations, neither a defect:

- `monotone` in `scf` mode is satisfied by all eight rules `reference_rules` can name at
  2 voters and 3 candidates. That is a fact about the size, not a bug, but it is a trap
  for anyone who tries to test "is this axiom vacuous" against the named rules.
- `Rule.describe()` returns `"no textbook match: N distinct outcomes over M profiles"`,
  which is a sentence fragment rather than a name, so a caller that wants to write "It is
  X." has to special-case it. The web layer asks for `rule.matches()` separately and
  writes different copy in each case.

## Known rough edges

- **The 8B is the weakest link, by design.** Across the dozen or so properties typed at
  it during the build, most survived the gates on the first draft and the repair loop
  recovered one or two more; that is a small sample and not a measured rate. Its
  recurring mistake is using a permutation or ballot variable it never bound. The pipeline handles this correctly, in that it rejects and explains, but a
  stranger who types something awkward will sometimes have to edit the formula. The
  edit-and-recheck path exists for that reason and is part of the demo.
- **The model names things loosely.** It called an anonymity axiom `neutrality` during
  the drive. The name is cosmetic; the formula and the gates are what count. A name
  collision with a library axiom gets a numeric suffix rather than a complaint.
- **A gate rejection message can repeat.** When the model makes the same mistake three
  times, the ladder shows the same objection three times, shortened to its first sentence
  for the history rows.
- **No cancel button.** A derivation at the largest offered size (4 voters, 3 candidates)
  runs to its 60s budget with a spinner and no way to stop it early. The size dropdown
  labels that row "often undecided inside the budget" so nobody wanders into it blind.
- **Custom axioms are per-session and per-rule-kind.** They live in the page's memory,
  are lost on reload, and are dropped when the rule kind changes, because a formalisation
  is written for one kind. Nothing warns before dropping them.
- **Free-form entry needs the model server started separately.** No supervision, no
  restart. If it dies mid-session the page reports the backend as gone on the next
  reload, not immediately.
- **`llama-server` is pointed at an ollama blob by its sha256 path.** Re-pulling the
  model changes the digest and the command above stops working. `ollama list` plus the
  manifest at `~/.ollama/models/manifests/registry.ollama.ai/library/llama3.1/8b` gives
  the current one.

## Screenshots

All under `notes/shots/`, taken at 1440 x 900 except the last.

| | |
|---|---|
| `01-picker.png` | the question: rule kind, electorate, the nine properties |
| `02-invent-panel.png` | the free-form box and the backend it is talking to |
| `03-proof.png` | Arrow: the minimal core, and the rule that appears without each axiom |
| `04-rule-and-playground.png` | Gibbard-Satterthwaite the other way, and the dictator caught disagreeing |
| `05-formalize-accepted.png` | five gates green and the behaviour table that says what it means |
| `06-formalize-rejected.png` | the model's attempts, each with the checker's reason |
| `07-custom-axiom-minted.png` | an invented axiom in the list, minted alongside a library one |
| `08-mobile.png` | 390 x 844 |
| `09-honest-note.png` | the disclosure a stranger opens when they wonder what was proved |
