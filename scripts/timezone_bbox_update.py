import json
from math import isclose

import anyio
from anyio import Path
from pytz import country_timezones
from shapely.geometry import shape
from zstandard import ZstdDecompressor

from app.utils import HTTP


def get_timezone_country_dict() -> dict[str, str]:
    result = {}

    print('Processing country timezones')
    for code, timezones in country_timezones.items():
        for timezone in timezones:
            if timezone in result:
                raise ValueError(f'Duplicate timezone {timezone!r}')

            result[timezone] = code

    return result


async def get_country_bbox_dict() -> dict[str, tuple[float, float, float, float]]:
    print('Downloading country data')
    r = await HTTP.get('https://osm-countries-geojson.monicz.dev/osm-countries-0-1.geojson.zst')
    r.raise_for_status()

    content = ZstdDecompressor().decompress(r.content)
    features = json.loads(content)['features']

    result = {}

    print('Processing country boundaries')
    for feature in features:
        tags: dict = feature['properties']['tags']
        country: str | None = tags.get('ISO3166-1:alpha2', tags.get('ISO3166-1'))

        if country is None:
            raise ValueError(f'Country code not found in {tags!r}')

        geom = shape(feature['geometry'])
        bbox = geom.bounds

        if country == 'FJ':
            bbox = (-182.870666, -20.67597, 181.575562, -12.480111)
        elif country == 'RU':
            bbox = (19.25, 41.188862, 190.95, 81.857361)
        elif country == 'TV':
            bbox = (176.064865, -10.801169, 179.863281, -5.641972)
        elif country == 'US':
            bbox = (-124.733253, 24.544245, -66.954811, 49.388611)

        if isclose(bbox[0], -180) and isclose(bbox[2], 180):
            print(f'[⚠️] {country}: spanning over 180° meridian')

        if country in result:
            raise ValueError(f'Duplicate country {country!r}')

        result[country] = bbox

    return result


def generate_javascript_file(data: dict[str, tuple[float, float, float, float]]) -> str:
    print('Generating JavaScript file')

    result = []
    items = sorted(data.items())

    for timezone, bbox in items:
        result.append(f'    ["{timezone}", [{bbox[0]}, {bbox[1]}, {bbox[2]}, {bbox[3]}]]')

    header = '// This file is auto-generated by `timezone-bbox-update`'
    return f'{header}\n\nexport const timezoneBoundsMap = new Map([\n' + ',\n'.join(result) + '\n])'


async def main():
    country_bbox = await get_country_bbox_dict()
    timezone_country = get_timezone_country_dict()

    result = {}

    print('Merging timezones with boundaries')
    for timezone, country in timezone_country.items():
        bbox = country_bbox.get(country)

        if bbox is None:
            print(f'[❔] {timezone}: missing {country!r} boundary')
            continue

        result[timezone] = bbox

    output = generate_javascript_file(result)
    output_path = Path('app/static/js/_timezone-bbox.js')
    await output_path.write_text(output)


if __name__ == '__main__':
    anyio.run(main)
