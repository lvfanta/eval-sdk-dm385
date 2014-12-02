#$L$
# Copyright (C) 2014 Ridgerun
##$L$

PKG_URL=http://directfb.org/downloads/Core/DirectFB-1.7
PKG_TARBALL=DirectFB-1.7.1.tar.gz
PKG_SHA1SUM=ff3dc6885f2875586849d88ee9f87fca866259b0

include ../../../bsp/classes/rrsdk.class

BINARIES= /usr/bin/{dfbg,dfbinspector}
LIBRARIES = /usr/lib/{libfusion-1.7.so.1.0.0,libdirectfb-1.7.so.1.0.0,libdirect-1.7.so.1.0.0}
LIBRARIES_OPTIONAL = /usr/lib/directfb-1.7-1/{inputdrivers/libdirectfb_linux_input.so,interfaces/IDirectFBFont/{libidirectfbfont_dgiff.so,libidirectfbfont_ft2.so},interfaces/IDirectFBImageProvider/{libidirectfbimageprovider_dfiff.so,libidirectfbimageprovider_gif.so,libidirectfbimageprovider_jpeg.so,libidirectfbimageprovider_png.so},interfaces/IDirectFBVideoProvider/libidirectfbvideoprovider_gif.so,systems/{libdirectfb_devmem.so,libdirectfb_dummy.so,libdirectfb_fbdev.so},wm/libdirectfbwm_default.so}

AUTOTOOLS_BUILD_DIR=$(AUTOTOOLS_SRC_DIR)
DESTDIR=$(FSDEVROOT)
AUTOTOOLS_PARAMS = --prefix=/usr --with-inputdrivers="linuxinput tslib" --enable-png --with-gfxdrivers=none --enable-zlib \
--enable-shared --disable-debug --disable-video4linux --disable-vnc  --disable-osx --with-tests LDFLAGS="$(APPS_LDFLAGS)" CFLAGS="$(APPS_CFLAGS)"
AUTOTOOLS_CORRECT_LA_SED_EXPRESSION?=s?libdir='/usr?libdir='$(FSDEVROOT)/usr?g;\
        s?\ /usr/lib?\ $(FSDEVROOT)//usr/lib?g
AUTOTOOLS_CORRECT_LA=/usr/lib/{libfusion.la,libdirectfb.la,libdirect.la}
AUTOTOOLS_CORRECT_PKGCONFIG=/usr/lib/pkgconfig/{direct.pc,directfb-internal.pc,directfb.pc,fusion.pc}

APPS_LDFLAGS+=-Wl,--rpath-link -Wl,$(FSDEVROOT)/usr/lib -lm
APPS_CFLAGS+="-D_GNU_SOURCE"

ifeq ($(CONFIG_FS_APPS_DIRECTFB_FREETYPE),y)
 AUTOTOOLS_PARAMS+=--enable-freetype FREETYPE_CONFIG="$(FSDEVROOT)/usr/bin/freetype-config"
else
 AUTOTOOLS_PARAMS+=--disable-freetype
endif

ifeq ($(CONFIG_FS_APPS_DIRECTFB_JPEG),y)
AUTOTOOLS_PARAMS+=--enable-jpeg
else
AUTOTOOLS_PARAMS+=--disable-jpeg
endif

ifeq ($(MAKECMDGOALS),sim)
AUTOTOOLS_PARAMS += --enable-x11 --disable-fbdev
else
AUTOTOOLS_PARAMS += --disable-x11 --enable-fbdev
endif

include $(CLASSES)/autotools.class

# Post install fixes
install::
	$(V)sed -i 's?prefix=/usr?prefix=$(FSDEVROOT)/usr?' $(FSDEVROOT)/usr/bin/directfb-config
