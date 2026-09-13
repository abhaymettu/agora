# Strategyproofness forces a dictator

Elect a single winner. Ask that no voter ever gains by lying about their ranking, and
that every candidate can win under some profile. Both are satisfiable, and what comes
back is a dictatorship.

## The question

```
python -m core derive --mode scf --voters 2 --candidates 3 strategyproof surjective
```

## What comes back

```
A social choice function over 2 voters and 3 candidates satisfying all of
these exists (a rule that elects one winner):

  strategyproof  no voter ever does better by submitting a ballot other than
                 their true one
  surjective     every outcome is reachable: nothing is ruled out before the
                 vote

One such rule: dictatorship of voter 1.

  v1: A > B > C | v2: A > B > C  ->  A
  v1: A > B > C | v2: A > C > B  ->  A
  v1: A > B > C | v2: B > A > C  ->  A
  v1: A > B > C | v2: B > C > A  ->  A
  v1: A > B > C | v2: C > A > B  ->  A
  v1: A > B > C | v2: C > B > A  ->  A
  v1: A > C > B | v2: A > B > C  ->  A
  v1: A > C > B | v2: A > C > B  ->  A
  ... 28 more profiles, all of them decided

Found by searching all 36 profiles of this electorate, 108 variables, in
0.06s. Every rule above was re-checked against its axioms without the solver.
This is a statement about 2 voters and 3 candidates: a base-case lemma, not a
result for every electorate.
```

## Running the rule

The rule comes back as an object, so the claim is checkable by running it on profiles of your choosing.

```python
>>> rule.show_outcome('A>B>C | C>B>A')
'A'
>>> rule.show_outcome('C>B>A | A>B>C')
'C'
>>> rule.show_outcome('B>C>A | A>B>C')
'B'
```

Re-checked against each axiom without going back through the solver:

```python
>>> rule.satisfies(library()['strategyproof'])
True
>>> rule.satisfies(library()['surjective'])
True
>>> rule.satisfies(library()['nondictatorial'])
False
```

`rule.matches()` returns `['dictatorship of voter 1']`.

## Notes

Adding `nondictatorial` to this set turns it unsatisfiable, which is
Gibbard-Satterthwaite. The satisfiable half is the more useful one to look at: it
hands you the rule, so you can check the claim by running it.

Search space 36 profiles, 108 variables, solved in 0.06s.
