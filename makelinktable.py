"""A quick utility to copy to the public names and make a csv for import to Wordpress."""

from pathlib import Path
import argparse
from censusdis.states import ALL_STATES_DC_AND_PR, STATE_NAMES_FROM_IDS


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('-o', '--output', type=str, required=True, help='Output directory')
    parser.add_argument('-d', '--data', type=str, help='Data directory')

    args = parser.parse_args()

    output_dir = Path(args.output)
    data_dir = Path(args.data)

    url = 'http://di-map.datapinions.com/data/1.0'

    for state in ALL_STATES_DC_AND_PR:
        name = STATE_NAMES_FROM_IDS[state]
        filename = f"{state}-{name}-2020".replace(' ', '_')

        # Write the line of the csv.
        print(
            f'{name},'
            f'<a href="{url}/csv/{filename}.csv">{filename}.csv</a>,'
            f'<a href="{url}/geojson/{filename}.geojson">{filename}.geojson</a>'
        )

        # Symlink to the dir so it's easy to copy to the cloud.
        for ext in ['csv', 'geojson']:
            data_file = data_dir / f'tracts-2020-{state}.{ext}'
            output_ext_dir = output_dir / ext
            output_ext_dir.mkdir(exist_ok=True, parents=True)
            link = output_ext_dir / f'{filename}.{ext}'

            link.symlink_to(data_file.absolute())


if __name__ == "__main__":
    main()
