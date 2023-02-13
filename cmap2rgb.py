
import argparse
import matplotlib as mpl
from matplotlib.colors import LinearSegmentedColormap
import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--cmap', type=str, default='YlGn')

    args = parser.parse_args()

    print(f"const {args.cmap} = new Colormap('{args.cmap}',\n[")

    cmap = mpl.colormaps[args.cmap]

    if isinstance(cmap, LinearSegmentedColormap):
        for x in np.linspace(0.0, 1.0, 255):
            r, g, b, _ = cmap(x)
            r255 = int(r * 255)
            g255 = int(g * 255)
            b255 = int(b * 255)
            print(f'  "rgb({r255} {g255} {b255})",')
    else:
        for r, g, b in cmap.colors:
            r255 = int(r * 255)
            g255 = int(g * 255)
            b255 = int(b * 255)
            print(f'  "rgb({r255} {g255} {b255})",')

    print("]);")


if __name__ == "__main__":
    main()
