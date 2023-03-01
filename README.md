# dis-datagen

This project contains the code used to generate
an interactive map of [Diversity and Integration
in the United States](http://di-map.datapinions.com/).

For more about this map, see this 
[essay](https://datapinions.com/diversity-and-integration-in-america-an-interactive-visualization/)
about it.

To use this project to build the data and site, first we need to clone and enter the 
repository using 

```shell
git clone https://github.com/vengroff/dis-datagen.git
cd dis-datagen
```
Next, we use [poetry](https://python-poetry.org/) to create a virtual
environment containing all of our dependencies. If you don't have poetry
you will need to install it before proceeding. Details can be found 
[here](https://python-poetry.org/docs/#installation).

Once poetry itself is installed, you can use it to install all of our
dependencies. Do this with the shell command

```shell
poetry install
```

Finally, we need to run `gmake` in the virtual environment with all of
our dependencies. To do this, run

```shell
poetry run gmake -j 4
```

I use `-j 4` because that way data from four states at a time will be downloaded
and processed in parallel. You can adjust this number up or down depending on how
many cores you have available to devote to this.

Once you have done this, you should have a new directory `dist` containing the full
static web site, map tiles and data.

## A Note on Census Keys

Given the volume of data downloaded in a short time, the U.S. Census API may cut 
you off if you don't have a key. You can request a key [here](https://api.census.gov/data/key_signup.html).
Once you have received the key by email, put it in a one-line text file at `~/.censusdis/api_key.txt`. 
Once you have done this, the `censusdis` API that we use will use that key in all requests
to the U.S. Census servers and you should have no further problems with access.
