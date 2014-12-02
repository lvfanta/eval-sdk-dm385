#$L$
# Copyright (C) 2014 Ridgerun (http://www.ridgerun.com). 
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


.PHONY: build chkconfig src preconfig buildfs clean install

ifeq ($(DEVDIR),)
$(error ====== DEVDIR variable is empty, invoke this Makefile from the BSP root, or provide the path to it =====)
endif

PKG_URL= http://security.ubuntu.com/ubuntu/pool/main/e/eglibc
PKG_TARBALL=libc-bin_2.15-0ubuntu10.7_i386.deb
PKG_SHA1SUM=eb214889010b0d2b1e85d1182d2394c68116f7ba

LDCONF=$(DEVDIR)/bsp/local/bin/ldconfig.2_15
export LDCONFIG=ldconfig.2_15

# Initial ldconfig in Ubuntu 14.04 reported unknown machine 40
# instead of properly handling ARM shared libaries.  Fix
# by getting older version of ldconfig
# see: http://arm.slackware.com/listarchive/2013-November/001870.html

$(LDCONF): rrfetched
	$(V)install -Dm 755 ldconfig-2.15/sbin/ldconfig.real $@
	$(V)echo "LDCONFIG=ldconfig.2_15" >> $(DEVDIR)/bsp/classes/common.defs
	$(V)sed -i -e 's!LDCONFIG?=.*!LDCONFIG?=ldconfig.2_15!' $(DEVDIR)/bsp/classes/common.defs

include $(DEVDIR)/bsp/classes/common.defs
include $(DEVDIR)/bsp/classes/fetcher.defs

build: $(LDCONF)

cmdline:

buildfs:

preconfig:

install:


clean: rrfetched_clean

