# Polish and demo rehearsal

Checked 2026-09-13, 04:08 to 04:25. Python 3.14, z3-solver 5.1.0, llama.cpp serving the
llama3.1 8B ollama blob on :8081, macOS arm64. The page was driven in a headless Chromium
(Chrome for Testing 153) through the Playwright plugin, on a fresh profile, at 1440 x 900
and 390 x 844.

**Verdict: DEMO-READY.** Every step of the demo script ran end to end and every mint
landed in under seven seconds. Seven things were off and six are fixed in the working
tree, listed at the end with what changed. The seventh is a commit trailer that needs a
history rewrite, which is the owner's call, not this lane's.

## What was run, in order

The app was started fresh from the committed tree (`AGORA_PORT=8010 python -m web`) so
the check is of what is in git, not of the process L2 left running on :8000. Timings are
round trips measured in the page, from `fetch` start to response.

| step | what | result | time |
|---|---|---|---|
| 0 | Mint with nothing picked | "Pick at least one property first." | |
| 1 | ranking rule, 2v3c, pareto + iia + nondictatorial | No rule can exist. Core: all three. Without pareto: a rule that ignores voter 2; without nondictatorial: dictatorship of voter 1; without iia: no textbook match. Footer: 36 profiles, 216 variables, 0.11s, base-case lemma. | 115 ms |
| 2 | "The machine's own words" and "What this result does and does not claim" | both open, the rendered CLI text matches the cards, the honest note is the README's three distinctions in fewer words | |
| 3 | winner rule, 2v3c, strategyproof + surjective | A rule exists. It is dictatorship of voter 1. Both properties listed, playground, full 36-row table | 95 ms |
| 4 | Find a disagreement | v1 `A > B > C`, v2 `B > C > A`: the rule elects A, Borda elects B, plurality is a tie, no Condorcet winner. (Before the fix below it found a plurality "disagreement" that was a 1-1 tie broken alphabetically.) | |
| 5 | hand-set election v1 `C > B > A`, v2 `A > B > C` | the rule elects C, which is voter 1's top: the dictator, visible | |
| 6 | free-form: the box's own placeholder, "a candidate that everyone puts last should never win" | accepted, all five gates green, but the 8B wrote `condorcet(p,c) -> not wins(p,c)`, which is the wrong axiom. The behaviour table said so: every named rule fails it, plurality included. See fix 2. | 1.4 s |
| 7 | edit the formula by hand to `forall p:profile, c:cand. (forall a:cand. neq(a,c) -> unanimous(p,a,c)) -> not wins(p,c)`, Check again | accepted; dictatorships, plurality, Borda, Copeland hold, the three constant rules fail. That is the table a correct formalisation should give. | 23 ms |
| 8 | Add to the list, mint it with condorcet | A rule exists, no textbook name, 3 distinct outcomes over 36 profiles, runnable in the playground | 85 ms |
| 9 | free-form, deliberately bogus: "the tallest voter's second favourite colour decides the winner on tuesdays" | accepted. The model reached for anonymity, its worked example, and the gates passed it because it is a well-formed, satisfiable, non-vacuous formula. The page's own caveat covers this ("they cannot prove it means what you said") but see the note on it below. | 1.5 s |
| 10 | free-form, the sentence L2 reported as rejected: "if a voter moves the winning candidate up their own ballot, that candidate should still win" | rejected, three attempts, each using a permutation variable it never bound, each attempt and reason shown in the ladder. Matches BUILD-WEB step 5 exactly. | 5.4 s |
| 11 | `/api/vet` directly with garbage, an unbound name, a contradiction, a tautology | rejected at sorts, sorts, satisfiable, non-vacuous respectively, each with a one-sentence reason | |
| 12 | `/api/derive` with a self-contradictory inline axiom | 400: the server re-vets, the browser is not trusted | |
| 13 | the three slower sizes offered by the picker, through the API | 3v3c condorcet + strategyproof: unsat in 0.5 s. 3v3c Arrow: unsat in 2.5 s. 2v4c strategyproof + surjective: sat in 6.8 s. 2v4c anonymous + neutral: unsat in 1.2 s. | |
| 14 | mobile, 390 x 844: picker, mint Arrow, custom axiom card, rejection ladder | no horizontal overflow (scrollWidth 390), every card readable, the verdict heading lands directly under the Mint button after a tap | |
| 15 | console, both widths, whole session | 0 errors, 0 warnings | |

Under a minute is not close to being tested by the sizes the picker offers. The 4v3c
row, labelled "often undecided inside the budget", was not driven; L1's timings put it
at 77 s for a ranking rule and the label says so.

Four more sentences were put through `/api/formalize` to choose a placeholder that the
model gets right under greedy decoding, since the first draft is deterministic:

| sentence | result |
|---|---|
| the outcome should not depend on which voter cast which ballot | anonymity, correct, first draft, 1.5 s |
| a candidate that everyone puts last should never win | anti-Condorcet, wrong, first draft |
| if every voter puts the same candidate first, that candidate wins | rejected after three drafts, never wrote unanimity |
| relabelling the candidates relabels the winner | neutrality, correct after one repair, 3.0 s |

Two right, one wrong-but-accepted, one rejected. That is the 8B, and BUILD-WEB already
says it is the weakest link. For the room: type the placeholder, which works, and if
someone else wants to type their own, the behaviour table is where to look, not the
green ticks.

## Screenshots

Under `notes/shots/polish-*.png`, all after the fixes unless said otherwise. Looked at
every one.

| | what I saw |
|---|---|
| `polish-01-picker.png` | 1440 x 900, first paint. Black ground, the picker in the left quarter, Mint pinned as a bar at the foot of the pane, the empty stage with its one-line hint. Nothing clipped. |
| `polish-02-arrow.png` | Arrow, both disclosures open. Amber verdict, the three blamed axioms in amber mono, the three witnesses, the CLI text in a card, the honest note. Amber and blue differ in lightness as well as hue; the glyphs (square for impossible, dot for exists) carry the state without colour. |
| `polish-03-disagreement.png` | The dictator caught by Borda: rule A, Borda B, plurality "tie", Condorcet "none". |
| `polish-04-formalize-edited.png` | The hand-edited axiom accepted, five gates, the behaviour table reading the way a correct axiom should. |
| `polish-05-formalize-rejected.png` | The rejection ladder: two earlier drafts with their reason, then parse clear and sorts failing with the full message. |
| `polish-06-empty-mint.png` | Mint with nothing picked: the error line pinned just above the bar, readable without scrolling. |
| `polish-07-mobile.png` | 390 wide, full page, before anything is minted. Single column, the Mint button back to a rounded block, no overflow. |
| `polish-08-mobile-result.png` | 390 wide, full page, a custom axiom in the list with its formula, and the rejection ladder below the picker, wrapping cleanly. Taken before the fixes; nothing in it changed. |

Against the bar: OLED black, yes (`#000`, ink `#ededef`). Glassy, yes (`backdrop-filter`
on the cards, with a solid fallback under reduced transparency). Colourblind-safe, yes
by the two-channel rule the stylesheet states. One viewport: on desktop it was not, see
fix 1; it is now. Mobile: works.

## Commit story

`git log --oneline -20`: twenty commits, every subject lowercase, plain English, one
line, no ticket prefixes, no conventional-commit tags, nothing that reads as generated.
Author is the owner on all of them. One thing is off:

- `9eb8d83` ("l3 verification note...") carries a `Claude-Session:` trailer in its body.
  It is the only commit with any trailer. It is on `origin/main`, three commits back.
  Removing it means rewriting those three commits and force-pushing; that is the owner's
  decision, so it is listed under FAIL items with the command, not done. This lane's own
  commit carries no trailer.

## README

The first sentence: "You name the properties a fair voting rule should have. The machine
either hands you a rule that provably has all of them, or hands you a proof that no such
rule can exist, minted on the spot, under a minute." That is the sharpest thing that is
true, and it is true: both branches were driven and the slowest offered size took 6.8 s.

The three distinctions are present and plainly put: base-case lemmas at 2 to 4 voters,
the lift to every electorate is a separate argument the machine does not make; the
constructive branch returns the rule as an object; the ILLC justify line answers "why
this result, here" for one profile and this answers existence over all profiles. It
also says where under a minute stops being true, with the measured numbers.

What was wrong: the README did not know the web demo or the free-form entry existed. It
said "no way to add a tenth except by writing it in the DSL" and "Nothing here calls a
network or a model", both false of the repo since `f6d17eb` and `f1fe2d6`. That is under-
claiming rather than hype, but a stranger who reads the README and then opens the page
would find a feature the README denies. Fixed, see fix 5.

## L3 re-verification

Re-run against the tree after L2 landed:

```
PYTHONPATH=. .venv/bin/python -m unittest tests.test_l3_reproduce -v   # 21 tests, 26.8s, OK
PYTHONPATH=. .venv/bin/python notes/l3_matrix.py                       # 16 rows, 29 rules, 73,230 axiom instances, 0 problems
PYTHONPATH=. .venv/bin/python -m unittest tests.test_web tests.test_formalize   # 35 tests, 7.0s, OK, after the server change
PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -t .       # 80 tests, 47.5s, OK
```

The regenerated matrix is row for row the one in VERIFY-CORE.md: the same eleven golden
rows and five added rows, the same cores, the same witness shapes (dictator v2 for
Arrow without nondictatorship, inverse dictator v1 for Wilson, dictator v1 for GS
without nondictatorship). Core still green.

## FAIL items, and what was done

1. **Mint below the fold on desktop.** `web/style.css`. At 1440 x 900 the picker pane
   needed 1459 px and the Mint button sat at y = 1350, 450 px under the fold, with the
   invent box and the last three properties. Fix, applied: the button is a `position:
   sticky` bar flush with the bottom of the pane, edge to edge, solid background, and the
   list scrolls under it; the error line is sticky just above it so "Pick at least one
   property first." is visible; the pane's 64 px bottom padding goes. Both revert to the
   rounded block under the 900 px media query, where the page scrolls as a whole. A
   first attempt that kept the rounded button and added a shadow left it floating over
   the condorcet card with a 64 px gap under it; that was worse and was replaced.

2. **The placeholder sentence formalises wrongly.** `web/index.html`. The first thing a
   stranger will type is the example in the box, and the model turns it into "a
   Condorcet winner never wins", accepted. Fix, applied: the placeholder is now "the
   outcome should not depend on which voter cast which ballot", which the model gets
   right on the first draft, deterministically.

3. **The playground's "disagreement" was a tie-break.** `web/app.js`, `scores` and
   `findDisagreement`. Plurality and Borda broke ties alphabetically without saying so,
   and the search only looked at plurality and the Condorcet winner. With two voters a
   dictator never disagrees with plurality except on a tie, so the showcase step was
   "the rule elects B, plurality says A" on a 1-1 vote. Anyone in the room who counts
   would object. Fix, applied: a tied score reads "tie" and counts as neither agreement
   nor disagreement, and Borda is in the search. The dictator is now caught by Borda on
   an untied profile.

4. **Static files were cached with no revalidation.** `web/server.py`. `SimpleHTTPRequestHandler`
   sends `Last-Modified` and nothing else, so a browser that had the page open earlier
   (the owner's, from L2) kept serving the old `app.js` after the fixes above; the
   headless browser did too, on the first reload. Fix, applied: `Cache-Control: no-cache`
   on every response, so files are revalidated on each load. Server tests pass.

5. **README denied the demo page and the free-form entry existed.** `README.md` lines
   78 and 92. Fix, applied: the sentence about a tenth axiom now says it can be typed in
   English on the demo page behind five checks; "Nothing here calls a network or a
   model" is now a statement about the core; a short "The demo page" section says how to
   run it, that free-form entry needs the model server, and that the checks prove the
   formula is well formed, not that it means what you typed.

6. **Untracked screenshot scratch.** `.gitignore`. The Playwright plugin writes its
   snapshots and screenshots into `.playwright-mcp/` in the repo. Added to `.gitignore`.
   The eight shots worth keeping were copied to `notes/shots/polish-*.png`.

7. **AI trailer on a pushed commit.** `9eb8d83`, body line `Claude-Session: https://claude.ai/code/session_013FjACuFq1n3w8nqPqTxZhk`.
   Not fixed: it needs a history rewrite of the last three commits on a pushed branch.
   The owner's call. If yes:

   ```
   git rebase -i HEAD~3          # mark 9eb8d83 as reword, delete the trailer line
   git push --force-with-lease origin main
   ```

## Noted, not fixed

- **Nonsense in, an axiom out.** Step 9 above. The gates judge the formula and cannot
  judge the sentence, and the model, constrained to the grammar, always produces
  something. The page says this in its faint paragraph under the behaviour table. If it
  matters for the room, the cheapest honest change is in `formalize/model.py`: let the
  grammar admit a literal "cannot" alternative and have the prompt say when to use it.
  That is a change to the pipeline, not polish, so it is left.
- **`notes/BUILD-WEB.md` step 3** describes the tie-broken disagreement (v1 `B > A > C`,
  v2 `A > B > C`, "plurality and Borda elect A"). That is what L2 saw with the code as it
  was. The build note is a record of that drive and is left as written; this note is the
  current behaviour.
- **The 8B's hit rate.** Two of four fresh sentences right, on top of L2's own sample.
  Not a bug; the demo script should lean on the placeholder and on the edit-and-recheck
  path, which is the part that shows the checker deciding.
