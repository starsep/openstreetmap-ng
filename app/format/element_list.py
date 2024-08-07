from collections.abc import Collection, Iterable
from dataclasses import dataclass

import cython

from app.lib.feature_icon import feature_icon
from app.lib.feature_name import feature_name
from app.models.db.element import Element
from app.models.db.element_member import ElementMember
from app.models.element_ref import ElementRef, VersionedElementRef
from app.models.element_type import ElementType
from app.queries.element_query import ElementQuery


@dataclass(frozen=True, slots=True)
class _Base:
    type: ElementType
    id: int
    name: str | None
    icon: str | None
    icon_title: str | None


@dataclass(frozen=True, slots=True)
class ChangesetListEntry(_Base):
    version: int
    visible: bool


@dataclass(frozen=True, slots=True)
class MemberListEntry(_Base):
    role: str | None


class FormatElementList:
    @staticmethod
    async def changeset_elements(elements: Collection[Element]) -> dict[ElementType, list[ChangesetListEntry]]:
        """
        Format elements for displaying on the website (icons, strikethrough, sort).

        Returns a mapping of element types to sequences of ElementStyle.
        """
        # element.version > 1 is mostly redundant
        # but ensures backward-compatible compliance for PositiveInt
        prev_refs: tuple[VersionedElementRef, ...] = tuple(
            VersionedElementRef(element.type, element.id, element.version - 1)
            for element in elements
            if not element.visible and element.version > 1
        )

        if prev_refs:
            prev_elements = await ElementQuery.get_by_versioned_refs(prev_refs, limit=len(prev_refs))
            prev_type_id_map = {(element.type, element.id): element for element in prev_elements}
        else:
            prev_type_id_map = {}

        result: dict[ElementType, list[ChangesetListEntry]] = {'node': [], 'way': [], 'relation': []}
        for element in elements:
            result[element.type].append(_encode_element(prev_type_id_map, element))
        for v in result.values():
            v.sort(key=_sort_key)
        return result

    @staticmethod
    def element_parents(ref: ElementRef, parents: Iterable[Element]) -> tuple[MemberListEntry, ...]:
        return tuple(_encode_parent(ref, element) for element in parents)

    @staticmethod
    def element_members(
        members: Iterable[ElementMember],
        members_elements: Iterable[Element],
    ) -> tuple[MemberListEntry, ...]:
        type_id_map: dict[tuple[ElementType, int], Element] = {
            (member.type, member.id): member  #
            for member in members_elements
        }
        return tuple(filter(None, (_encode_member(type_id_map, member) for member in members)))


@cython.cfunc
def _encode_element(prev_type_id_map: dict[tuple[ElementType, int], Element], element: Element):
    element_type = element.type
    element_id = element.id
    prev = prev_type_id_map.get((element_type, element_id))
    tags = prev.tags if (prev is not None) else element.tags

    if tags:
        name = feature_name(tags)
        resolved = feature_icon(element_type, tags)
    else:
        name = None
        resolved = None

    if resolved is not None:
        icon = resolved[0]
        icon_title = resolved[1]
    else:
        icon = None
        icon_title = None

    return ChangesetListEntry(
        type=element_type,
        id=element_id,
        name=name,
        version=element.version,
        visible=element.visible,
        icon=icon,
        icon_title=icon_title,
    )


@cython.cfunc
def _encode_parent(ref: ElementRef, element: Element):
    element_type = element.type
    element_id = element.id

    if tags := element.tags:
        name = feature_name(tags)
        resolved = feature_icon(element_type, tags)
    else:
        name = None
        resolved = None

    if resolved is not None:
        icon = resolved[0]
        icon_title = resolved[1]
    else:
        icon = None
        icon_title = None

    if element_type == 'relation':
        members = element.members
        if members is None:
            raise AssertionError('Relation members must be set')
        role = ', '.join(
            sorted(
                {
                    member_ref.role
                    for member_ref in members
                    if member_ref.role and member_ref.id == ref.id and member_ref.type == ref.type
                }
            )
        )
    else:
        role = ''

    return MemberListEntry(
        type=element_type,
        id=element_id,
        name=name,
        icon=icon,
        icon_title=icon_title,
        role=role,
    )


@cython.cfunc
def _encode_member(type_id_map: dict[tuple[ElementType, int], Element], member: ElementMember):
    member_type = member.type
    member_id = member.id
    element = type_id_map.get((member_type, member_id))
    if element is None:
        return None

    if tags := element.tags:
        name = feature_name(tags)
        resolved = feature_icon(member_type, tags)
    else:
        name = None
        resolved = None

    if resolved is not None:
        icon = resolved[0]
        icon_title = resolved[1]
    else:
        icon = None
        icon_title = None

    return MemberListEntry(
        type=member_type,
        id=member_id,
        name=name,
        icon=icon,
        icon_title=icon_title,
        role=member.role,
    )


@cython.cfunc
def _sort_key(element: Element) -> tuple:
    return (not element.visible, element.id, element.version)
