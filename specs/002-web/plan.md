# 002: plan

## Shape

Three Python modules and three static files. No framework, no build step, no new
runtime dependency beyond what the core already needs.

```
formalize/grammar.py   the DSL signature, the GBNF built from it, the sort checker
formalize/model.py     llama.cpp server client, ollama fallback, the prompt
formalize/__init__.py  the gate pipeline; the only thing web/ imports
web/server.py          http.server: static files plus a few JSON endpoints
web/index.html         one page, four panels
web/app.js             state and rendering, no dependencies
web/style.css          OLED black, one viewport
```

## Why no framework

`http.server` serves files and handles POST bodies in about eighty lines. A demo that
starts with `python -m web` and needs nothing installed is worth more than one that
needs a package manager to be in a good mood at 9am.

## Why the playground runs in the browser

`Rule.as_dict()` already returns the entire outcome table keyed by a printable profile.
For the sizes in scope that is 36 to 1,296 rows, small enough to ship to the page. So
stress-testing a rule is a dictionary lookup with no round trip, and plurality, Borda
and the Condorcet winner are a few lines of JavaScript each. Nothing is recomputed on
the server and nothing can drift from what the solver returned.

## Why GBNF rather than a JSON schema

Ollama constrains output to a JSON schema; llama.cpp constrains to an arbitrary grammar.
The DSL is a grammar, so llama.cpp can make an unparseable formula structurally
impossible instead of merely unlikely. Both are on the machine and the 8B is already
pulled, so the pipeline speaks to `llama-server` over the ollama blob and falls back to
ollama's `format` if that server is not up.

## Endpoints

```
GET  /api/axioms       the library, with modes and glosses
GET  /api/health       is the model backend reachable
POST /api/derive       {axioms, mode, voters, candidates, timeout} -> result
POST /api/formalize    {text, mode} -> proposal + gate report
```

`/api/derive` accepts library names and inline custom axioms in the same list, so a
minted rule can mix the two.

## Order

1. grammar and sort checker, with the nine library axioms as the test corpus
2. gate pipeline, model backend last so the gates can be tested without it
3. server
4. page
5. drive the demo end to end, screenshot every screen
