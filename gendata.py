
import argparse
import sys
from typing import Iterable, Optional

import censusdis.data as ced
import censusdis.maps as cem
import divintseg as dis
import pandas as pd
import geopandas as gpd
import numpy as np
from censusdis.states import ALL_STATES_DC_AND_PR, STATE_NAMES_FROM_IDS
from censusdis.states import STATE_AK, STATE_WY, STATE_NY, STATE_NJ, STATE_CT

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


def hl_variable(variable: str) -> str:
    """
    Convert to hispanic or latino variable name.

    Parameters
    ----------
    variable
        Original variable name.
    Returns
    -------
        Name of derived variable we will use for non-Hispanic or
        Latino version of the concept measured by this variable.
    """
    if not variable.startswith("P1_"):
        raise ValueError("Must be a P1 variable.")

    # See https://api.census.gov/data/2020/dec/pl/groups/P1.html
    # and https://api.census.gov/data/2020/dec/pl/groups/P2.html.
    var_num = int(variable[-4:-1])
    var_num = var_num + 2

    return f'hl_{var_num:03d}N'


def nhl_variable_for_hl_variable(hl_var: str) -> str:
    if not hl_var.startswith('hl_'):
        raise ValueError("Must be an hl variable.")

    return hl_var.replace("hl_", "P2_")


def all_state_data(year: int, group1: str, group2: str, total_col: str):
    """Generate all the state data, one data frame per state."""
    for state in [STATE_WY, STATE_AK]:  # ALL_STATES_DC_AND_PR:
        if verbose:
            print(f"Processing {STATE_NAMES_FROM_IDS[state]}")

        # If we load all the variables at once across
        # both groups the server side sometimes has issues.
        # So we download the groups separately and then merge.
        if verbose:
            print(f"Downloading {group1}")

        df_block_for_state_group1 = ced.download(
            DATASET,
            year,
            leaves_of_group=group1,
            state=state,
            block="*",
        )

        if verbose:
            print(f"Downloading {group2}")

        df_block_for_state_group2 = ced.download(
            DATASET,
            year,
            [total_col],
            leaves_of_group=group2,
            state=state,
            block="*",
        )

        df_block_for_state = df_block_for_state_group2.merge(
            df_block_for_state_group1,
            on=["STATE", "COUNTY", "TRACT", "BLOCK"],
        )

        if verbose:
            print(f"Downladed {len(df_block_for_state.index)} rows.")

        group1_leaves = [var for var in df_block_for_state.columns if var.startswith(group1)]

        # Compute the NHL version of each leaf.
        for var in group1_leaves:
            hl_var = hl_variable(var)
            nhl_var = nhl_variable_for_hl_variable(hl_var)

            df_block_for_state[hl_var] = df_block_for_state[var] - df_block_for_state[nhl_var]

        df_block_for_state = df_block_for_state.drop(group1_leaves, axis='columns')

        hl_leaves = [var for var in df_block_for_state.columns if var.startswith('hl')]
        nhl_leaves = [nhl_variable_for_hl_variable(var) for var in hl_leaves]

        total_hl_and_non_hl = df_block_for_state[hl_leaves + nhl_leaves].sum(axis='columns')
        if not (df_block_for_state[total_col].equals(total_hl_and_non_hl)):
            raise ValueError(
                "These values should be the same! "
                "Something went wrong in computing race counts for Hispanic or Latino population."
            )

        yield df_block_for_state


# From https://github.com/vengroff/censusdis/blob/main/notebooks/Nationwide%20Diversity%20and%20Integration.ipynb
def tract_bounds(year: int, epsg: int) -> gpd.GeoDataFrame:

    group1 = "P1"
    group2 = "P2"
    total_col = f'{group2}_001N'
    hl_col_in_group2 = f'{group2}_002N'

    # Download the data

    # If we try to bulk download all states at once we
    # get a 500 from the API with the error, "There was
    # an error while running your query.  We've logged
    # the error and we'll correct it ASAP.  Sorry for
    # the inconvenience." So go state by state and
    # concat them.
    df_block = pd.concat(all_state_data(year, group1, group2, total_col))

    if verbose:
        print(f"Downloaded a total of {len(df_block.index)} rows.")

    leaf_cols = [
        col for col in df_block.columns
        if col.startswith(group2) and col not in [total_col, hl_col_in_group2] or col.startswith('hl')
    ]

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