#$L$
# Copyright (C) 2007 Ridgerun (http://www.ridgerun.com). 
#
#  This source code has a dual license.  If this file is linked with other
#  source code that has a GPL license, then this file is licensed with a GPL
#  license as described below.  Otherwise the source code contained in this
#  file is property of Ridgerun. This source code is protected under
#  copyright law.
#
#  This program is free software; you can redistribute  it and/or modify it
#  under  the terms of  the GNU General  Public License as published by the
#  Free Software Foundation;  either version 2 of the  License, or (at your
#  option) any later version.
#
#  THIS  SOFTWARE  IS  PROVIDED  ``AS  IS''  AND   ANY  EXPRESS  OR IMPLIED
#  WARRANTIES,   INCLUDING, BUT NOT  LIMITED  TO, THE IMPLIED WARRANTIES OF
#  MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.  IN
#  NO  EVENT  SHALL   THE AUTHOR  BE    LIABLE FOR ANY   DIRECT,  INDIRECT,
#  INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
#  NOT LIMITED   TO, PROCUREMENT OF  SUBSTITUTE GOODS  OR SERVICES; LOSS OF
#  USE, DATA,  OR PROFITS; OR  BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
#  ANY THEORY OF LIABILITY, WHETHER IN  CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
#  THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#  You should have received a copy of the  GNU General Public License along
#  with this program; if not, write  to the Free Software Foundation, Inc.,
#  675 Mass Ave, Cambridge, MA 02139, USA.
#$L$

.PHONY: build chkconfig preconfig buildfs install clean
ifeq ($(DEVDIR),)
$(error ====== DEVDIR variable is empty, invoke this Makefile from the BSP root, or provide the path to it =====)
endif
include $(DEVDIR)/bsp/mach/Make.conf
include $(DEVDIR)/fs/Apps.defs

AUTOTOOLS=ACLOCAL=true AUTOCONF=true AUTOMAKE=true AUTOHEADER=true

CPPFLAGS="-I$(EXPAT_INCLUDE)/"
LDFLAGS="-L$(EXPAT_LIB) -lexpat"

build: .configured
ifeq ($(CONFIG_FS_APPS_AVAHI),y)
	$(V) $(MAKE) -C src $(AUTOTOOLS) $(TOOLCHAIN_ENVIRONMENT) $(QOUT)
endif

.configured:
ifeq ($(CONFIG_FS_APPS_AVAHI),y)
	$(V) cd src && \
        rm -rf config.cache && \
        export $(EXPORT_TOOLCHAIN_ENVIRONMENT) && \
        PKG_CONFIG_PATH=$(LIBDAEMON_LIB):$(PKG_CONFIG_PATH) \
        CPPFLAGS=$(CPPFLAGS) \
        LDFLAGS=$(LDFLAGS) \
	LIBDAEMON_CFLAGS="-I$(LIBDAEMON)/Output/include" \
	LIBDAEMON_LIBS="-L$(LIBDAEMON_LIB) -ldaemon" \
	ac_cv_func_malloc_0_nonnull=yes \
	ac_cv_func_realloc_0_nonnull=yes \
        ./configure \
        --build=i686-gnu-linux \
        --host=$(ARCH)-linux \
        --target=$(ARCH)-linux \
        --prefix=/ \
        --with-avahi-user=root \
        --with-avahi-group=root \
        --with-avahi-priv-access-group=root \
        --with-autoipd-user=root \
        --with-autoipd-group=root \
        --disable-stack-protector \
        --disable-glib --disable-qt3 --disable-qt4 --disable-gtk --disable-dbus \
        --disable-python --disable-pygtk --disable-python-dbus --disable-mono \
        --disable-monodoc --disable-doxygen-doc --disable-doxygen-dot --disable-doxygen-html \
        --disable-manpages --disable-xmltoman --with-distro=none --disable-gdbm $(QOUT)
	$(V) cd ../ && touch .configured $(QOUT)
endif

sim:

chkconfig:

preconfig:

buildfs:

install: 
ifeq ($(CONFIG_FS_APPS_AVAHI),y)
	$(V) install -D $(AVAHI)/src/avahi-autoipd/avahi-autoipd                  $(FSROOT)/usr/sbin/avahi-autoipd $(QOUT)
	$(V) install -D $(AVAHI)/src/avahi-common/.libs/libavahi-common.so.3.4.4  $(FSROOT)/lib/libavahi-common.so.3.4.4 $(QOUT)
	$(V) install -D $(AVAHI)/src/avahi-common/.libs/libavahi-common.so.3      $(FSROOT)/lib/libavahi-common.so.3 $(QOUT)
	$(V) install -D $(AVAHI)/src/avahi-common/.libs/libavahi-common.so        $(FSROOT)/lib/libavahi-common.so $(QOUT)
	$(V) install -D $(AVAHI)/src/avahi-core/.libs/libavahi-core.so.5.0.2      $(FSROOT)/lib/libavahi-core.so.5.0.2 $(QOUT)
	$(V) install -D $(AVAHI)/src/avahi-core/.libs/libavahi-core.so.5          $(FSROOT)/lib/libavahi-core.so.5 $(QOUT)
	$(V) install -D $(AVAHI)/src/avahi-core/.libs/libavahi-core.so            $(FSROOT)/lib/libavahi-core.so $(QOUT)
	$(V) touch .installed $(QOUT)
endif

clean: 
ifeq ($(CONFIG_FS_APPS_AVAHI),y)
	$(V) rm -f .configured $(QOUT)
	$(V) rm -f .installed $(QOUT)
	$(V) rm -Rf Output/* $(QOUT)
	$(V) $(MAKE) clean distclean -C src  $(QOUT)
endif


