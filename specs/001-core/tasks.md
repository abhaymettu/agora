# Tasks 001: derivation core

- [ ] T1 `domain.py`: Electorate, ballots, profiles, candidate and voter
      permutations, `sub`, `lift`, `permc`, `permv`, and the ground predicates
      `pref`, `unanimous`, `condorcet`, `samepair`, `top`, `neq`.
- [ ] T2 `dsl.py`: tokeniser, AST nodes, parser. Parses the axiom file into
      per-axiom, per-mode formulas with English glosses.
- [ ] T3 `axioms.agora`: nine axioms written in the DSL.
- [ ] T4 `ground.py`: expand an AST over an Electorate into Z3.
- [ ] T5 `solve.py`: frame constraints, selectors, check, greedy minimal core,
      per-axiom witnesses, timeout degradation.
- [ ] T6 `rules.py`: Rule object with `winner`/`ranking`/`table`, and a recogniser
      for dictatorship, constant, plurality, borda, copeland.
- [ ] T7 `render.py`: English for sat, unsat, and unknown.
- [ ] T8 `tests/test_golden.py`: Arrow, GS, drop-an-axiom, frame sanity.
- [ ] T9 `cli.py` and `README.md`.
- [ ] T10 timing sweep across electorate sizes; `notes/BUILD-CORE.md`.
