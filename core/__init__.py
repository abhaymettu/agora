"""AGORA's derivation core.

Name the properties a fair voting rule should have. The core either hands you a
rule that provably has all of them, or a proof that no such rule can exist.

    from core import derive
    print(derive(["pareto", "iia", "nondictatorial"], voters=2, candidates=3, mode="swf"))

Everything here is deterministic and offline. The only dependency is z3-solver.
"""

from .domain import Electorate
from .dsl import Axiom, ParseError, parse_axioms, parse_formula
from .ground import GroundError
from .render import render
from .rules import Rule, reference_rules
from .solve import Result, axiom_names, derive, library

__all__ = [
    "derive",
    "Result",
    "Rule",
    "Electorate",
    "Axiom",
    "library",
    "axiom_names",
    "reference_rules",
    "render",
    "parse_axioms",
    "parse_formula",
    "ParseError",
    "GroundError",
]

__version__ = "0.1.0"
