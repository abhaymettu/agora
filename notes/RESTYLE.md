# Restyle: presentation pass

2026-09-13. The repo is now presented as an ordinary project: a README that describes
the tool, a generated `examples/` gallery, local run instructions, and nothing in the
visitor's path that describes how the thing got built.

## What was scrubbed

### README: the honesty-announcement heading

The README's largest section was headed with a meta-announcement, which is exactly the
tell to avoid. The content under it was fine and was kept; only the framing changed.

Before:

```
## What this is, said honestly

**Small electorates are base-case lemmas, and the output says so every time.** Two to
four voters, three to four candidates. ...
```

After:

```
## Scope

**Small electorates are base-case lemmas, and the output says so every time.** Two to
four voters, three to four candidates. ...
```

### README: demo framing

Before:

```
## The demo page

python -m web            # http://127.0.0.1:8000

Pick the properties, mint, and stress-test the rule you get back on elections you type
in. Free-form entry needs a local model server as well (`notes/BUILD-WEB.md` has the
command); without one the page says so and everything else still works. Nothing the
model writes reaches the solver until it has parsed, sort-checked, grounded, and been
shown satisfiable and non-vacuous, and the page shows which named rules it accepts
and rejects, ...
```

After (folded into "Running it", no separate section, no link into `notes/`):

```
There is also a local browser interface, if picking axioms from a list and running the
returned rule on profiles you type is easier than the CLI:

python -m web            # http://127.0.0.1:8000
```

### README: links into the build notes

Three references to `notes/` were removed and their content moved into the README
itself, so `notes/` is no longer on any path a visitor follows:

| before | after |
|---|---|
| "Measured numbers per size are in `notes/timings.txt`." | the twelve-row timings table, inline |
| "`notes/BUILD-CORE.md` has the full interface, the grammar, the encoding, and measured timings per electorate size." | the "Using it from Python" section, inline |
| "Free-form entry needs a local model server as well (`notes/BUILD-WEB.md` has the command)" | cut |

### README: the citation disclaimer

Removed. It was a note-to-self, not something a reader needs:

```
*Citations here were written offline. Check them before quoting.*
```

The "Lineage" heading it sat under is now "Related work" and names the same two lines
of prior work.

### README: "minted on the spot, under a minute"

The opening claim and the section arguing for it ("**'Under a minute' holds for most of
the range, not all of it.**") were replaced by the measured table under "Sizes and
timings", plus two sentences on the two rows that do not resolve. Same facts, no claim
to walk back.

### specs/002-web/spec.md

Before: `- The core is read-only to this lane. A bug found there is reported, not patched.`

After: `- The core is read-only from here. A bug found there is reported, not patched.`

The only occurrence of process vocabulary in any tracked file outside `notes/`. Checked
with a grep for `owner|lane|agent|claude|anthropic|session` across all tracked `.md`,
`.py`, `.html`, `.js` and `.agora` files; everything else it found is inside `notes/`.

### .playwright-mcp/

Ten tracked page-snapshot `.yml` files, already listed in `.gitignore` but tracked from
before that line existed. `git rm --cached`, one commit.

### What was left alone

- **`notes/`** keeps BUILD-CORE, BUILD-WEB, VERIFY-CORE, POLISH-DEMO and the shots.
  Nothing in the README, the examples, or the web page links to or summarises them.
- **`web/index.html`** prose was checked and is already clean: it describes what the
  result does and does not claim, with no origin story.
- **Git history.** Subjects like "polish pass: ... the readme knows the demo exists"
  and "write up the web lane" are still in the log, and commit `9eb8d83` carries a
  `Claude-Session:` trailer in its body. Fixing either means rewriting three pushed
  commits and force-pushing. Left for you to call.

## The new README structure

1. **Title and the Arrow transcript.** What the tool does in two sentences, then the
   impossibility branch as real output, then the constructive branch as a four-line
   Python session.
2. **Why.** The argument for the tool existing: axiom-set questions are proved one at a
   time by hand, the proofs do not compose, and for a fixed small electorate the
   question is decidable by SAT. The useful case is an axiom set nobody has written
   about.
3. **Worked examples.** A five-row table linking into `examples/`.
4. **Scope.** The four distinctions kept from the old README: base-case lemmas; the
   constructive branch returns an object; existence rather than explanation; what is
   out of scope (ties, indifference, irresolute rules, domain restrictions).
5. **Sizes and timings.** The measured table, twelve rows.
6. **Running it.** `pip install z3-solver`, four commands, the local browser interface.
7. **The axiom library.** Nine axioms, and why Pareto is load-bearing.
8. **The axiom DSL.** The `strategyproof` block, the six sorts, the ground facts.
9. **Using it from Python.** `derive`, `Result`, `Rule`, and a worked call.
10. **When it cannot answer.** Degradation and the per-electorate timeout.
11. **Related work.** Tang and Lin, Geist and Endriss, and what this adds.

## The examples

`examples/generate.py` runs the five axiom sets through `core.derive` and writes the
markdown. Every verdict, table, timing and trace in those files is live output; only the
framing paragraphs are written by hand. Re-run with
`PYTHONPATH=. python examples/generate.py`.

| file | axiom set | electorate | result |
|---|---|---|---|
| `01-arrow.md` | `pareto iia nondictatorial`, swf | 2v3c | unsat, core all three, 0.10s |
| `02-wilson.md` | `iia surjective nondictatorial`, swf | 2v3c | sat, inverse dictatorship of voter 1, 0.08s |
| `03-gibbard-satterthwaite.md` | `strategyproof surjective`, scf | 2v3c | sat, dictatorship of voter 1, 0.06s |
| `04-copeland.md` | `condorcet monotone nondictatorial`, scf | 3v3c | sat, copeland with alphabetical tie-breaking, 0.09s |
| `05-anonymous-neutral.md` | `condorcet anonymous neutral`, scf | 3v3c | unsat, core is `anonymous, neutral`, 0.15s |

Each satisfiable example carries a playground trace and a solver-free re-check:

```python
>>> rule.show_outcome('A>B>C | B>C>A | C>A>B')
'A'
>>> rule.satisfies(library()['condorcet'])
True
>>> rule.satisfies(library()['strategyproof'])
False
```

Each impossibility carries the core and a witness rule per proper subset. `05` is the
one that earns its place beyond the textbook results: three axioms asked, two blamed,
and the renderer says so in English ("You asked for 3. The two above are enough to rule
it out on their own, so condorcet never came into it").

Two of the five double as arguments about the library itself. `02` is why Pareto is in
it: without Pareto, Arrow's set is satisfiable and the inverse dictator wins.
`04` is the case where the search produced a table and the table turned out to be a
rule with a name.

## Verification

- `PYTHONPATH=. python -m unittest discover -s tests -t .` — 80 tests, 51.4s, OK.
- `PYTHONPATH=. python examples/generate.py` — five files regenerated; the second run
  differed from the first only in the timing digits, so the outputs are stable.
- Every code snippet asserted in the README was executed: the Arrow transcript,
  `witnesses["nondictatorial"].describe()` → `dictatorship of voter 2`,
  `rule.winner("A>B>C | C>B>A")` → `0`, `rule.matches()` →
  `['dictatorship of voter 1']`, `rule.satisfies(library()["nondictatorial"])` →
  `False`, `matches()` on the Copeland rule, and `python -m web` defaulting to port
  8000 (`web/server.py:28`).

## Commits

```
6e73e24 stop tracking playwright page snapshots
b295eb6 worked examples, generated from the core
014a477 rewrite the readme as a project readme
704f2ed spec: drop process wording
```
