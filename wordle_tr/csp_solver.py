"""Candidate filtering as a constraint satisfaction problem.

Variables X1..X5 are the letters of the hidden word. Domains come from
``Constraints.domains()`` (node consistency); the letter-count bounds are global
constraints; the dictionary constraint is enforced by searching inside a trie
of the answer list, so only prefixes of real words are ever extended. The
search assigns X1, X2, ... in order (backtracking) and, after each assignment,
runs forward checking.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from wordle_tr.alphabet import ALPHABET, WORD_LENGTH, sort_key
from wordle_tr.constraints import Constraints


class WordTrie:
    """Prefix tree of equal-length words; children are kept in Turkish alphabetical order."""

    def __init__(self, words: Iterable[str]) -> None:
        root: dict = {}
        for word in words:
            node = root
            for letter in word:
                node = node.setdefault(letter, {})
        self.root = _sorted_children(root)
        self.size = _count_nodes(self.root)  # nodes below the root

    def __contains__(self, word: str) -> bool:
        node = self.root
        for letter in word:
            if letter not in node:
                return False
            node = node[letter]
        return True

    def words(self) -> list[str]:
        """All stored words, in Turkish alphabetical order."""
        out: list[str] = []

        def walk(node: dict, prefix: str) -> None:
            if not node:
                out.append(prefix)
            for letter, child in node.items():
                walk(child, prefix + letter)

        walk(self.root, "")
        return out


def _sorted_children(node: dict) -> dict:
    return {c: _sorted_children(node[c]) for c in sorted(node, key=sort_key)}


def _count_nodes(node: dict) -> int:
    return sum(1 + _count_nodes(child) for child in node.values())


@dataclass
class CSPResult:
    solutions: list[str]  # in Turkish alphabetical order
    nodes_expanded: int  # assignments tried (= trie nodes visited)


class CSPSolver:
    """Backtracking search with forward checking over a trie of ``words``."""

    def __init__(self, words: Iterable[str]) -> None:
        self.trie = WordTrie(words)

    def solve(self, constraints: Constraints, forward_checking: bool = True) -> CSPResult:
        n = WORD_LENGTH
        domains = constraints.domains()
        ordered = [[c for c in ALPHABET if c in d] for d in domains]
        hi = {c: k for c, k in constraints.max_count.items() if k < n}
        lo = {c: k for c, k in constraints.min_count.items() if k > 0}
        # room[c][p]: positions p..n-1 whose domain still allows c
        room = {c: [sum(c in domains[j] for j in range(p, n)) for p in range(n + 1)] for c in lo}
        counts = dict.fromkeys(ALPHABET, 0)
        letters = [""] * n
        solutions: list[str] = []
        nodes = 0

        def forward_check(pos: int, assigned: str) -> bool:
            """After an assignment: can X_pos .. X_n still satisfy the count constraints?"""
            shortfall = 0
            for c, k in lo.items():
                need = k - counts[c]
                if need > 0:
                    if need > room[c][pos]:  # too few later positions allow c
                        return False
                    shortfall += need
            if shortfall > n - pos:  # the required letters do not fit
                return False
            if counts[assigned] == hi.get(assigned, n):  # it reached its maximum: remove it from
                for j in range(pos, n):                 # the later domains; none may become empty
                    if all(counts[c] >= hi.get(c, n) for c in ordered[j]):
                        return False
            return True

        def complete() -> bool:
            return all(counts[c] >= k for c, k in lo.items()) and all(counts[c] <= k for c, k in hi.items())

        def backtrack(node: dict, pos: int) -> None:
            nonlocal nodes
            if pos == n:
                if forward_checking or complete():
                    solutions.append("".join(letters))
                return
            domain = domains[pos]
            if len(ordered[pos]) < len(node):
                options = [(c, node[c]) for c in ordered[pos] if c in node]
            else:
                options = [(c, child) for c, child in node.items() if c in domain]
            for c, child in options:
                if forward_checking and counts[c] >= hi.get(c, n):  # maximum count would be exceeded
                    continue
                nodes += 1
                letters[pos] = c
                counts[c] += 1
                if not forward_checking or forward_check(pos + 1, c):
                    backtrack(child, pos + 1)
                counts[c] -= 1

        backtrack(self.trie.root, 0)
        return CSPResult(solutions, nodes)
