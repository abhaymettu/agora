"""The demo server: static files and four JSON endpoints.

`http.server` and nothing else. A demo whose first step is `pip install` is a demo
that can fail in front of someone, and everything here is either in the standard
library or already required by the core.

    python -m web            then open http://127.0.0.1:8000

The server never reasons. It parses a request, calls the core or the formalisation
gates, and returns what they said. One thing it does insist on: an axiom that
arrives inline from the browser is put through the gates again here, because the
page is not a trusted source for what counts as an axiom.
"""

from __future__ import annotations

import json
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from core import derive, library, render
from formalize import formalize, health, vet
from formalize.model import ModelUnavailable

HERE = Path(__file__).parent
PORT = int(os.environ.get("AGORA_PORT", "8000"))

# The sizes the picker offers. Anything larger is honest about not finishing, but
# there is no reason to put a control in front of someone that mostly returns
# "undecided": measured timings per size are in notes/timings.txt.
SIZES = [
    {"voters": 2, "candidates": 3, "note": "instant"},
    {"voters": 3, "candidates": 3, "note": "a few seconds"},
    {"voters": 2, "candidates": 4, "note": "up to a minute"},
    {"voters": 4, "candidates": 3, "note": "often undecided inside the budget"},
]
MAX_TIMEOUT = 120.0


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(HERE), **kw)

    def log_message(self, fmt, *args):
        if "/api/" in (self.path or ""):
            sys.stderr.write("%s %s\n" % (self.command, self.path))

    def do_GET(self):
        if self.path == "/api/axioms":
            return self.send_json(catalogue())
        if self.path == "/api/health":
            return self.send_json(health())
        return super().do_GET()

    def do_POST(self):
        routes = {"/api/derive": self.derive, "/api/formalize": self.formalize, "/api/vet": self.vet}
        run = routes.get(self.path)
        if run is None:
            return self.send_error(404)
        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length) or "{}")
        except (ValueError, TypeError):
            return self.send_json({"error": "that was not JSON"}, 400)
        try:
            self.send_json(run(body))
        except ValueError as exc:
            self.send_json({"error": str(exc)}, 400)
        except ModelUnavailable as exc:
            self.send_json(
                {
                    "error": "no local model is answering, so free-form entry is off. "
                    "Start one with the command in notes/BUILD-WEB.md, or pick from the "
                    "library instead.",
                    "detail": str(exc),
                },
                503,
            )

    # -- the endpoints ------------------------------------------------------

    def derive(self, body: dict) -> dict:
        mode = _mode(body)
        voters, candidates = _size(body)
        picked, glosses = [], {}
        for item in body.get("axioms") or []:
            axiom, english = _axiom(item, mode)
            picked.append(axiom)
            glosses[axiom if isinstance(axiom, str) else axiom.name] = english
        if not picked:
            raise ValueError("pick at least one axiom")

        timeout = min(float(body.get("timeout") or 60.0), MAX_TIMEOUT)
        result = derive(picked, voters, candidates, mode=mode, timeout=timeout)
        out = result.as_dict()
        out["text"] = render(result)
        out["glosses"] = glosses
        if result.rule is not None:
            out["rule_name"] = result.rule.describe()
            out["rule_named"] = bool(result.rule.matches())
        return out

    def formalize(self, body: dict) -> dict:
        text = (body.get("text") or "").strip()
        if not text:
            raise ValueError("type a property first")
        if len(text) > 400:
            raise ValueError("keep it to a sentence or two")
        return formalize(text, _mode(body)).as_dict()

    def vet(self, body: dict) -> dict:
        formula = (body.get("formula") or "").strip()
        if not formula:
            raise ValueError("there is no formula to check")
        return vet(formula, _mode(body), name=body.get("name") or "custom",
                   english=body.get("english") or "", backend="edited by hand").as_dict()

    # -- plumbing -----------------------------------------------------------

    def end_headers(self) -> None:
        # Static files carry Last-Modified and nothing else, so a browser would
        # keep serving yesterday's app.js. Everything revalidates, every time.
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def send_json(self, payload: dict, status: int = 200) -> None:
        raw = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def _mode(body: dict) -> str:
    mode = body.get("mode") or "scf"
    if mode not in ("scf", "swf"):
        raise ValueError(f"unknown rule kind {mode!r}")
    return mode


def _size(body: dict) -> tuple:
    voters, candidates = int(body.get("voters") or 2), int(body.get("candidates") or 3)
    if not any(s["voters"] == voters and s["candidates"] == candidates for s in SIZES):
        raise ValueError(f"{voters} voters and {candidates} candidates is not one of the sizes offered")
    return voters, candidates


def _axiom(item, mode: str):
    """A library name stays a name. Anything inline is put back through the gates."""
    if isinstance(item, str):
        if item not in library():
            raise ValueError(f"no axiom named {item!r}")
        ax = library()[item]
        if not ax.supports(mode):
            raise ValueError(f"{item} is not defined for this kind of rule")
        return item, ax.english
    formula = (item or {}).get("formula", "")
    checked = vet(formula, mode, name=item.get("name") or "custom",
                  english=item.get("english") or "")
    if not checked.accepted:
        raise ValueError(f"{checked.name} did not pass the {checked.failed} gate: {checked.why}")
    return checked.axiom, checked.english or checked.name


def catalogue() -> dict:
    return {
        "axioms": [
            {"name": n, "modes": list(a.modes), "english": a.english}
            for n, a in library().items()
        ],
        "sizes": SIZES,
    }


def serve(port: int = PORT) -> None:
    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    except OSError as exc:
        raise SystemExit(
            f"port {port} is already taken ({exc.strerror.lower()}). Either stop what is on it "
            f"or run with AGORA_PORT=8001."
        ) from None
    print(f"agora on http://127.0.0.1:{port}   (ctrl-c to stop)", flush=True)
    backend = health()
    print(
        f"model backend: {backend['backend']} "
        f"({'grammar-constrained' if backend.get('grammar') else 'json-schema only'})"
        if backend.get("backend")
        else f"model backend: none. {backend.get('note', '')} Free-form entry will say so.",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
