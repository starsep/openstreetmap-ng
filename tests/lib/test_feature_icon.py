import pytest

from app.lib.feature_icon import features_icons
from app.models.db.element import Element
from app.models.element import ElementId


@pytest.mark.parametrize(
    ('type', 'tags', 'expected'),
    [
        ('way', {'crab': 'yes'}, ('crab_yes.webp', 'crab=yes')),
        ('node', {'non_existing_key': 'aaa'}, None),
    ],
)
def test_features_icons(type, tags, expected):
    element = Element(
        changeset_id=1,
        type=type,
        id=ElementId(1),
        version=1,
        visible=False,
        tags=tags,
        point=None,
        members=[],
    )
    assert features_icons((element,)) == (expected,)
