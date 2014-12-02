#$L$
# Copyright (C) 2012-2013 Ridgerun (http://www.ridgerun.com). 
##$L$

PKG_URL=http://gstreamer.freedesktop.org/src/gst-python/
PKG_TARBALL=gst-python-0.10.22.tar.bz2
PKG_SHA1SUM=7012445d921ae1b325c162500750c9b0e777201f

DESTDIR=$(FSDEVROOT)
CORRECT_PKGCONFIG=/usr/lib/pkgconfig/gst-python-0.10.pc
CORRECT_LA=/usr/lib/python2.7/site-packages/gstoption.la /usr/lib/python2.7/site-packages/gst-0.10/gst/interfaces.la /usr/lib/gstreamer-0.10/libgstpython.la

AUTOTOOLS_PARAMS=--build=$(HOST_ARCH) --enable-shared --prefix=/usr PYGOBJECT_CFLAGS=-I$(FSDEVROOT)/usr/include/pygtk-2.0 PYTHON_INCLUDES=-I$(FSDEVROOT)/usr/include/python$(PYTHON_VERSION) --with-libpython-dir=/usr/lib/ --with-sysroot=/usr/lib/

ifeq ($(TOOLCHAIN),linaro-4.7.1)
OTHERS=/usr/include/gstreamer-0.10/gst/{pygst.h,pygstexception.h,pygstminiobject.h,pygstvalue.h} /usr/lib/python${PYTHON_VERSION}/dist-packages/pygst.pth 
LIBRARIES=/usr/lib/gstreamer-0.10/libgstpython.so /usr/lib/python${PYTHON_VERSION}/dist-packages/{gst-0.10/gst/{audio,interfaces,pbutils,video,tag,_gst}.so,gstoption.so}
 20 LIBRARIES_OPTIONAL=$(shell find $(FSDEVROOT)/usr/lib/python${PYTHON_VERSION}/dist-packages -type f -name '*.p    yo' -or -name pygst.py | sed 's!.*fsdev!!')
else
OTHERS=/usr/include/gstreamer-0.10/gst/{pygst.h,pygstexception.h,pygstminiobject.h,pygstvalue.h} /usr/lib/python${PYTHON_VERSION}/site-packages/pygst.pth 
LIBRARIES=/usr/lib/gstreamer-0.10/libgstpython.so /usr/lib/python${PYTHON_VERSION}/site-packages/{gst-0.10/gst/{audio,interfaces,pbutils,video,tag,_gst}.so,gstoption.so}
LIBRARIES_OPTIONAL=$(shell find $(FSDEVROOT)/usr/lib/python${PYTHON_VERSION}/site-packages -type f -name '*.pyo' -or -name pygst.py | sed 's!.*fsdev!!')
endif

include ../../../bsp/classes/rrsdk.class
include $(CLASSES)/autotools.class

