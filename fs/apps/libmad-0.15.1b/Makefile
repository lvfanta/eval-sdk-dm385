#$L$
# Copyright (C) 2011 Ridgerun (http://www.ridgerun.com). 
##$L$

PKG_URL=ftp://ftp.mars.org/pub/mpeg/
PKG_TARBALL=libmad-0.15.1b.tar.gz
PKG_SHA1SUM=cac19cd00e1a907f3150cc040ccc077783496d76

include $(DEVDIR)/bsp/mach/Make.conf

LIBRARIES = /usr/lib/libmad.so.0.2.1

# libmad needs arm instruction set to compile
ifeq ($(TOOLCHAIN),linaro)
AUTOTOOLS_PARAMS+=CFLAGS="$(CFLAGS) -marm"
endif

include ../../../bsp/classes/rrsdk.class
include $(CLASSES)/autotools.class

