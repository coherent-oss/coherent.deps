"""
Parse and match ``scope: action[rule, ...]`` comment directives.

Directives follow the shape shared by type-checker suppression comments
(e.g. ``type: ignore[attr-defined]``, ``ty: ignore[unresolved-import]``).

Private for now; may be extracted into its own library later.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

_pattern = re.compile(
    r'\b(?P<scope>[\w.]+)\s*:\s*(?P<action>[\w.]+)\s*(?:\[(?P<rules>[^\]]*)\])?'
)


class Directive:
    """
    A ``scope: action[rule, ...]`` directive.

    Two directives are equal when they *match*: same scope and action, and
    either carries no rules (a wildcard over that scope/action) or their rule
    sets overlap. Matching is therefore not transitive, so directives are
    intentionally unhashable.

    A directive with no rule matches any directive of the same scope/action:

    >>> Directive.parse('type: ignore[attr-defined]') == Directive.parse('type: ignore')
    True

    Otherwise the rule sets must overlap:

    >>> Directive.parse('deps: ignore[a]') == Directive.parse('deps: ignore[b]')
    False
    >>> Directive.parse('deps: ignore[a, b]') == Directive.parse('deps: ignore[b]')
    True

    Scope and action must always agree:

    >>> Directive.parse('deps: ignore') == Directive.parse('type: ignore')
    False
    """

    def __init__(self, scope: str, action: str, rules: Iterable[str] = ()):
        self.scope = scope
        self.action = action
        self.rules = frozenset(filter(None, (rule.strip() for rule in rules)))

    @classmethod
    def parse(cls, text: str) -> Directive:
        """
        Parse the (first) directive in ``text``.

        >>> Directive.parse('# deps: ignore[inferred-dependency]')
        <Directive deps: ignore[inferred-dependency]>
        """
        return next(iter(read(text)))

    def __eq__(self, other):
        if not isinstance(other, Directive):
            return NotImplemented
        return (
            self.scope == other.scope
            and self.action == other.action
            and (not self.rules or not other.rules or bool(self.rules & other.rules))
        )

    # matching is not transitive, so instances can't satisfy the hash contract
    __hash__ = None

    def __str__(self):
        rules = f'[{", ".join(sorted(self.rules))}]' if self.rules else ''
        return f'{self.scope}: {self.action}{rules}'

    def __repr__(self):
        return f'<Directive {self}>'


def read(text: str) -> list[Directive]:
    r"""
    Parse every directive present in ``text``.

    >>> read('# ty: ignore[unresolved-import]  # deps: ignore[inferred-dependency]')
    [<Directive ty: ignore[unresolved-import]>, <Directive deps: ignore[inferred-dependency]>]

    A comment with no directive yields nothing:

    >>> read('# just a comment')
    []
    """
    return [
        Directive(
            match['scope'],
            match['action'],
            match['rules'].split(',') if match['rules'] else (),
        )
        for match in _pattern.finditer(text)
    ]


def match(directives: str, text: str) -> bool:
    """
    Is every directive in ``directives`` indicated in ``text``?

    A directive with no rule matches any directive of the same scope/action:

    >>> match('type: ignore[attr-defined]', 'type: ignore')
    True

    >>> match('deps: ignore[inferred-dependency]', '# deps: ignore[inferred-dependency]')
    True
    >>> match('deps: ignore[inferred-dependency]', '# deps: ignore')
    True
    >>> match('deps: ignore[inferred-dependency]', '# deps: ignore[other]')
    False
    >>> match('deps: ignore[inferred-dependency]', '# an unrelated comment')
    False
    """
    present = read(text)
    return all(directive in present for directive in read(directives))
