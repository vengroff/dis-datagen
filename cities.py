
import argparse
from pathlib import Path
import geopandas as gpd
import censusdis.maps as cem


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument('-e', '--epsg', type=int, default=4326)
    parser.add_argument('output', type=str, help="Output file.")

    args = parser.parse_args()

    # Original download from https://hub.arcgis.com/datasets/esri::usa-major-cities/explore?location=28.251697%2C-112.218138%2C3.71&showTable=true
    path = Path.home() / 'data' / 'USA_Major_Cities' / 'USA_Major_Cities.shp'

    gdf_cities = gpd.read_file(path)

    gdf_cities = gdf_cities.sort_values(['POPULATION'], ascending=False)[['NAME', 'POP_CLASS', 'geometry']]

    gdf_cities = cem.relocate_ak_hi_pr(gdf_cities)

    gdf_cities = gdf_cities.to_crs(epsg=args.epsg)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    for pop_class in range(6, 11):
        output_path = output_dir / f"cities-{pop_class}.geojson"

        gdf_cities[gdf_cities['POP_CLASS'] == pop_class].to_file(output_path)


if __name__ == "__main__":
    main()