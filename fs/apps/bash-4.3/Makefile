#$L$
# Copyright (C) 2014 Ridgerun (http://www.ridgerun.com). 
##$L$

PKG_URL=http://ftp.gnu.org/gnu/bash/
PKG_TARBALL=bash-4.3.tar.gz
PKG_SHA1SUM=45ac3c5727e7262334f4dfadecdf601b39434e84

AUTOTOOLS_PARAMS = --disable-nls --prefix=/usr
DESTDIR=$(FSDEVROOT)

BINARIES= /usr/bin/{bash,bashbug}
FETCHER_EXTRACT_DIRECTORY_NAME=src

include ../../../bsp/classes/rrsdk.class
include $(CLASSES)/autotools.class
