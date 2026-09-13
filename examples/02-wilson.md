# Drop unanimity and the impossibility goes away

Arrow without Pareto, with surjectivity in its place. This is satisfiable, and the
rule it returns is the reason Pareto is not decoration: society ranks candidates in
the exact reverse of voter 1's ballot. Unanimous for A over B, and A comes last.

## The question

```
python -m core derive --mode swf --voters 2 --candidates 3 iia surjective nondictatorial
```

## What comes back

```
A social welfare function over 2 voters and 3 candidates satisfying all of
these exists (a rule that produces a ranking):

  iia             how society ranks a against b depends only on how the voters
                  rank a against b
  surjective      every outcome is reachable: nothing is ruled out before the
                  vote
  nondictatorial  no one voter's ballot is always the outcome, whatever anyone
                  else says

One such rule: inverse dictatorship of voter 1.

  v1: A > B > C | v2: A > B > C  ->  C > B > A
  v1: A > B > C | v2: A > C > B  ->  C > B > A
  v1: A > B > C | v2: B > A > C  ->  C > B > A
  v1: A > B > C | v2: B > C > A  ->  C > B > A
  v1: A > B > C | v2: C > A > B  ->  C > B > A
  v1: A > B > C | v2: C > B > A  ->  C > B > A
  v1: A > C > B | v2: A > B > C  ->  B > C > A
  v1: A > C > B | v2: A > C > B  ->  B > C > A
  ... 28 more profiles, all of them decided

Found by searching all 36 profiles of this electorate, 216 variables, in
0.08s. Every rule above was re-checked against its axioms without the solver.
This is a statement about 2 voters and 3 candidates: a base-case lemma, not a
result for every electorate.
```

## Running the rule

The rule comes back as an object, so the claim is checkable by running it on profiles of your choosing.

```python
>>> rule.show_outcome('A>B>C | C>B>A')
'C > B > A'
>>> rule.show_outcome('A>B>C | A>B>C')
'C > B > A'
>>> rule.show_outcome('B>A>C | C>A>B')
'C > A > B'
```

Re-checked against each axiom without going back through the solver:

```python
>>> rule.satisfies(library()['iia'])
True
>>> rule.satisfies(library()['surjective'])
True
>>> rule.satisfies(library()['nondictatorial'])
True
>>> rule.satisfies(library()['pareto'])
False
```

`rule.matches()` returns `['inverse dictatorship of voter 1']`.

## Notes

Wilson's theorem, in object form. Leave Pareto out of the axiom library and the
flagship result comes out wrong, because the inverse dictator satisfies everything
that is left.

Search space 36 profiles, 216 variables, solved in 0.08s.
