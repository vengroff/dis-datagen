
import argparse
import sys
from typing import Iterable, Optional

import censusdis.data as ced
import censusdis.maps as cem
import divintseg as dis
import pandas as pd
import geopandas as gpd
import numpy as np
from censusdis.states import ALL_STATES_DC_AND_PR, STATE_NAMES_FROM_IDS, STATE_NY, STATE_NJ, STATE_CT

verbose = False

DATASET = 'dec/pl'


def state_bounds(year: int, epsg: int) -> gpd.GeoDataFrame:
    """
    Generate a file of state vector boundaries.

    Parameters
    ----------
    year
        Year of census data to use.
    epsg
        The epsg to project to.

    Returns
    -------
        The states in a geo data frame.
    """
    gdf_states = ced.download(
        DATASET, year,
        ['NAME'],
        state=ALL_STATES_DC_AND_PR,
        with_geometry=True
    )

    gdf_states = cem.relocate_ak_hi_pr(gdf_states)

    gdf_states = gdf_states.to_crs(epsg=epsg)

    return gdf_states


def save_state_bounds(year: int, epsg: int, filename: str, rep_filename: Optional[str]):
    """
    Generate and save the state bounds.

    Parameters
    ----------
    year
        Year of census data to use.
    epsg
        The epsg to project to.
    filename
        The path to the output file.

    Returns
    -------
        None
    """
    gdf_states = state_bounds(year, epsg)
    gdf_states.to_file(filename)

    if rep_filename is not None:
        gdf_states.geometry = gdf_states.representative_point()
        gdf_states.to_file(rep_filename)


def city_bounds(year: int, epsg: int) -> gpd.GeoDataFrame:
    """
    Generate a file of city vector boundaries.

    Parameters
    ----------
    year
        Year of census data to use.
    epsg
        The epsg to project to.

    Returns
    -------
        The cities in a geo data frame.
    """
    group = "P2"
    total_col = f'{group}_001N'

    gdf_cities = ced.download(
        DATASET, year,
        ['NAME', total_col],
        place="*",
        with_geometry=True
    )

    gdf_cities = gdf_cities.sort_values(by=total_col, ascending=False).reset_index(drop=False)

    if verbose:
        print(gdf_cities[['NAME', total_col]].head(10))

    gdf_cities = cem.relocate_ak_hi_pr(gdf_cities)

    gdf_cities = gdf_cities.to_crs(epsg=epsg)

    return gdf_cities


def save_city_bounds(year: int, epsg: int, filename: str, rep_filename: Optional[str]):
    """
    Generate and save city bounds.

    Parameters
    ----------
    year
        Year of census data to use.
    epsg
        The epsg to project to.
    filename
        The path to the output file.

    Returns
    -------
        None
    """
    gdf_cities = city_bounds(year, epsg)
    gdf_cities.to_file(filename)

    if rep_filename is not None:
        gdf_cities.geometry = gdf_cities.representative_point()
        gdf_cities.to_file(rep_filename)


# From https://github.com/vengroff/censusdis/blob/main/notebooks/Nationwide%20Diversity%20and%20Integration.ipynb
def tract_bounds(year: int, epsg: int) -> gpd.GeoDataFrame:

    group = "P2"
    total_col = f'{group}_001N'

    # Download the data

    # If we try to bulk download all states at once we
    # get a 500 from the API with the error, "There was
    # an error while running your query.  We've logged
    # the error and we'll correct it ASAP.  Sorry for
    # the inconvenience." So go state by state and
    # concat them.
    df_block_per_state = []

    for state in ALL_STATES_DC_AND_PR:
        if verbose:
            print(f"Processing {STATE_NAMES_FROM_IDS[state]}")

        df_block_for_state = ced.download(
            DATASET,
            year,
            [total_col],
            leaves_of_group=group,
            state=state,
            block="*",
        )
        if verbose:
            print(f"Downladed {len(df_block_for_state.index)} rows.")
        df_block_per_state.append(df_block_for_state)

    df_block = pd.concat(df_block_per_state)

    if verbose:
        print(f"Downloaded a total of {len(df_block.index)} rows in {len(df_block_for_state)} state batches.")

    leaf_cols = [col for col in df_block.columns if col.startswith(group) and col != total_col]

    # Compute diversity and integration

    df_di = dis.di(
        df_block[["STATE", "COUNTY", "TRACT", "BLOCK"] + leaf_cols],
        by=["STATE", "COUNTY", "TRACT"],
        over="BLOCK",
    ).reset_index()

    if verbose:
        print(f"DI over {len(df_di.index)} rows.")

    # Sum up over tracts and merge in.

    df_by_tracts = df_block.groupby(
        ["STATE", "COUNTY", "TRACT"]
    )[[total_col] + leaf_cols].sum().reset_index()

    # Replace zeros with NaN so they are left out of the
    # geojson file we write.
    df_features = df_by_tracts.replace(0, np.nan)

    df_di = df_di.merge(df_features, on=["STATE", "COUNTY", "TRACT"])

    # Infer the geographies

    gdf_di = ced.add_inferred_geography(df_di, year)

    gdf_di = gdf_di[~gdf_di.geometry.isnull()]

    # Get census county names.
    df_county_names = ced.download(
        DATASET,
        year,
        ['NAME'],
        state="*",
        county="*",
    ).rename({'NAME': 'COUNTY_NAME'}, axis='columns')

    gdf_di = gdf_di.merge(df_county_names, on=['STATE', 'COUNTY'])

    gdf_di = cem.relocate_ak_hi_pr(gdf_di)

    return gdf_di.to_crs(epsg=epsg)


def save_tract_bounds(year: int, epsg: int, filename: str):
    """
    Generate and save the state bounds.

    Parameters
    ----------
    year
        Year of census data to use.
    epsg
        The epsg to project to.
    filename
        The path to the output file.

    Returns
    -------
        None
    """
    gdf_tracts = tract_bounds(year, epsg)
    with open(filename, 'w') as file:
        file.write(gdf_tracts.to_json(na='drop'))


def main(argv: Iterable[str]):
    parser = argparse.ArgumentParser(prog=argv[0])

    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-y', '--year', required=True, type=int)

    parser.add_argument('-e', '--epsg', type=int, default=4326)
    parser.add_argument('-o', '--output', type=str, help="Output file.", required=True)
    parser.add_argument('-r', '--rep-output', type=str, help="Output file of representative points.")

    parser.add_argument(
        dest='layer',
        choices=['states', 'tracts', 'cities']
    )

    args = parser.parse_args(argv[1:])

    global verbose

    verbose = args.verbose

    if verbose:
        print("Verbose mode on.")

    filename = args.output
    rep_filename = args.rep_output

    if args.layer == 'states':
        save_state_bounds(year=args.year, epsg=args.epsg, filename=filename, rep_filename=rep_filename)
    elif args.layer == 'tracts':
        save_tract_bounds(year=args.year, epsg=args.epsg, filename=filename)
    elif args.layer == 'cities':
        save_city_bounds(year=args.year, epsg=args.epsg, filename=filename, rep_filename=rep_filename)


if __name__ == "__main__":
    main(sys.argv)