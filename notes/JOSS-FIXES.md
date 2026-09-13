# JOSS pre-submission fixes

Run 2026-09-13. Three of the four blockers in `notes/JOSS-READY.md` are cleared here
(packaging, CI, the VoteKit author list). Blockers 1 and 2 — the repo being private and
having no public development history — are the owner's calls and were not touched.

Everything below was run this session; the commands and their output are quoted as they
came back.

## 1. Packaging (blocker 3): cleared

`pyproject.toml`, new at the repo root. setuptools backend, `requires-python >= 3.11`,
one runtime dependency (`z3-solver`), the three packages declared explicitly:

```toml
[tool.setuptools]
packages = ["core", "formalize", "web"]

[tool.setuptools.package-data]
core = ["axioms.agora"]
web = ["index.html", "app.js", "style.css"]
```

The package-data lines are load-bearing, not boilerplate. `core/solve.py:30` reads the
axiom library off disk with `Path(__file__).with_name("axioms.agora")`, and
`web/server.py:27` serves the three browser assets the same way. Without those two
entries a wheel installs and then fails on the first `derive` call.

`python -m core` needed no new entry point: `core/__main__.py` already dispatches to
`core.cli.main`, and it starts working the moment the package is importable. No
`[project.scripts]` was added — nothing in the README or the examples documents a
console-script name, so there is none to keep working.

License metadata uses the PEP 639 form (`license = "MIT"`, `license-files = ["LICENSE"]`),
which is why the build requirement is `setuptools>=77`. `LICENSE` itself is untouched.

The file carries nothing beyond what a build or an install reads. Trove classifiers and a
keyword list were written and then cut: with the repo private and nothing going to PyPI,
they have no consumer. The `Homepage` URL stays because the JOSS submission form asks for
that exact string.

### Fresh-venv verification

A clean `python3 -m venv` outside the repo, nothing pre-installed:

```
$ python3 -m venv .../freshvenv && .../freshvenv/bin/pip install .
Building wheel for agora (pyproject.toml): finished with status 'done'
Created wheel for agora: filename=agora-0.1.0-py3-none-any.whl size=52771
  sha256=3d06ef82379ed0589d23addc270829ad35860bca0beeb2909576f3123564ec99
Successfully installed agora-0.1.0 z3-solver-5.1.0.0
```

Then, run from a scratch directory **outside the repo** so the installed package is what
answers and not the working tree:

```
$ cd /tmp/.../outside
$ .../freshvenv/bin/python -m core derive --mode swf pareto iia nondictatorial

No social welfare function over 2 voters and 3 candidates satisfies all of
these at once (a rule that produces a ranking):

  pareto          if every voter ranks a above b, then so does society
  iia             how society ranks a against b depends only on how the voters
                  rank a against b
  nondictatorial  no one voter's ballot is always the outcome, whatever anyone
                  else says

Those three are jointly unsatisfiable and none of them is spare. Give up any
one and a rule appears:

  without pareto           the constant rule that always returns C > A > B
  without iia              no textbook match: 6 distinct outcomes over 36 profiles
  without nondictatorial   dictatorship of voter 2

Established by searching all 36 profiles of this electorate, 216 variables, in
0.17s. Every rule above was re-checked against its axioms without the solver.
This is a statement about 2 voters and 3 candidates: a base-case lemma, not a
result for every electorate.
```

That is the README block character for character, the elapsed time aside (0.17s here
against the README's 0.11s; same machine, different load).

One example from `examples/` was run the same way — `examples/04-copeland.md`, the
constructive branch rather than the impossibility branch:

```
$ .../freshvenv/bin/python -m core derive --mode scf --voters 3 --candidates 3 \
      condorcet monotone nondictatorial
...
One such rule: copeland with alphabetical tie-breaking.
...
Found by searching all 216 profiles of this electorate, 648 variables, in
0.10s.
```

Diffed programmatically against the output block committed in
`examples/04-copeland.md`, normalising only the elapsed-time line:

```
MATCH (modulo elapsed time): True
```

Package data confirmed present in the installed copy, again from outside the repo:

```
$ .../freshvenv/bin/python -c "import core, core.solve, web.server, formalize; ..."
core 0.1.0 True 15
web assets ['app.js', 'index.html', 'style.css']
formalize ok formalize
```

`True` is `AXIOM_FILE.exists()` against the installed path, and 15 is the axiom count the
README documents.

### The clone path still works

Unchanged and re-checked from the repo root with the repo's own venv:

```
$ .venv/bin/python -m core derive --mode swf pareto iia nondictatorial
...
Established by searching all 36 profiles of this electorate, 216 variables, in
0.11s.
```

`pip install .` builds local directories in place, so it leaves `agora.egg-info/` and
`build/` in the tree. `.gitignore` gained exactly those two — observed after a real
install, not guessed; `dist/` was tried and dropped because nothing in this repo's
workflow produces it. `git status --porcelain` after the install shows only the intended
changes.

## 2. CI (blocker 4): cleared

`.github/workflows/tests.yml`, 17 lines, no options nobody set:

```yaml
name: tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.14"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install .
      - run: python -m unittest discover -s tests -t .
```

Two versions rather than one: 3.14 is what `.venv` runs (`Python 3.14.7`), and 3.11 is
the floor `pyproject.toml` declares. Declaring a floor and never testing it is how a
floor rots.

Both matrix entries were run locally before the workflow was written, so this is not a
guess about what GitHub will do. 3.11 came from `uv python install 3.11` into a separate
venv, installed with the same `pip install .`:

```
$ .../v311/bin/python -V
Python 3.11.15
$ .../v311/bin/python -m unittest discover -s tests -t .
Ran 85 tests in 53.829s

OK
```

**No timeout tweaks are needed.** The suite is ~62s at its slowest measurement
(58.7s on 3.14, 53.8s on 3.11 this session; `notes/JOSS-READY.md` recorded 62.2s
earlier). The GitHub Actions default job timeout is 360 minutes, so the run has roughly
three orders of magnitude of headroom and neither `timeout-minutes` nor any per-step
timeout was set. No `pip` cache either — the only dependency is one 39 MB z3 wheel, and
caching it would buy seconds against a minute-long job.

Not verified: that the workflow actually runs green on GitHub. It cannot be, while the
repo is private and unpushed. What is verified is that the exact two commands in it
succeed on both interpreter versions on this machine.

## 3. Bibliography: VoteKit author list filled

`paper/paper.bib`, the `donnay2025` entry. Was `{Donnay, Christopher and others}`.

Source fetched this session:

```
$ curl -sL "https://doi.org/10.21105/joss.07477" -w "%{http_code} %{url_effective}\n"
200 https://joss.theoj.org/papers/10.21105/joss.07477
```

Authors taken from the `citation_author` meta tags on that page, in page order:

```
citation_author" content="Christopher Donnay"
citation_author" content="Moon Duchin"
citation_author" content="Jack Gibson"
citation_author" content="Zach Glaser"
citation_author" content="Andrew Hong"
citation_author" content="Malavika Mukundan"
citation_author" content="Jennifer Wang"
```

Now:

```bibtex
@article{donnay2025,
  author  = {Donnay, Christopher and Duchin, Moon and Gibson, Jack and
             Glaser, Zach and Hong, Andrew and Mukundan, Malavika and
             Wang, Jennifer},
  title   = {VoteKit: A {P}ython package for computational social choice research},
  journal = {Journal of Open Source Software},
  volume  = {10},
  number  = {109},
  pages   = {7477},
  year    = {2025},
  doi     = {10.21105/joss.07477}
}
```

Style matches the file's other entries: `Last, First` throughout, ` and ` between
authors, continuation lines aligned under the opening brace the way `satterthwaite1975`
already wraps its title. Only the author field changed; volume, number, pages, year and
DOI were already correct against the same page.

This clears the last of the two smaller items `notes/JOSS-READY.md` flagged before the
form gets filled in. The other one, the ORCID, is the owner's to register.

## 4. Tests: 85 pass, 0 fail

Full suite from the repo venv, as asked:

```
$ .venv/bin/python -m unittest discover -s tests -t .
Ran 85 tests in 58.707s

OK

.venv/bin/python -m unittest discover -s tests -t .  47.91s user 0.22s system 81% cpu 58.821 total
```

85 run, 85 passed, 0 failed, 0 errored, 0 skipped. Wall time 58.8s. Nothing failed, so
nothing was worked around and no test was touched.

The run prints `POST /api/derive` and `GET /api/axioms` lines and one
`ResourceWarning: Implicitly cleaning up <HTTPError 400: 'Bad Request'>` from
`test_web.py`. Both are the web tests exercising the server's own logging and its
deliberate 400 path; neither is a failure and neither was introduced here.

Second run under 3.11 in the fresh-install venv, quoted in the CI section above: also
`Ran 85 tests in 53.829s / OK`.

## 5. Disclosure section (verbatim)

Copied unedited from `paper/paper.md` lines 140-146. `paper/paper.md` was not modified by
this lane.

> # AI usage disclosure
>
> The implementation, tests and documentation in this repository were written with the
> assistance of a generative AI coding agent, directed and reviewed by the author. The
> independent second implementation in `tests/l3_reference.py` and the solver-free
> re-verification of every returned rule were built as checks on that process;
> `notes/VERIFY-CORE.md` records what they cover and where that coverage stops.

## 6. State check

Before the commit for this pass:

```
$ git status -sb
## main...origin/main [ahead 6]
 M .gitignore
 M paper/paper.bib
?? .github/
?? pyproject.toml
```

```
$ git log --oneline origin/main..HEAD
b087b5e joss readiness: checklist with receipts, blockers, submission metadata
4a8da4c joss paper: summary, statement of need, the axiom library, bibliography
04eee0d add mit license and contributing guidelines
48a3776 discovery sweep: the map, the two unplaced results, the verdict
253baff sweep harness: minimal inconsistent subsets, model counts, implication order
9d90f7e six more axioms: unanimity, majority, condorcet loser, tops-only, maskin monotonicity, reversal
```

After this pass's commit — `packaging, ci and the votekit author list`, five files:
`pyproject.toml`, `.github/workflows/tests.yml`, `.gitignore`, `paper/paper.bib` and this
one. `paper/paper.md` is not among them:

```
$ git status -sb
## main...origin/main [ahead 7]
```

Working tree clean. Six commits were already unpushed when this lane started, so the push
set is seven. Nothing was pushed, no remote was contacted except the two
read-only fetches noted above (the JOSS paper page, and PyPI for the `z3-solver` and
`setuptools` wheels). The repo is still private.

## What is still blocking submission

Untouched, both owner decisions, both from `notes/JOSS-READY.md`:

1. **The repo is private.** JOSS needs the source, the issue tracker and issue creation
   all readable without registration.
2. **No public development history.** The checklist asks for months of it; this repo has
   one day of commits and zero days public. `JOSS-READY.md` lays out the three ways out
   (wait six months, submit to JORS or SoftwareX instead, or submit and expect a
   pre-review rejection on that item).

Plus the ORCID, which is a form field rather than a blocker.
