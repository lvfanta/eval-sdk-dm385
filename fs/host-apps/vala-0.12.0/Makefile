#$L$
# Copyright (C) 2011 Ridgerun (http://www.ridgerun.com).
#$L$

PKG_VERSION=0.12.0
PKG_URL=http://download.gnome.org/sources/vala/0.12/
PKG_TARBALL=vala-0.12.0.tar.bz2
PKG_SHA1SUM=3799a1cdda63b40b7aa031bca7da6bf1baf000b1

include ../../../bsp/classes/rrsdk_local.class
include $(CLASSES)/autotools_local.class

AUTOTOOLS_BUILD_DIR=$(HOST_ARCH)
AUTOTOOLS_PARAMS+=--prefix=$(LOCALDIR)
AUTOTOOLS_HOST=
CONFIG_SITE=

# Extra build steps, need to be defined after including autotools.class
# to have the right order
build:: $(DEVDIR)/fs/config.site.d/vala-$(PKG_VERSION)-host

$(DEVDIR)/fs/config.site.d/vala-$(PKG_VERSION)-host:
	$(V) echo "test -z \"\$$VAPIDIR\" && VAPIDIR=\"$(DEVDIR)/bsp/local/share/vala-0.12/vapi\"" > $@
	$(V) $(MAKE) -C $(DEVDIR)/fs config.site

