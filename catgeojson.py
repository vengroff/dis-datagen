"""Small script to concatenate all the state geojson tract files."""

import argparse
import pandas as pd
import geopandas as gpd


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('-o', '--output', type=str, required=True)
    parser.add_argument('-c', '--csv', type=str)
    parser.add_argument("files", nargs="+")

    args = parser.parse_args()

    gdf_all = gpd.GeoDataFrame(
        pd.concat((gpd.read_file(file) for file in args.files), ignore_index=True)
    )
    with open(args.output, 'w') as file:
        file.write(gdf_all.to_json(na='drop'))

    if args.csv is not None:
        gdf_all[
            [col for col in gdf_all if col not in ['id', 'geometry', 'COUNTY_NAME']]
        ].to_csv(args.csv, index=False)


if __name__ == "__main__":
    main()
