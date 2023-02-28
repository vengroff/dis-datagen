PYTHON = python3.9

LAYERS = boundaries tracts

CMAP = YlOrRd

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
RASTER_5_MAX_Y := 14

RASTER_4_MIN_X := 2
RASTER_4_MIN_Y := 5
RASTER_4_MAX_X := 5
RASTER_4_MAX_Y := 6

RASTER_3_MIN_X := 1
RASTER_3_MIN_Y := 2
RASTER_3_MAX_X := 2
RASTER_3_MAX_Y := 3

RASTER_2_MIN_X := 0
RASTER_2_MIN_Y := 1
RASTER_2_MAX_X := 1
RASTER_2_MAX_Y := 2

RASTER_Z := 2 3 4 5 6 7 8

FAVICON_SIZES := 512 270 192 180 32

ALL_STATES := $(shell $(PYTHON) -c \
	"from censusdis.states import ALL_STATES_DC_AND_PR; print('\n'.join(ALL_STATES_DC_AND_PR))")

GEN_DATA_DIR := ./build/gendata
DIST_ROOT := ./dist
RASTER_TILE_DIR := $(DIST_ROOT)/rastertiles
VECTOR_TILE_DIR := $(DIST_ROOT)/vectortiles

SITE_SRC := ./site-src

# The year to load data for.
YEAR := 2020

# This is the projection to use for our tiles.
EPSG := 4326

# How to invoke our python script to generate
# data for a layer.
GENDATA_PY := gendata.py
GENDATA := $(PYTHON) -m $(HE) $(basename $(GENDATA_PY))
GENDATA_FLAGS := -v -y $(YEAR) -e $(EPSG)

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


.PHONY: all vtiles rtiles data tracts site html favicon css js clean distclean

.PRECIOUS: $(GEN_DATA_DIR)/%.geojson


all: vtiles rtiles site

# Vector tiles in .pmtiles files.
vtiles: $(LAYERS:%=$(VECTOR_TILE_DIR)/%-$(YEAR).pmtiles)

# Raster tiles. Consider packaging up in .pmtiles as well.
rtiles: $(RASTER_Z:%=$(RASTER_TILE_DIR)/$(CMAP)/diversity/%) $(RASTER_Z:%=$(RASTER_TILE_DIR)/$(CMAP)/integration/%)

# Download all the raw data and do all the D and I computations.
tracts: $(GEN_DATA_DIR)/tracts-$(YEAR).geojson

data: tracts $(ALL_GEO_LAYER_FILES)

# The static site.
site: html favicon css js

html: $(DIST_ROOT)/index.html

favicon: $(FAVICON_SIZES:%=$(DIST_ROOT)/favicon%.png)

css: $(DIST_ROOT)/css/dimap.css

js: $(DIST_ROOT)/js/colors.js

clean:
	rm -rf $(GEN_DATA_DIR)

distclean: clean
	rm -rf $(DIST_ROOT)

$(DIST_ROOT)/%.html: $(SITE_SRC)/%.html
	mkdir -p $(dir $@)
	cp $< $@

$(DIST_ROOT)/favicon%.png: $(SITE_SRC)/favicon%.png
	mkdir -p $(dir $@)
	cp $< $@

$(DIST_ROOT)/css/%.css: $(SITE_SRC)/css/%.css
	mkdir -p $(dir $@)
	cp $< $@

$(DIST_ROOT)/js/%.js: $(SITE_SRC)/js/%.js
	mkdir -p $(dir $@)
	cp $< $@

$(GEN_DATA_DIR):
	mkdir -p $@

$(VECTOR_TILE_DIR):
	mkdir -p $@

# Generate geometry for tracts, including diversity
# and integration attributes.

# Rule to download for an individual state.
$(GEN_DATA_DIR)/tracts-$(YEAR)-%.geojson $(GEN_DATA_DIR)/tracts-$(YEAR)-%.csv:
	$(GENDATA) $(GENDATA_FLAGS) \
	-o $(GEN_DATA_DIR)/tracts-$(YEAR)-$*.geojson \
	-c $(GEN_DATA_DIR)/tracts-$(YEAR)-$*.csv \
	tracts \
	-s $*

# Once we have all the states we can put them together into one file.
$(GEN_DATA_DIR)/tracts-$(YEAR).geojson $(GEN_DATA_DIR)/tracts-$(YEAR).csv&: $(ALL_STATES:%=$(GEN_DATA_DIR)/tracts-$(YEAR)-%.geojson)
	$(PYTHON) -m catgeojson \
	-o $(GEN_DATA_DIR)/tracts-$(YEAR).geojson \
	-c $(GEN_DATA_DIR)/tracts-$(YEAR).csv \
	$^

# Rebuild if the script changes.
# $(GEN_DATA_DIR)/tracts-$(YEAR).geojson: $(GENDATA_PY)

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
$(VECTOR_TILE_DIR)/boundaries-$(YEAR).pmtiles: $(ALL_GEO_LAYER_FILES)
	mkdir -p $(dir $@)
	tippecanoe --force --drop-rate 0 -Z 2 -z 13 --projection=EPSG:$(EPSG) -o $@ $+

# Create a pmtiles file containing boundary layers.
$(VECTOR_TILE_DIR)/tracts-$(YEAR).pmtiles: $(GEN_DATA_DIR)/tracts-$(YEAR).geojson
	mkdir -p $(dir $@)
	tippecanoe --force --drop-rate 0 -Z 7 -z 13 --projection=EPSG:$(EPSG) -o $@ $+

# Raster tiles for a given zoom level.
$(RASTER_TILE_DIR)/$(CMAP)/diversity/% $(RASTER_TILE_DIR)/$(CMAP)/integration/% &: $(GEN_DATA_DIR)/tracts-$(YEAR).geojson
	$(RASTER_TILES) -v -z ${*} -o $(RASTER_TILE_DIR) \
		-x $(RASTER_${*}_MIN_X) \
		-X $(RASTER_${*}_MAX_X) \
		-y $(RASTER_${*}_MIN_Y) \
		-Y $(RASTER_${*}_MAX_Y) \
		-c $(CMAP) \
		$(GEN_DATA_DIR)/tracts-$(YEAR).geojson
	touch $(RASTER_TILE_DIR)/$(CMAP)/diversity/$* $(RASTER_TILE_DIR)/$(CMAP)/integration/$*
