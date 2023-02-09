
from typing import Iterable
import argparse
import sys
import geopandas as gpd
import censusdis.data as ced
from censusdis.states import ALL_STATES_DC_AND_PR, STATE_NJ
import divintseg as dis

from matplotlib.colors import LinearSegmentedColormap

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
    ).to_crs(epsg=epsg)

    return gdf_states


def save_state_bounds(year: int, epsg: int, filename: str):
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


# From https://github.com/vengroff/censusdis/blob/main/notebooks/Nationwide%20Diversity%20and%20Integration.ipynb
def tract_bounds(year: int, epsg: int) -> gpd.GeoDataFrame:

    group = "B03002"

    # Download the data

    df_bg = ced.download(
        DATASET,
        year,
        leaves_of_group=group,
        state=ALL_STATES_DC_AND_PR,
        block_group="*",
    )

    # Compute diversity and integration

    df_di = dis.di(
        df_bg,
        by=["STATE", "COUNTY", "TRACT"],
        over="BLOCK_GROUP",
    ).reset_index()

    # Infer the geographies

    gdf_di = ced.add_inferred_geography(df_di, year)

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
    parser.add_argument('-o', '--output', type=str, help="Output file.")

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
    if filename is None:
        filename = '-'

    if args.layer == 'states':
        save_state_bounds(year=args.year, epsg=args.epsg, filename=filename)
    elif args.layer == 'tracts':
        save_tract_bounds(year=args.year, epsg=args.epsg, filename=filename)


if __name__ == "__main__":
    main(sys.argv)