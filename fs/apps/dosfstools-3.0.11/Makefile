#$L$
# Copyright (C) 2011 Ridgerun (http://www.ridgerun.com)
##$L$

PKG_URL=http://dosfstools.sourcearchive.com/downloads/3.0.11-1/
PKG_TARBALL=dosfstools_3.0.11.orig.tar.gz
PKG_SHA1SUM=29dc6fc65619fc2f45849d249a6d9c6fa20937ec

BINARIES= /usr/local/sbin/{mkdosfs,dosfsck,dosfslabel}
LINKS=	/usr/local/sbin/{fsck.msdos,fsck.vfat,mkfs.msdos,mkfs.vfat}

CFLAGS += -D_FILE_OFFSET_BITS=64

include ../../../bsp/classes/rrsdk.class

FETCHER_EXTRACT_DIRECTORY_NAME=src
build: rrfetched $(BUILT_FLAG)

$(BUILT_FLAG): 
	$(V) $(MAKE) -C src $(TOOLCHAIN_ENVIRONMENT) $(QOUT)
	$(V) touch $@

$(INSTALLED_FLAG):
	$(V) $(MAKE) -C src DESTDIR=$(FSDEVROOT) install $(QOUT)
	$(V) touch $@

install: $(INSTALLED_FLAG) rrsdk_install 

uninstall:

clean:
	$(V) if [ -d src ] ; then \
		 $(MAKE) -C src clean $(TOOLCHAIN_ENVIRONMENT) $(QOUT) ; \
	fi ; 
	$(V) rm -Rf $(INSTALLED_FLAG) $(BUILT_FLAG)

distclean: clean rrfetched_clean


include $(CLASSES)/fetcher.defs
include $(CLASSES)/flags.defs
