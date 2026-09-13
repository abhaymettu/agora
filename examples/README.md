# Worked examples

Five runs against the derivation core, output included verbatim.
Regenerate all of them with:

```
PYTHONPATH=. python examples/generate.py
```

| example | what came back | time |
|---|---|---|
| [Arrow's theorem, derived](01-arrow.md) | impossible; core pareto, iia, nondictatorial | 0.10s |
| [Drop unanimity and the impossibility goes away](02-wilson.md) | inverse dictatorship of voter 1 | 0.08s |
| [Strategyproofness forces a dictator](03-gibbard-satterthwaite.md) | dictatorship of voter 1 | 0.06s |
| [Copeland, minted from three properties](04-copeland.md) | copeland with alphabetical tie-breaking | 0.09s |
| [Anonymity and neutrality collide at three voters](05-anonymous-neutral.md) | impossible; core anonymous, neutral | 0.15s |

Every one of these is a statement about the electorate it names. Small
electorates are where the classical theorems bite and where exhaustive search
finishes; carrying a result up to every electorate is a separate argument the
core does not make.
