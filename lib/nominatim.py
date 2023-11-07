import logging
from abc import ABC
from urllib.parse import urlencode

from httpx import HTTPError
from shapely.geometry import Point

from config import NOMINATIM_URL
from lib.cache import Cache
from utils import HTTP


class Nominatim(ABC):
    @staticmethod
    async def reverse_name(point: Point, zoom: int, locales: str) -> str:
        '''
        Reverse geocode a point into a human-readable name.
        '''

        path = '/reverse?' + urlencode({
            'format': 'jsonv2',
            'lon': point.x,
            'lat': point.y,
            'zoom': zoom,
            'accept-language': locales,
        })

        async def factory() -> str:
            r = await HTTP.get(NOMINATIM_URL + path, timeout=4)
            r.raise_for_status()
            data = await r.json()
            return data['display_name']

        try:
            display_name = await Cache.get_one_by_key(path, factory)
        except HTTPError:
            logging.warning('Nominatim reverse geocoding failed', exc_info=True)
            display_name = None

        if display_name:
            return display_name
        else:
            # always succeed, return coordinates as a fallback
            return f'{point.y:.3f}, {point.x:.3f}'
