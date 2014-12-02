#$L$
# Copyright (C) 2013 Ridgerun (http://www.ridgerun.com). 
##$L$

PKG_URL=http://www.kernel.org/pub/linux/utils/kernel/hotplug/
PKG_TARBALL=udev-182.tar.xz
PKG_SHA1SUM=ad226ca222ada889621aae9bdb50fb6e90e77fd9

AUTOTOOLS_PARAMS=\
  --prefix=/usr \
  --sysconfdir=/etc \
  --exec-prefix=/usr \
  --with-usb-ids-path=no \
  --with-pci-ids-path=no \
  --disable-gtk-doc-html \
  --disable-introspection \
  --disable-manpages \
  --disable-keymap \
  --disable-extras \
  --with-firmware-path=lib/firmware/updates:lib/firmware

DESTDIR=$(FSDEVROOT)

CORRECT_LA=/usr/lib/{libgudev-1.0.la,libudev.la}	
CORRECT_PKGCONFIG=/usr/lib/pkgconfig/{libudev.pc,gudev-1.0.pc}

BINARIES = /usr/libexec/udev/udevd /usr/bin/udevadm
LIBRARIES = /usr/lib/{libudev.so.0.13.1,libgudev-1.0.so.0.1.1}
EXTRA_FILES = /etc/udev
OTHERS= /usr/libexec/udev/rules.d/{60-persistent-storage.rules,85-i2c.rules,42-usb-hid-pm.rules,50-udev-default.rules,60-persistent-alsa.rules,60-persistent-input.rules,60-persistent-serial.rules,60-persistent-storage-tape.rules,75-net-description.rules,75-tty-description.rules,78-sound-card.rules,80-drivers.rules,95-udev-late.rules}

INIT_SCRIPT=udev.init
INIT_SCRIPT_DEPENDENCIES=mountall
INIT_SCRIPT_LEVEL=99

include ../../../bsp/classes/rrsdk.class
include $(CLASSES)/autotools.class
