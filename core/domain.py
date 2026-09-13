"""Finite electorates.

Everything the axioms quantify over lives here: ballots, profiles, the two kinds
of relabelling, and the ground facts (who prefers what, who beats whom) that are
decided by arithmetic rather than by the solver. No Z3 in this file.

Candidates and voters are integers. A ballot is a tuple of candidates, best
first. A profile is a tuple of ballots, one per voter.
"""

from __future__ import annotations

from functools import cached_property
from itertools import permutations, product

Ballot = tuple[int, ...]
Profile = tuple[Ballot, ...]

CAND_NAMES = "ABCDEFGH"


class Electorate:
    """A fixed number of voters ranking a fixed number of candidates."""

    def __init__(self, voters: int, candidates: int) -> None:
        if voters < 1:
            raise ValueError("need at least one voter")
        if candidates < 2:
            raise ValueError("need at least two candidates")
        self.voters = voters
        self.candidates = candidates
        self.cands: tuple[int, ...] = tuple(range(candidates))
        self.vs: tuple[int, ...] = tuple(range(voters))
        self.ballots: tuple[Ballot, ...] = tuple(permutations(self.cands))
        self.profiles: tuple[Profile, ...] = tuple(
            product(self.ballots, repeat=voters)
        )
        self.cperms: tuple[tuple[int, ...], ...] = self.ballots
        self.vperms: tuple[tuple[int, ...], ...] = tuple(permutations(self.vs))
        self._rank = {b: _positions(b) for b in self.ballots}
        self._full = (1 << voters) - 1

    def __repr__(self) -> str:
        return f"Electorate(voters={self.voters}, candidates={self.candidates})"

    def name(self, c: int) -> str:
        return CAND_NAMES[c]

    def show_ballot(self, b: Ballot) -> str:
        return " > ".join(CAND_NAMES[c] for c in b)

    def show_profile(self, p: Profile) -> str:
        return " | ".join(
            f"v{i + 1}: {self.show_ballot(b)}" for i, b in enumerate(p)
        )

    def parse_ballot(self, text: str | Ballot) -> Ballot:
        """Accept 'A > B > C', 'ABC', or an already-built tuple."""
        if isinstance(text, tuple):
            b = text
        else:
            toks = [t for t in text.replace(">", " ").split() if t]
            if len(toks) == 1 and len(toks[0]) > 1:
                toks = list(toks[0])
            b = tuple(CAND_NAMES.index(t.strip().upper()) for t in toks)
        if sorted(b) != list(self.cands):
            raise ValueError(f"{text!r} is not a ranking of {self.candidates} candidates")
        return b

    def parse_profile(self, rows: str | list) -> Profile:
        """Accept a list of ballots, or one string with ballots separated by '|'."""
        if isinstance(rows, str):
            rows = rows.split("|")
        p = tuple(self.parse_ballot(r) for r in rows)
        if len(p) != self.voters:
            raise ValueError(f"expected {self.voters} ballots, got {len(p)}")
        return p

    # -- profile transformations, the terms the DSL can build --------------

    def sub(self, p: Profile, i: int, r: Ballot) -> Profile:
        """p with voter i's ballot replaced by r."""
        return p[:i] + (r,) + p[i + 1 :]

    def lift(self, p: Profile, i: int, c: int) -> Profile:
        """p with candidate c raised one place in voter i's ballot."""
        b = p[i]
        k = self._rank[b][c]
        if k == 0:
            return p
        lifted = b[: k - 1] + (c, b[k - 1]) + b[k + 1 :]
        return self.sub(p, i, lifted)

    def permc(self, p: Profile, s: tuple[int, ...]) -> Profile:
        """Relabel every candidate by s: candidate c becomes candidate s[c]."""
        return tuple(tuple(s[c] for c in b) for b in p)

    def permv(self, p: Profile, t: tuple[int, ...]) -> Profile:
        """Reassign ballots between voters by t: voter i now holds p[t[i]]."""
        return tuple(p[t[i]] for i in self.vs)

    def rev(self, p: Profile) -> Profile:
        """p with every ballot turned upside down."""
        return tuple(tuple(reversed(b)) for b in p)

    def top(self, p: Profile, i: int) -> int:
        return p[i][0]

    # -- ground facts -------------------------------------------------------

    @cached_property
    def _mask(self) -> dict[Profile, tuple[tuple[int, ...], ...]]:
        """_mask[p][a][b] is the bitmask of voters who rank a above b in p."""
        m, table = self.candidates, {}
        for p in self.profiles:
            ranks = [self._rank[b] for b in p]
            rows = []
            for a in range(m):
                row = []
                for b in range(m):
                    bits = 0
                    for i, rk in enumerate(ranks):
                        if rk[a] < rk[b]:
                            bits |= 1 << i
                    row.append(bits)
                rows.append(tuple(row))
            table[p] = tuple(rows)
        return table

    def pref(self, p: Profile, i: int, a: int, b: int) -> bool:
        """Voter i ranks a strictly above b in p."""
        rk = self._rank[p[i]]
        return rk[a] < rk[b]

    def unanimous(self, p: Profile, a: int, b: int) -> bool:
        """Every voter ranks a above b."""
        return a != b and self._mask[p][a][b] == self._full

    def samepair(self, p: Profile, q: Profile, a: int, b: int) -> bool:
        """Every voter ranks a against b the same way in p and in q."""
        return self._mask[p][a][b] == self._mask[q][a][b]

    def beats(self, p: Profile, a: int, b: int) -> bool:
        """A strict majority ranks a above b."""
        return a != b and 2 * self._mask[p][a][b].bit_count() > self.voters

    def condorcet(self, p: Profile, c: int) -> bool:
        """c beats every other candidate head to head."""
        return all(self.beats(p, c, d) for d in self.cands if d != c)

    def condorcet_winner(self, p: Profile) -> int | None:
        for c in self.cands:
            if self.condorcet(p, c):
                return c
        return None

    def condorcetloser(self, p: Profile, c: int) -> bool:
        """Every other candidate beats c head to head."""
        return all(self.beats(p, d, c) for d in self.cands if d != c)

    @cached_property
    def _tops(self) -> dict[Profile, tuple[int, ...]]:
        return {p: tuple(b[0] for b in p) for p in self.profiles}

    def majoritytop(self, p: Profile, c: int) -> bool:
        """More than half the voters put c first."""
        return 2 * self._tops[p].count(c) > self.voters

    def sametops(self, p: Profile, q: Profile) -> bool:
        """Every voter's first choice is the same in p and in q."""
        return self._tops[p] == self._tops[q]

    def improves(self, p: Profile, q: Profile, c: int) -> bool:
        """No voter has moved c down against anyone between p and q.

        The Maskin monotonic transformation: for every voter, whatever c beat on
        that ballot in p, it still beats in q. Nothing is asked of pairs that do
        not involve c.
        """
        mp, mq = self._mask[p], self._mask[q]
        return all(mp[c][d] & ~mq[c][d] == 0 for d in self.cands if d != c)


def _positions(b: Ballot) -> tuple[int, ...]:
    pos = [0] * len(b)
    for k, c in enumerate(b):
        pos[c] = k
    return tuple(pos)
