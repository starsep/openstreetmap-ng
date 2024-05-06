from collections import defaultdict
from collections.abc import Sequence

import cython
import numpy as np
from shapely import Point, get_coordinates, points

from app.lib.date_utils import legacy_date
from app.lib.exceptions_context import raise_for
from app.lib.format_style_context import format_is_json
from app.models.db.element import Element
from app.models.element_member_ref import ElementMemberRef
from app.models.element_type import ElementType
from app.models.osmchange_action import OSMChangeAction
from app.models.validating.element import ElementValidating


class Element06Mixin:
    @staticmethod
    def encode_element(element: Element) -> dict:
        """
        >>> encode_element(Element(type=ElementType.node, id=1, version=1, ...))
        {'node': {'@id': 1, '@version': 1, ...}}
        """
        if format_is_json():
            return _encode_element(element, is_json=True)
        else:
            return {element.type: _encode_element(element, is_json=False)}

    @staticmethod
    def encode_elements(elements: Sequence[Element]) -> dict[str, Sequence[dict]]:
        """
        >>> encode_elements([
        ...     Element(type=ElementType.node, id=1, version=1, ...),
        ...     Element(type=ElementType.way, id=2, version=1,
        ... ])
        {'node': [{'@id': 1, '@version': 1, ...}], 'way': [{'@id': 2, '@version': 1, ...}]}
        """
        if format_is_json():
            return {'elements': tuple(_encode_element(element, is_json=True) for element in elements)}
        else:
            result: dict[ElementType, list[dict]] = defaultdict(list)

            # merge elements of the same type together
            for element in elements:
                result[element.type].append(_encode_element(element, is_json=False))

            return result

    @staticmethod
    def decode_element(element: tuple[ElementType, dict]) -> Element:
        """
        >>> decode_element(('node', {'@id': 1, '@version': 1, ...}))
        Element(type=ElementType.node, ...)
        """
        type = element[0]
        data = element[1]
        return _decode_element(type, data, changeset_id=None)

    @staticmethod
    def encode_osmchange(elements: Sequence[Element]) -> Sequence[tuple[OSMChangeAction, dict[ElementType, dict]]]:
        """
        >>> encode_osmchange([
        ...     Element(type=ElementType.node, id=1, version=1, ...),
        ...     Element(type=ElementType.way, id=2, version=2, ...)
        ... ])
        [
            ('create', {'node': {'@id': 1, '@version': 1, ...}}),
            ('modify', {'way': {'@id': 2, '@version': 2, ...}}),
        ]
        """
        result = []

        for element in elements:
            # determine the action automatically
            if element.version == 1:
                action = 'create'
            elif element.visible:
                action = 'modify'
            else:
                action = 'delete'

            result.append((action, {element.type: _encode_element(element, is_json=False)}))

        return result

    @staticmethod
    def decode_osmchange(
        changes: Sequence[tuple[OSMChangeAction, Sequence[tuple[ElementType, dict]]]], *, changeset_id: int | None
    ) -> Sequence[Element]:
        """
        If `changeset_id` is None, it will be extracted from the element data.

        >>> decode_osmchange([
        ...     ('create', [('node', {'@id': 1, '@version': 1, ...})]),
        ...     ('modify', [('way', {'@id': 2, '@version': 2, ...})])
        ... ])
        [Element(type=ElementType, ...), Element(type=ElementType.way, ...)]
        """
        # skip attributes-only osmChange
        if isinstance(changes, dict):
            return ()

        result = []

        for action, elements_data in changes:
            # skip osmChange attributes
            if action.startswith('@'):
                continue
            # skip attributes-only actions
            if isinstance(elements_data, dict):
                continue

            if action == 'create':
                for key, data in elements_data:
                    data['@version'] = 0
                    element = _decode_element(key, data, changeset_id=changeset_id)

                    if element.id > 0:
                        raise_for().diff_create_bad_id(element.versioned_ref)

                    result.append(element)

            elif action == 'modify':
                for key, data in elements_data:
                    element = _decode_element(key, data, changeset_id=changeset_id)

                    if element.version < 2:
                        raise_for().diff_update_bad_version(element.versioned_ref)

                    result.append(element)

            elif action == 'delete':
                delete_if_unused: bool = False  # TODO: finish implementation

                for key, data in elements_data:
                    if key == '@if-unused':
                        delete_if_unused = True
                        continue

                    data['@visible'] = False
                    element = _decode_element(key, data, changeset_id=changeset_id)

                    if element.version < 2:
                        raise_for().diff_update_bad_version(element.versioned_ref)

                    result.append(element)

            else:
                raise_for().diff_unsupported_action(action)

        return result


@cython.cfunc
def _encode_nodes(nodes: Sequence[ElementMemberRef], *, is_json: cython.char) -> tuple[dict | int, ...]:
    """
    >>> _encode_nodes([
    ...     ElementMemberRef(type=ElementType.node, id=1, role=''),
    ...     ElementMemberRef(type=ElementType.node, id=2, role=''),
    ... ])
    [{'@ref': 1}, {'@ref': 2}]
    """
    if is_json:
        return tuple(node.id for node in nodes)
    else:
        return tuple({'@ref': node.id} for node in nodes)


@cython.cfunc
def _decode_nodes_unsafe(nodes: Sequence[dict]) -> tuple[ElementMemberRef, ...]:
    """
    This method does not validate the input data.

    >>> _decode_nodes_unsafe([{'@ref': '1'}])
    [ElementMemberRef(type=ElementType.node, id=1, role='')]
    """
    return tuple(
        ElementMemberRef(
            type='node',
            id=int(node['@ref']),
            role='',
        )
        for node in nodes
    )


@cython.cfunc
def _encode_members(members: Sequence[ElementMemberRef], *, is_json: cython.char) -> tuple[dict, ...]:
    """
    >>> _encode_members([
    ...     ElementMemberRef(type=ElementType.node, id=1, role='a'),
    ...     ElementMemberRef(type=ElementType.way, id=2, role='b'),
    ... ], is_json=False)
    [
        {'@type': 'node', '@ref': 1, '@role': 'a'},
        {'@type': 'way', '@ref': 2, '@role': 'b'},
    ]
    """
    if is_json:
        return tuple(
            {
                'type': member.type,
                'ref': member.id,
                'role': member.role,
            }
            for member in members
        )
    else:
        return tuple(
            {
                '@type': member.type,
                '@ref': member.id,
                '@role': member.role,
            }
            for member in members
        )


@cython.cfunc
def _decode_members_unsafe(members: Sequence[dict]) -> tuple[ElementMemberRef, ...]:
    """
    This method does not validate the input data.

    >>> _decode_members_unsafe([
    ...     {'@type': 'node', '@ref': '1', '@role': 'a'},
    ... ])
    [ElementMemberRef(type=ElementType.node, id=1, role='a')]
    """
    return tuple(
        ElementMemberRef(
            type=member['@type'],
            id=int(member['@ref']),
            role=member['@role'],
        )
        for member in members
    )


@cython.cfunc
def _encode_element(element: Element, *, is_json: cython.char) -> dict:
    """
    >>> _encode_element(Element(type=ElementType.node, id=1, version=1, ...))
    {'@id': 1, '@version': 1, ...}
    """
    # read property once for performance
    element_type = element.type
    changeset = element.changeset

    is_node: cython.char = element_type == 'node'
    is_way: cython.char = not is_node and element_type == 'way'
    is_relation: cython.char = not is_node and not is_way

    if is_json:
        return {
            'type': element_type,
            'id': element.id,
            **(_encode_point(element.point, is_json=True) if is_node else {}),
            'version': element.version,
            'timestamp': legacy_date(element.created_at),
            'changeset': element.changeset_id,
            **(
                {
                    'uid': changeset.user_id,
                    'user': changeset.user.display_name,
                }
                if changeset.user_id is not None
                else {}
            ),
            'visible': element.visible,
            'tags': element.tags,
            **({'nodes': _encode_nodes(element.members, is_json=True)} if is_way else {}),
            **({'members': _encode_members(element.members, is_json=True)} if is_relation else {}),
        }
    else:
        return {
            '@id': element.id,
            **(_encode_point(element.point, is_json=False) if is_node else {}),
            '@version': element.version,
            '@timestamp': legacy_date(element.created_at),
            '@changeset': element.changeset_id,
            **(
                {
                    '@uid': changeset.user_id,
                    '@user': changeset.user.display_name,
                }
                if changeset.user_id is not None
                else {}
            ),
            '@visible': element.visible,
            'tag': tuple({'@k': k, '@v': v} for k, v in element.tags.items()),
            **({'nd': _encode_nodes(element.members, is_json=False)} if is_way else {}),
            **({'member': _encode_members(element.members, is_json=False)} if is_relation else {}),
        }


@cython.cfunc
def _decode_element(type: ElementType, data: dict, *, changeset_id: int | None):
    """
    If `changeset_id` is None, it will be extracted from the element data.

    >>> decode_element(('node', {'@id': 1, '@version': 1, ...}))
    Element(type=ElementType.node, ...)
    """
    if (data_tags := data.get('tag')) is not None:
        tags = _decode_tags_unsafe(data_tags)
    else:
        tags = {}

    if (lon := data.get('@lon')) is None or (lat := data.get('@lat')) is None:
        point = None
    else:
        # numpy automatically parses strings
        point = points(np.array((lon, lat), np.float64))

    # decode members from either nd or member
    if (data_nodes := data.get('nd')) is not None:
        members = _decode_nodes_unsafe(data_nodes)
    elif (data_members := data.get('member')) is not None:
        members = _decode_members_unsafe(data_members)
    else:
        members = ()

    return Element(
        **dict(
            ElementValidating(
                changeset_id=changeset_id if (changeset_id is not None) else data.get('@changeset'),
                type=type,
                id=data.get('@id'),
                version=data.get('@version', 0) + 1,
                visible=data.get('@visible', True),
                tags=tags,
                point=point,
                members=members,
            )
        )
    )


@cython.cfunc
def _encode_point(point: Point | None, *, is_json: cython.char) -> dict:
    """
    >>> _encode_point(Point(1, 2), is_json=False)
    {'@lon': 1, '@lat': 2}
    """
    if point is None:
        return {}

    x, y = get_coordinates(point)[0].tolist()

    if is_json:
        return {'lon': x, 'lat': y}
    else:
        return {'@lon': x, '@lat': y}


@cython.cfunc
def _decode_tags_unsafe(tags: Sequence[dict]) -> dict:
    """
    This method does not validate the input data.

    >>> _decode_tags_unsafe([
    ...     {'@k': 'a', '@v': '1'},
    ...     {'@k': 'b', '@v': '2'},
    ... ])
    {'a': '1', 'b': '2'}
    """
    items = tuple((tag['@k'], tag['@v']) for tag in tags)
    result = dict(items)

    if len(items) != len(result):
        raise ValueError('Duplicate tag keys')

    return result
