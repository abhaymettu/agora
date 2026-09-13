"""The local model that drafts a formalisation. Nothing here is trusted.

Two backends, both on this machine, no network and no paid API:

    llama.cpp   `llama-server` over the GGUF ollama already pulled. Preferred,
                because it constrains generation to a GBNF, and the DSL is a
                grammar, so an unparseable formula becomes impossible rather than
                unlikely.
    ollama      the same weights behind ollama's own server, constrained to a JSON
                schema. Weaker: the shape of the JSON is guaranteed, the contents
                of the formula string are not. Used only when llama-server is down.

Either way the output is a proposal. What makes it an axiom is the gates in
`formalize/__init__.py`, which do not involve the model.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from core import library

from .grammar import ATOMS, ENGLISH_SORT, FACTS, TERMS, gbnf

LLAMA_URL = os.environ.get("AGORA_LLAMA_URL", "http://127.0.0.1:8081")
OLLAMA_URL = os.environ.get("AGORA_OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.environ.get("AGORA_OLLAMA_MODEL", "llama3.1:8b")

# Which library axioms to show as worked examples, per rule kind. Chosen so that
# every shape the language has is on screen at least once: a ground-fact guard, a
# substituted ballot, a lifted candidate, a relabelling, and a nested quantifier.
EXAMPLES = {
    "scf": ("pareto", "strategyproof", "monotone", "anonymous", "nondictatorial"),
    "swf": ("pareto", "iia", "neutral", "monotone", "surjective"),
}

SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "english": {"type": "string"},
        "formula": {"type": "string"},
    },
    "required": ["name", "english", "formula"],
}


class ModelUnavailable(Exception):
    """Neither local backend answered."""


def reference(mode: str) -> str:
    """The language, written out from the same tables the checker uses."""
    lines = ["Sorts you can quantify over:"]
    lines += [f"  {s:8} {g}" for s, g in ENGLISH_SORT.items()]
    lines.append("")
    lines.append("Statements about the rule (this is the unknown you are constraining):")
    for head, (m, sorts) in ATOMS.items():
        if m == mode:
            lines.append(f"  {head}({', '.join(sorts)})")
    lines.append("")
    lines.append("Facts about the ballots, true or false before any rule is chosen:")
    for head, sorts in FACTS.items():
        sig = "anything, anything of the same sort" if sorts == ("*", "*") else ", ".join(sorts)
        lines.append(f"  {head}({sig})")
    lines.append("")
    lines.append("Ways to build a new profile or pick a candidate out of one:")
    for head, (sorts, result) in TERMS.items():
        lines.append(f"  {head}({', '.join(sorts)}) gives a {result}")
    lines.append("  s(a) where s:cperm relabels candidate a; t(i) where t:vperm moves voter i")
    return "\n".join(lines)


def prompt(mode: str) -> list:
    """System message plus worked examples, as chat turns."""
    kind = "elects exactly one winner" if mode == "scf" else "produces a strict ranking of all candidates"
    system = (
        "You translate a fairness property of a voting rule into a small formal "
        f"language. The rule under discussion {kind}.\n\n"
        f"{reference(mode)}\n\n"
        "Connectives: not, and, or, ->, <->. Quantifiers: forall, exists. Every name "
        "must be introduced by a quantifier before it is used, and no name may be "
        "reused by an inner quantifier. Distinct candidates are not implied: say "
        "neq(a,b) when you mean two different ones.\n\n"
        'Answer with one JSON object: "name" a short lowercase identifier, "english" '
        'one sentence restating what you formalised, "formula" the formal statement. '
        "Nothing else."
    )
    turns = [{"role": "system", "content": system}]
    lib = library()
    for name in EXAMPLES[mode]:
        ax = lib[name]
        turns.append({"role": "user", "content": ax.english})
        turns.append(
            {
                "role": "assistant",
                "content": json.dumps(
                    {"name": name, "english": ax.english, "formula": _flatten(ax, mode)}
                ),
            }
        )
    return turns


def _flatten(axiom, mode: str) -> str:
    """The axiom's own source line for this mode, as one line."""
    from core.solve import AXIOM_FILE

    want, inside, buf = f"{mode} ", False, ""
    for raw in AXIOM_FILE.read_text().splitlines():
        line = buf + raw.split("#", 1)[0].strip()
        buf = ""
        if line.endswith("\\"):          # the file wraps long formulas
            buf = line[:-1].strip() + " "
            continue
        if line.startswith("axiom "):
            inside = line[6:].strip() == axiom.name
        elif inside and line.startswith(want):
            return line[len(want) :].strip()
    raise KeyError(f"{axiom.name} has no {mode} line")


def propose(text: str, mode: str, timeout: float = 90.0, repair: list | None = None,
            temperature: float = 0.0) -> dict:
    """Draft a formalisation. Raises ModelUnavailable if no local backend answers.

    `repair` carries earlier rejected attempts as (formula, reason) pairs. They go
    back to the model as its own turns followed by the checker's complaint, so the
    second attempt is answering a specific objection rather than guessing again.

    The first draft is greedy so the same question gives the same answer. Repairs
    are not: at temperature zero a model told it is wrong will happily write the
    same thing again, and the caller raises the temperature to break that.
    """
    turns = prompt(mode) + [{"role": "user", "content": text.strip()}]
    tried = []
    for formula, reason in repair or []:
        tried.append(f"  {formula}\n    rejected: {reason}")
    if tried:
        turns[-1]["content"] += (
            "\n\nThese attempts were rejected by the checker, so do not repeat them:\n"
            + "\n".join(tried)
            + "\n\nWrite a different formalisation of the same property that fixes the "
            "objection above."
        )
    errors = []
    for backend, call in (("llama.cpp", _llama), ("ollama", _ollama)):
        try:
            out = call(turns, mode, timeout, temperature)
        except Exception as exc:  # a backend that is not up, or answered badly
            errors.append(f"{backend}: {exc}")
            continue
        out["backend"] = backend
        return out
    raise ModelUnavailable("; ".join(errors))


def _llama(turns: list, mode: str, timeout: float, temperature: float = 0.0) -> dict:
    body = {
        "messages": turns,
        "grammar": gbnf(mode),
        "temperature": temperature,
        "n_predict": 320,
        "cache_prompt": True,
        "top_k": 0,
        "min_p": 0.0,
        "top_p": 1.0,
        "seed": int(temperature * 100),
    }
    reply = _post(f"{LLAMA_URL}/v1/chat/completions", body, timeout)
    return _fields(reply["choices"][0]["message"]["content"])


def _ollama(turns: list, mode: str, timeout: float, temperature: float = 0.0) -> dict:
    body = {
        "model": OLLAMA_MODEL,
        "messages": turns,
        "format": SCHEMA,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": 320},
    }
    reply = _post(f"{OLLAMA_URL}/api/chat", body, timeout)
    return _fields(reply["message"]["content"])


def _post(url: str, body: dict, timeout: float) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _fields(raw: str) -> dict:
    out = json.loads(raw)
    missing = [k for k in ("name", "english", "formula") if not str(out.get(k, "")).strip()]
    if missing:
        raise ValueError(f"reply is missing {', '.join(missing)}")
    return {k: str(out[k]).strip() for k in ("name", "english", "formula")}


def health(timeout: float = 2.0) -> dict:
    """Which backend, if any, is up. Used by the page to say so plainly."""
    try:
        with urllib.request.urlopen(f"{LLAMA_URL}/health", timeout=timeout) as r:
            if json.loads(r.read()).get("status") == "ok":
                return {"backend": "llama.cpp", "grammar": True, "url": LLAMA_URL}
    except Exception:
        pass
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=timeout) as r:
            names = [m["name"] for m in json.loads(r.read()).get("models", [])]
        if OLLAMA_MODEL in names:
            return {"backend": "ollama", "grammar": False, "url": OLLAMA_URL}
        return {"backend": None, "grammar": False, "note": f"ollama is up but {OLLAMA_MODEL} is not pulled"}
    except Exception:
        pass
    return {"backend": None, "grammar": False, "note": "no local model server is running"}
