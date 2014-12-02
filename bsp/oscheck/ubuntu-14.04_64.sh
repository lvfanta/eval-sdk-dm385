#!/bin/sh

# Initial ldconfig in Ubuntu 14.04 reported unknown machine 40
# instead of properly handling ARM shared libaries.  Fix
# by getting older version of ldconfig
# see: http://arm.slackware.com/listarchive/2013-November/001870.html

make -C $DEVDIR/fs/host-apps/ldconfig-2.15 build install
