
import argparse
import sys
from typing import Iterable, Optional

import censusdis.data as ced
import censusdis.maps as cem
import divintseg as dis
import geopandas as gpd
from censusdis.states import ALL_STATES_DC_AND_PR

verbose = False

DATASET = 'acs/acs5'


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


# From https://github.com/vengroff/censusdis/blob/main/notebooks/Nationwide%20Diversity%20and%20Integration.ipynb
def tract_bounds(year: int, epsg: int) -> gpd.GeoDataFrame:

    group = "B03002"
    total_col = f'{group}_001E'

    # Download the data

    df_bg = ced.download(
        DATASET,
        year,
        [total_col],
        leaves_of_group=group,
        state=ALL_STATES_DC_AND_PR,
        block_group="*",
    )

    leaf_cols = [col for col in df_bg.columns if col.startswith(group) and col != total_col]

    # Compute diversity and integration

    df_di = dis.di(
        df_bg[["STATE", "COUNTY", "TRACT", "BLOCK_GROUP"] + leaf_cols],
        by=["STATE", "COUNTY", "TRACT"],
        over="BLOCK_GROUP",
    ).reset_index()

    # Sum up over tracts and merge in.

    df_by_tracts = df_bg.groupby(
        ["STATE", "COUNTY", "TRACT"]
    )[[total_col] + leaf_cols].sum().reset_index()

    df_di = df_di.merge(df_by_tracts, on=["STATE", "COUNTY", "TRACT"])

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
    gdf_tracts.to_file(filename)


def main(argv: Iterable[str]):
    parser = argparse.ArgumentParser(prog=argv[0])

    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-y', '--year', required=True, type=int)

    parser.add_argument('-e', '--epsg', type=int, default=4326)
    parser.add_argument('-o', '--output', type=str, help="Output file.", required=True)
    parser.add_argument('-r', '--rep-output', type=str, help="Output file of representative points.")

    parser.add_argument(
        dest='layer',
        choices=['states', 'tracts']
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


if __name__ == "__main__":
    main(sys.argv)