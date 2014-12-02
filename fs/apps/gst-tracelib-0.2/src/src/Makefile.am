module_LTLIBRARIES = libgsttracelib.la
moduledir = $(libdir)/gst-tracelib

libgsttracelib_la_SOURCES = gsttracelib.c
libgsttracelib_la_LIBADD = $(BASE_DEPS_LIBS)
libgsttracelib_la_CFLAGS = $(BASE_DEPS_CFLAGS)
libgsttracelib_la_LDFLAGS = -module -avoid-version
libgsttracelib_la_LIBTOOLFLAGS = --tag=disable-static

dist_bin_SCRIPTS = gsttl gsttl_splitlog.py gsttl_plot.sh

EXTRA_DIST = gsttl.in

