from enum import Enum
from typing import Self


class ElementType(str, Enum):
    node = 'node'
    way = 'way'
    relation = 'relation'

    @staticmethod
    def from_str(cls, s: str) -> Self:
        """
        Get the element type from the given string.

        >>> ElementType.from_str('node')
        ElementType.node
        >>> ElementType.from_str('w123')
        ElementType.way
        """

        if s.startswith('n'):
            return cls.node
        elif s.startswith('w'):
            return cls.way
        elif s.startswith('r'):
            return cls.relation
        else:
            raise ValueError(f'Unknown element type {s!r}')
