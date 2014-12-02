#$L$
# Copyright (C) 2013 Ridgerun (http://www.ridgerun.com). 
#$L$

PKG_URL=http://www.saddi.com/software/flup/dist/
PKG_TARBALL=flup-1.0.2.tar.gz
PKG_SHA1SUM=29cec06ee28f44b8d6713f4da3d5b793eba6cf21

FETCHER_EXTRACT_DIRECTORY_NAME=src

PYTHON_PKG=flup
PYTHON_PKG_FILES=$(PYTHON_PKG)/*

include ../../../bsp/classes/rrsdk.class
include $(CLASSES)/python.class


build: python_install

unpatch:

uninstall:
	$(V) rm -rf $(PYTHON_SITE_PACKAGES)/flup
