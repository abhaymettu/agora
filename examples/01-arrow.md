# Arrow's theorem, derived

The most famous impossibility in the subject. Ask for a rule that produces a full
social ranking, respects unanimity, decides each pair using only how the voters rank
that pair, and is not one voter's ballot copied out. No such rule exists.

## The question

```
python -m core derive --mode swf --voters 2 --candidates 3 pareto iia nondictatorial
```

## What comes back

```
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
0.10s. Every rule above was re-checked against its axioms without the solver.
This is a statement about 2 voters and 3 candidates: a base-case lemma, not a
result for every electorate.
```

## The core

Asked for 3, blamed 3: `pareto, iia, nondictatorial`. Minimality was verified.

Each proper subset comes with a rule that satisfies it:

- without `pareto`: the constant rule that always returns C > A > B
- without `iia`: no textbook match: 6 distinct outcomes over 36 profiles
- without `nondictatorial`: dictatorship of voter 2

## Notes

The three axioms are jointly unsatisfiable and the core is all three of them: drop any
one and a rule appears. The witnesses are the evidence for that. `without
nondictatorial` returning a dictatorship is the theorem's punchline stated as an
object rather than as a sentence.

Search space 36 profiles, 216 variables, solved in 0.10s.
