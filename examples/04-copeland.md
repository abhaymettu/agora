# Copeland, minted from three properties

Not every axiom set ends in an impossibility or a dictator. Ask for a winner-elects
rule that honours a Condorcet winner when there is one, never punishes a candidate for
being raised, and is not a dictatorship. The search returns a rule the literature
already has a name for.

## The question

```
python -m core derive --mode scf --voters 3 --candidates 3 condorcet monotone nondictatorial
```

## What comes back

```
A social choice function over 3 voters and 3 candidates satisfying all of
these exists (a rule that elects one winner):

  condorcet       a candidate who beats every other head to head comes first
  monotone        raising a candidate on one ballot never costs that candidate
                  ground
  nondictatorial  no one voter's ballot is always the outcome, whatever anyone
                  else says

One such rule: copeland with alphabetical tie-breaking.

  v1: A > B > C | v2: A > B > C | v3: A > B > C  ->  A
  v1: A > B > C | v2: A > B > C | v3: A > C > B  ->  A
  v1: A > B > C | v2: A > B > C | v3: B > A > C  ->  A
  v1: A > B > C | v2: A > B > C | v3: B > C > A  ->  A
  v1: A > B > C | v2: A > B > C | v3: C > A > B  ->  A
  v1: A > B > C | v2: A > B > C | v3: C > B > A  ->  A
  v1: A > B > C | v2: A > C > B | v3: A > B > C  ->  A
  v1: A > B > C | v2: A > C > B | v3: A > C > B  ->  A
  ... 208 more profiles, all of them decided

Found by searching all 216 profiles of this electorate, 648 variables, in
0.09s. Every rule above was re-checked against its axioms without the solver.
This is a statement about 3 voters and 3 candidates: a base-case lemma, not a
result for every electorate.
```

## Running the rule

The rule comes back as an object, so the claim is checkable by running it on profiles of your choosing.

```python
>>> rule.show_outcome('A>B>C | B>C>A | C>A>B')
'A'
>>> rule.show_outcome('A>B>C | A>C>B | B>A>C')
'A'
>>> rule.show_outcome('C>B>A | C>A>B | A>B>C')
'C'
```

Re-checked against each axiom without going back through the solver:

```python
>>> rule.satisfies(library()['condorcet'])
True
>>> rule.satisfies(library()['monotone'])
True
>>> rule.satisfies(library()['nondictatorial'])
True
>>> rule.satisfies(library()['strategyproof'])
False
```

`rule.matches()` returns `['copeland with alphabetical tie-breaking']`.

## Notes

The rule was recognised, not looked up: the search produced a table over all 216
profiles and the table happens to be identical to Copeland with alphabetical
tie-breaking. The first profile above is the Condorcet cycle, where no candidate beats
every other, and the rule still has to decide.

Search space 216 profiles, 648 variables, solved in 0.09s.
