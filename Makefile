PYTHON = python3.9

LAYERS = states tracts

MIN_ZOOM_states-2020 := 2
MAX_ZOOM_states-2020 := 10

MIN_ZOOM_tracts-2020 := 7
MAX_ZOOM_tracts-2020 := 16

MIN_ZOOM_cities := 4
MAX_ZOOM_cities := 13

RASTER_8_MIN_X := 38
RASTER_8_MIN_Y := 86
RASTER_8_MAX_X := 80
RASTER_8_MAX_Y := 110

RASTER_7_MIN_X := 19
RASTER_7_MIN_Y := 43
RASTER_7_MAX_X := 40
RASTER_7_MAX_Y := 55

RASTER_6_MIN_X := 9
RASTER_6_MIN_Y := 21
RASTER_6_MAX_X := 20
RASTER_6_MAX_Y := 27

RASTER_5_MIN_X := 4
RASTER_5_MIN_Y := 10
RASTER_5_MAX_X := 11
RASTER_5_MAX_Y := 13

RASTER_4_MIN_X := 2
RASTER_4_MIN_Y := 5
RASTER_4_MAX_X := 4
RASTER_4_MAX_Y := 6

RASTER_3_MIN_X := 1
RASTER_3_MIN_Y := 2
RASTER_3_MAX_X := 2
RASTER_3_MAX_Y := 3

RASTER_Z := 3 4 5 6 7 8


GEN_DATA_DIR = ./build/gendata
RASTER_TILE_DIR = ./build/rastertiles

# The year to load data for.
YEAR := 2020

# This is the projection to use for our tiles.
EPSG := 4326

# How to invoke our python script to generate
# data for a layer.
GENDATA := $(PYTHON) -m gendata
GENDATA_FLAGS := -y $(YEAR) -e $(EPSG)

RASTER_TILES := $(PYTHON) -m rastertiles

.PHONY: all clean

.PRECIOUS: $(GEN_DATA_DIR)/%.geojson

# Use our python script to download census data
# and generate a geojson for a given layer.
$(GEN_DATA_DIR)/%-$(YEAR).geojson: $(GEN_DATA_DIR)
	$(GENDATA) $(GENDATA_FLAGS) -o $@ $*

# Convert a geojson file to a pmtiles file using
# tippecanoe.
$(GEN_DATA_DIR)/%.pmtiles: $(GEN_DATA_DIR)/%.geojson
	tippecanoe --force -Z$(MIN_ZOOM_$*) -z$(MAX_ZOOM_$*) --projection=EPSG:$(EPSG) -l $* -o $@ $<

# Raster tiles for a given zoom level.
$(RASTER_TILE_DIR)/%: $(GEN_DATA_DIR)/tracts-$(YEAR).geojson
	$(RASTER_TILES) -v -z ${*} -o $(RASTER_TILE_DIR) \
		-x $(RASTER_${*}_MIN_X) \
		-X $(RASTER_${*}_MAX_X) \
		-y $(RASTER_${*}_MIN_Y) \
		-Y $(RASTER_${*}_MAX_Y) \
		$(GEN_DATA_DIR)/tracts-$(YEAR).geojson

$(GEN_DATA_DIR)/cities:
	$(PYTHON) -m cities -e 4326 $@

$(GEN_DATA_DIR)/cities.pmtiles: $(GEN_DATA_DIR)/cities
	tippecanoe --force -Z$(MIN_ZOOM_cities) -z$(MAX_ZOOM_cities) --projection=EPSG:$(EPSG) \
		-o $@ \
		$</cities-10.geojson \
		$</cities-9.geojson \
		$</cities-8.geojson \
		$</cities-7.geojson \
		$</cities-6.geojson

all: $(LAYERS:%=$(GEN_DATA_DIR)/%-$(YEAR).pmtiles)

clean:
	rm -rf $(GEN_DATA_DIR)

$(GEN_DATA_DIR):
	mkdir -p $@
