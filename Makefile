PYTHON = python3.9

LAYERS = boundaries tracts

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
RASTER_4_MAX_X := 5
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

CITY_GEO_LAYER_FILES := \
	$(GEN_DATA_DIR)/cities-10.geojson \
	$(GEN_DATA_DIR)/cities-9.geojson \
	$(GEN_DATA_DIR)/cities-8.geojson \
	$(GEN_DATA_DIR)/cities-7.geojson \
	$(GEN_DATA_DIR)/cities-6.geojson

STATE_GEO_LAYER_FILES := \
	$(GEN_DATA_DIR)/states-$(YEAR).geojson \
	$(GEN_DATA_DIR)/states-rep-$(YEAR).geojson

ALL_GEO_LAYER_FILES := $(STATE_GEO_LAYER_FILES) $(CITY_GEO_LAYER_FILES)


.PHONY: all clean

.PRECIOUS: $(GEN_DATA_DIR)/%.geojson

# Generate geometry for tracts, including diversity
# and integration attributes.
$(GEN_DATA_DIR)/tracts-$(YEAR).geojson: $(GEN_DATA_DIR)
	$(GENDATA) $(GENDATA_FLAGS) -o $@ tracts

# Generate state bounds and representative points.
$(STATE_GEO_LAYER_FILES) &: $(GEN_DATA_DIR)
	$(GENDATA) $(GENDATA_FLAGS) \
		-o $(GEN_DATA_DIR)/states-$(YEAR).geojson \
		-r $(GEN_DATA_DIR)/states-rep-$(YEAR).geojson states

# Generate city representation points.
$(CITY_GEO_LAYER_FILES) &:
	$(PYTHON) -m cities -e 4326 $(GEN_DATA_DIR)

# Convert a geojson file to a pmtiles file using
# tippecanoe.
# $(GEN_DATA_DIR)/%.pmtiles: $(GEN_DATA_DIR)/%.geojson
# 	tippecanoe --force -Z$(MIN_ZOOM_$*) -z$(MAX_ZOOM_$*) --projection=EPSG:$(EPSG) -l $* -o $@ $<

# Create a pmtiles file containing geometry layers.
$(GEN_DATA_DIR)/boundaries-$(YEAR).pmtiles: $(ALL_GEO_LAYER_FILES)
	tippecanoe --force --drop-rate 0 -Z 2 -z 13 --projection=EPSG:$(EPSG) -o $@ $+

# Raster tiles for a given zoom level.
$(RASTER_TILE_DIR)/%: $(GEN_DATA_DIR)/tracts-$(YEAR).geojson
	$(RASTER_TILES) -v -z ${*} -o $(RASTER_TILE_DIR) \
		-x $(RASTER_${*}_MIN_X) \
		-X $(RASTER_${*}_MAX_X) \
		-y $(RASTER_${*}_MIN_Y) \
		-Y $(RASTER_${*}_MAX_Y) \
		$(GEN_DATA_DIR)/tracts-$(YEAR).geojson

all: $(LAYERS:%=$(GEN_DATA_DIR)/%-$(YEAR).pmtiles)

clean:
	rm -rf $(GEN_DATA_DIR)

$(GEN_DATA_DIR):
	mkdir -p $@
