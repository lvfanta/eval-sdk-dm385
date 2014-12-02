#$L$
# Copyright (C) 2014 Ridgerun (http://www.ridgerun.com). 
##$L$

PKG_URL=https://bitbucket.org/libgd/gd-libgd/downloads
PKG_TARBALL=libgd-2.1.0.tar.gz
PKG_SHA1SUM=a0f3053724403aef9e126f4aa5c662573e5836cd

include ../../../bsp/classes/rrsdk.defs

LIBRARIES = /usr/lib/libgd.so.3.0.0

AUTOTOOLS_PARAMS = --enable-shared \
	--with-png \
	--with-zlib \
	LDFLAGS="$(APPS_LDFLAGS)" CFLAGS="$(APPS_CFLAGS)"

APPS_LDFLAGS+=-Wl,--rpath-link -Wl,$(FSDEVROOT)/usr/lib -lm

ifeq ($(CONFIG_FS_APPS_LIBGD_FREETYPE),y)
 AUTOTOOLS_PARAMS+=--with-freetype FREETYPE_CONFIG="$(FSDEVROOT)/usr/bin/freetype-config"
else
 AUTOTOOLS_PARAMS+=--without-freetype
endif

ifeq ($(CONFIG_FS_APPS_LIBGD_JPEG),y)
AUTOTOOLS_PARAMS+=--with-jpeg
else
AUTOTOOLS_PARAMS+=--without-jpeg
endif

ifeq ($(MAKECMDGOALS),sim)
AUTOTOOLS_PARAMS += --with-x \
	--with-xmp \
	--with-fontconfig
else
AUTOTOOLS_PARAMS += --without-x \
	--without-xmp \
	--without-fontconfig
endif

include $(CLASSES)/autotools.class

