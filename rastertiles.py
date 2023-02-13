
import argparse
import geopandas as gpd
from shapely.geometry import Polygon
import matplotlib.pyplot as plt

import pathlib

verbose = False

# See https://gis.stackexchange.com/questions/144471/spherical-mercator-world-bounds
EPSG_3857_X_MIN = -20037508.3427892
EPSG_3857_Y_MIN = -20037508.3427892
EPSG_3857_X_MAX = 20037508.3427892
EPSG_3857_Y_MAX = 20037508.3427892


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument('-v', '--verbose', action='store_true')

    parser.add_argument('-z', '--zoom-level', type=int, default=7)

    parser.add_argument('-x', "--min-x", type=int)
    parser.add_argument('-X', "--max-x", type=int)

    parser.add_argument('-y', "--min-y", type=int)
    parser.add_argument('-Y', "--max-y", type=int)

    parser.add_argument('-c', '--cmap', type=str, default='Greens')  # try also 'hot'

    parser.add_argument(
        '-t', '--total-population', default='B03002_001E', type=str,
        help='Total population variable, so we can check for empty tracts.'
    )

    parser.add_argument('-o', '--output-dir', type=str, required=True)

    parser.add_argument('input', type=str)

    args = parser.parse_args()

    global verbose

    verbose = args.verbose

    if verbose:
        print("Verbose mode on.")

    z = args.zoom_level
    min_x = args.min_x
    max_x = args.max_x
    min_y = args.min_y
    max_y = args.max_y

    meters_per_tile_x = (EPSG_3857_X_MAX - EPSG_3857_X_MIN) / (1 << z)
    meters_per_tile_y = (EPSG_3857_Y_MAX - EPSG_3857_Y_MIN) / (1 << z)

    if verbose:
        print(f"Zoom level: {z}")
        print(f"Meters per tile x: {meters_per_tile_x:.2f}")

    gdf = gpd.read_file(args.input)

    if verbose:
        print(f'Read {len(gdf.index)} rows from {args.input}.')

    gdf = gdf[~gdf.geometry.isnull()]

    if verbose:
        print(f'Reduced to {len(gdf.index)} rows by removing null geometries.')

    if verbose:
        print(f"{gdf.crs} total bounds of input: {gdf.geometry.total_bounds}")

    # This is the projection that tiles are rendered in.
    original_crs = gdf.crs
    gdf = gdf.to_crs(epsg=3857)

    if verbose:
        print(f"epsg:3857 total bounds of input: {gdf.geometry.total_bounds}")

    for x in range(min_x, max_x + 1, 1):
        for y in range(min_y, max_y + 1, 1):
            if verbose:
                print(f"Processing {z}/{x}/{y}.")

            x_lim_3857 = (
                             EPSG_3857_X_MIN + x * meters_per_tile_x,
                             EPSG_3857_X_MIN + (x + 1) * meters_per_tile_x
            )
            y_lim_3857 = (
                EPSG_3857_Y_MAX - (y + 1) * meters_per_tile_y,
                EPSG_3857_Y_MAX - y * meters_per_tile_y
            )

            if verbose:
                print(
                    "Tile bounds in epsg:3857: "
                    f"({x_lim_3857[0]:.2f}, {y_lim_3857[0]:.2f}, "
                    f"{x_lim_3857[1]:.2f}, {y_lim_3857[1]:.2f})"
                )

            gs_tile = gpd.GeoSeries(
                [
                    Polygon([
                        (x_lim_3857[0], y_lim_3857[0]),
                        (x_lim_3857[0], y_lim_3857[1]),
                        (x_lim_3857[1], y_lim_3857[1]),
                        (x_lim_3857[1], y_lim_3857[0]),
                        (x_lim_3857[0], y_lim_3857[0]),
                    ])
                ],
            ).set_crs(epsg=3857).to_crs(original_crs)

            if verbose:
                print(f"Tile bounds in {gs_tile.crs}: {gs_tile.iloc[0]}")

            gdf_clipped = gdf.cx[x_lim_3857[0]:x_lim_3857[1], y_lim_3857[0]:y_lim_3857[1]]

            if verbose:
                print(f"EPSG:3857 bounds of input clipped to tile: {gdf_clipped.geometry.total_bounds}")

            if len(gdf_clipped.index) > 0:
                # Otherwise we clipped in all, so no need for a tile.

                plot_vars = [
                    'diversity', 'integration'
                ]

                for plot_var in plot_vars:
                    ax = gdf_clipped.plot(
                        plot_var,
                        cmap=args.cmap,
                        legend=False,
                        figsize=(256 / 64, 256 / 64),
                        vmin=0.0,
                        vmax=0.8,
                    )

                    # Grey out empty tracts.
                    gdf_clipped_empty = gdf_clipped[gdf_clipped[args.total_population] == 0]

                    if len(gdf_clipped_empty.index) > 0:
                        ax = gdf_clipped_empty.plot(
                            color='#C0C0C0',
                            legend=False,
                            figsize=(256 / 64, 256 / 64),
                            ax=ax,
                        )

                    ax.set_xlim(x_lim_3857[0], x_lim_3857[1])
                    ax.set_ylim(y_lim_3857[0], y_lim_3857[1])

                    ax.tick_params(
                        left=False,
                        right=False,
                        bottom=False,
                        labelleft=False,
                        labelbottom=False,
                    )

                    ax.axis('off')

                    tile_dir = pathlib.Path(args.output_dir) / args.cmap / plot_var / f'{z}' / f'{x}'
                    tile_dir.mkdir(parents=True, exist_ok=True)
                    tile_file = tile_dir / f'{y}.png'

                    if verbose:
                        print(f"Saving to {tile_file}.")

                    plt.savefig(tile_file, bbox_inches='tight', pad_inches=0.0, dpi=64)

                    plt.close()


if __name__ == "__main__":
    main()
