# Copyright (C) 2014 RidgeRun, LLC (http://www.ridgerun.com)

FETCHER_NO_DOWNLOAD=yes
FETCHER_EXTRACT_DIRECTORY_NAME=src
NETCAM_DIR=$(FSROOT)/usr/share/netcam

INIT_SCRIPT=netcam.init
INIT_SCRIPT_LEVEL=85

build: verify

install: rrsdk_install
	$(V) mkdir -p $(NETCAM_DIR) 
	$(V) mkdir -p $(NETCAM_DIR)/{templates,static}
	$(V) rm -f $(NETCAM_DIR)/*.{pyo,pyc,py}
ifeq ($(CONFIG_USER_APPS_NETCAM_USE_PYTHON_SOURCE),y)
	$(V) rm -f $(NETCAM_DIR)/*.pyo
	$(V) cp src/*.py $(NETCAM_DIR)
else
	$(V) python -O -m compileall -d src src
	$(V) cp src/*.pyo $(NETCAM_DIR)
endif
	$(V) cp src/*.fcgi $(NETCAM_DIR)
	$(V) cp src/pipelines.gst $(NETCAM_DIR)
	$(V) cp -r src/templates/* $(NETCAM_DIR)/templates

verify:
	python -O -m compileall -d src src

clean:
	$(V) rm -f *~ src/*.pyo src/*~ src/templates/*~ src/*.pyc

distclean: clean
	$(V) rm -rf fetcher_verified src

include ../../bsp/classes/rrsdk.class
