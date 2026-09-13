# JOSS submission readiness

Checked 2026-09-13. Paper written, not submitted. **Four blockers stand between this and
a submission that would survive pre-review**, listed at the bottom with what each costs.

The verdict this follows is `notes/DISCOVERY.md`: the social choice content is not new,
the software is what is worth writing up. The paper says nothing else.

## What was added in this pass

| file | what |
|---|---|
| `LICENSE` | MIT, copyright 2026 Abhay Mettu. OSI-approved, plain text, repo root. |
| `CONTRIBUTING.md` | community guidelines: support, bug reports, adding an axiom, changing the core, pull requests. |
| `paper/paper.md` | the JOSS paper. 1,000 words of prose excluding code blocks, inside the 250-1000 JOSS asks for. |
| `paper/paper.bib` | 15 entries. Every key cited in the paper is defined, and every entry defined is cited (checked programmatically). |

## The reviewer checklist, item by item

Items are from the JOSS reviewer checklist as it stood on 2026-09-13
(<https://joss.readthedocs.io/en/latest/review_checklist.html>). The checklist has been
revised since the version most JOSS write-ups quote: it now carries a **Development
History and Open-Source Practice** block and an **AI usage disclosure** item, and both
bite here.

### General checks

| item | verdict | evidence |
|---|---|---|
| Repository: source available at the repository URL | **BLOCKED** | `gh repo view abhaymettu/agora --json isPrivate` returns `true`. Nothing is browsable. |
| License: plain-text LICENSE, OSI-approved | **pass** | `LICENSE`, MIT, 21 lines, repo root. GitHub's own `licenseInfo` is still `null` and will populate on the next push. |
| Contribution and authorship: submitting author is a major contributor | **pass** | Sole author. `git log --format='%an' \| sort -u` is one name. |
| Scope and significance: credible scholarly significance | **pass, with a caveat to argue** | The gap is real and documented in `notes/DISCOVERY.md`: a decade of one-paper-one-encoding SAT work that shipped no software, and three maintained packages that check a given rule rather than search for one. The caveat a reviewer will raise is that the tool answers base cases at two to five voters, not the general question, and the README says so up front. |

### Development history and open-source practice

| item | verdict | evidence |
|---|---|---|
| Development timeline: sustained development over months, not rapid recent generation | **BLOCKED** | All 29 commits are dated 2026-09-13, first `fff5358`, last `48a3776`. This is the single hardest item to satisfy and no amount of editing fixes it. |
| Open development: six months of public history, releases, issues, external engagement | **BLOCKED** | Zero days of public history, no releases, no tags (`git tag` is empty), no issues. |
| Collaborative effort: multiple developers, external users | **fail** | One author, no external users. JOSS accepts single-author submissions, so this is a weakness rather than a bar, but it compounds the two above. |
| Good practices: license, documentation, tests, releases, contribution pathways | **partial** | License and docs and tests: yes. Releases: none. Contribution pathway: `CONTRIBUTING.md`, new as of this pass. No CI (`.github/` does not exist), so the tests have never run anywhere but this machine. |

### Functionality

| item | verdict | evidence |
|---|---|---|
| Installation proceeds as documented | **partial** | `pip install z3-solver` then run from a clone. There is no `pyproject.toml`, `setup.py` or `requirements.txt`, so the package is not installable and not "packaged appropriately according to language standards". A reviewer will flag this. |
| Functional claims confirmed | **pass** | `python -m core derive --mode swf pareto iia nondictatorial` was run this session and returned the Arrow output the README and the paper both quote, verbatim except the elapsed time (0.13s against the README's 0.11s). |
| Performance claims confirmed | **pass, self-reported** | The README timing table is one machine, one run each, and says so. `notes/timings.txt` is the raw record. |

### Documentation

| item | verdict | evidence |
|---|---|---|
| Statement of need: problems solved, target audience | **pass** | `README.md` "Why"; `paper/paper.md` "Statement of need". |
| Installation instructions with a clear dependency list | **partial** | `README.md` "Running it" names z3-solver as the only dependency. No automated package management. Same gap as above. |
| Example usage, ideally on real problems | **pass** | `examples/` holds five worked runs with verbatim output (Arrow, Wilson, Gibbard-Satterthwaite, Copeland, anonymity-neutrality), regenerable with `PYTHONPATH=. python examples/generate.py`. |
| Functionality documentation | **pass** | `README.md` documents the full public API surface: `derive`, `Result`, `Rule`, the DSL, the axiom table, and the failure modes. |
| Automated tests | **pass** | `.venv/bin/python -m unittest discover -s tests -t .` ran this session: **85 tests, OK, 62.230s**. Spread: `test_golden.py` 24, `test_l3_reproduce.py` 21, `test_formalize.py` 20, `test_web.py` 15, `test_axioms_added.py` 5. Documented in `README.md`. Not run in CI. |
| Community guidelines for contribution, issues, support | **pass, new** | `CONTRIBUTING.md`. Did not exist before this pass. |

### Software paper

| item | verdict | evidence |
|---|---|---|
| Summary for non-specialists | **pass** | `paper/paper.md` "Summary". |
| Statement of need as a titled section | **pass** | `paper/paper.md` "Statement of need". |
| State of the field: comparison to commonly-used packages | **pass** | Same section. `pref_voting`, `abcvoting`, `VoteKit` named and distinguished; Boixel and Endriss named as the closest existing tool; the SAT line cited as `tang2009`, `geist2011`, `brandt2016`, `brandt2017`, `geist2017`. |
| Software design: trade-offs and architecture | **pass** | `paper/paper.md` "Design and the axiom library" names the trade explicitly: axioms as data costs a quadratic grounding pass, buys extensibility and a small formula. |
| Research impact: realized or credible near-term | **weak** | No users, no citations, no realized impact. The paper leans on the sweep in `notes/DISCOVERY.md` (2,746 questions, 104 minimal impossibilities, four known theorems reproduced) as evidence the tool does work nobody has to hand-encode. That is the strongest available argument and it is an argument, not a track record. |
| AI usage disclosure | **pass, needs your sign-off** | `paper/paper.md` has an "AI usage disclosure" section. It states the code, tests and docs were written with a generative AI coding agent under your direction and review, and points at `tests/l3_reference.py` and `notes/VERIFY-CORE.md` as the checks on that process. **This is a claim about your process, so read it and edit the wording before anything goes out.** Omitting it is not an option: it is a checklist item, and the development-timeline item means a reviewer will ask regardless. |
| Quality of writing | **your call** | Not self-assessable. |
| References complete and correct | **pass** | 15 entries in `paper/paper.bib`, every cited key defined and every defined key cited. Volumes, pages and DOIs for `tang2009`, `geist2011`, `brandt2016`, `holliday2025`, `lackner2023`, `donnay2025` and `geist2017` were checked against sources this session. **One entry is incomplete on purpose:** `donnay2025` (VoteKit) is `{Donnay, Christopher and others}` because the full author list was not confirmed. Fill it in from <https://doi.org/10.21105/joss.07477> before submitting. |

## Blockers, in the order they have to be cleared

1. **The repository is private.** JOSS requires the source browsable, the issue tracker
   readable, and issues openable, all without registration. Nothing else on this list
   matters until this changes, and the standing instruction on this lane is that the repo
   stays private unless you say otherwise. Your call, and it is a one-way door: making it
   public publishes 29 commits of development history dated to one day.

2. **No public development history.** The current checklist asks for "sustained
   development over months or years rather than rapid recent code generation" and "six
   months of public history, releases, issues, and external engagement". This repo has
   zero days of either. `notes/DISCOVERY.md` already called this "a calendar problem, not
   a work problem", which is true and is also exactly what a reviewer would expect a
   submitter to say. Three ways out:
   - Publish now, let it sit six months, submit in March 2027. Costs nothing but time,
     and the history accumulates only if the repo actually gets worked on.
   - Submit to JORS or SoftwareX instead, neither of which has a public-history rule.
     `notes/DISCOVERY.md` already lists these as the alternatives.
   - Submit to JOSS now and expect it to be rejected at pre-review on this item alone.

3. **Not packaged.** No `pyproject.toml`, so `pip install agora` does not exist and the
   only install path is cloning. "Packaged appropriately for the language" is an explicit
   requirement. This is the cheapest blocker to clear: one `pyproject.toml` declaring the
   `core`, `formalize` and `web` packages and the `z3-solver` dependency, plus a
   `python -m core` entry point.

4. **No CI.** The 85 tests have only ever run on this machine. A GitHub Actions workflow
   running the suite on push is roughly ten lines and turns "there are tests" into
   "the tests pass, here is the badge". Not formally required; reviewers ask for it.

Two smaller items that are not blockers but need doing before the form is filled in: the
ORCID (`paper/paper.md` has it commented out with a TODO, and JOSS strongly prefers one,
free at <https://orcid.org/register>), and the VoteKit author list in `paper.bib`.

## Submission metadata block

Fill this into <https://joss.theoj.org/papers/new> when the blockers above are cleared.
Nothing here has been submitted.

```
Title:            AGORA: deriving voting rules and impossibilities from axioms
Submitting author: Abhay Mettu
Author ORCID:     (none yet - register at https://orcid.org/register)
Affiliation:      Independent researcher

Repository URL:   https://github.com/abhaymettu/agora
                  (currently PRIVATE - must be public before submission)

Branch with paper: main
                   (paper/paper.md and paper/paper.bib are on main; JOSS also
                    accepts a short-lived branch cut from the default branch)

Software version:  v0.1.0        <- tag does not exist yet, see below
Archive DOI:       (none yet - Zenodo, see below)

Languages:         Python
Subject area:      Computational social choice / economics / computer science
```

### Cutting the version tag

JOSS wants the tag and the archive to be of the exact state under review, so this happens
after the paper is final, not before. There are no tags today (`git tag` is empty), so
`v0.1.0` is the first. Annotate the tag, push it, and cut a GitHub release from it with
`gh release create v0.1.0`.

### The Zenodo archive step

JOSS asks authors to "make a tagged release of the software, and deposit a copy of the
repository with a data-archiving service such as Zenodo or figshare, get a DOI for the
archive, and update the review issue thread with the version number and DOI".

1. Sign in to <https://zenodo.org> with the GitHub account.
2. Under Account -> GitHub, flip the switch on for `abhaymettu/agora`. The repository has
   to be public for it to appear in that list, which is blocker 1 again.
3. Cut the `v0.1.0` GitHub release above. Zenodo picks it up automatically and mints a
   DOI. Only releases created *after* the switch is flipped are archived, so the order
   matters.
4. Copy the DOI from the Zenodo record.
5. Two fields on the JOSS form take it: the version (`v0.1.0`) and the archive DOI. The
   metadata on the Zenodo record itself should be edited so the title, the author name and
   the license match `paper/paper.md` and `LICENSE`; Zenodo's defaults from GitHub are
   usually close but not exact on the title.

After submission JOSS runs the paper through its compiler and posts a PDF preview on the
review issue. That is the first point where a LaTeX or bibliography error shows up, since
the compiler has not been run against `paper/paper.md` locally. Whedon can be run before
submission if that turns out to matter.
