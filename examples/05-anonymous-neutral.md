# Anonymity and neutrality collide at three voters

Three properties that each sound like a minimum: honour the Condorcet winner, ignore
who cast which ballot, and treat the candidates alike. There is no such rule, and the
reason is smaller than the question asked.

## The question

```
python -m core derive --mode scf --voters 3 --candidates 3 condorcet anonymous neutral
```

## What comes back

```
No social choice function over 3 voters and 3 candidates satisfies all of
these at once (a rule that elects one winner):

  anonymous  the outcome depends on which ballots were cast, not on who cast
             them
  neutral    relabelling the candidates relabels the outcome and changes
             nothing else

You asked for 3. The two above are enough to rule it out on their own, so
condorcet never came into it.

Those two are jointly unsatisfiable and none of them is spare. Give up any one
and a rule appears:

  without anonymous   no textbook match: 3 distinct outcomes over 216 profiles
  without neutral     no textbook match: 3 distinct outcomes over 216 profiles

Established by searching all 216 profiles of this electorate, 648 variables,
in 0.15s. Every rule above was re-checked against its axioms without the
solver. This is a statement about 3 voters and 3 candidates: a base-case
lemma, not a result for every electorate.
```

## The core

Asked for 3, blamed 2: `anonymous, neutral`. Minimality was verified.

Each proper subset comes with a rule that satisfies it:

- without `anonymous`: no textbook match: 3 distinct outcomes over 216 profiles
- without `neutral`: no textbook match: 3 distinct outcomes over 216 profiles

## Notes

Two of the three are enough. Condorcet never came into it, and the core says so, which
is the difference between "these three are impossible" and knowing which of them to
argue about. A resolute rule has to break the symmetric cycle somehow, and anonymity
plus neutrality leave it nowhere to break it.

Search space 216 profiles, 648 variables, solved in 0.15s.
