import json
from pathlib import Path

import cython


@cython.cfunc
def _get_local_chapters() -> tuple[tuple[str, str], ...]:
    resources = Path('node_modules/osm-community-index/dist/resources.min.json').read_bytes()
    communities_dict: dict[str, dict] = json.loads(resources)['resources']
    # filter local chapters
    chapters = [c for c in communities_dict.values() if c['type'] == 'osm-lc' and c['id'] != 'OSMF']
    chapters.sort(key=lambda c: c['id'].casefold())
    return tuple((c['id'], c['strings']['url']) for c in chapters)


LOCAL_CHAPTERS = _get_local_chapters()
"""
Sequence of local chapters (id, url) tuples.

>>> LOCAL_CHAPTERS
[('be-chapter', 'https://openstreetmap.be'), ...]
"""
