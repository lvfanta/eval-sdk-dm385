#! /bin/bash

#$L$
# Copyright (C) 2013 Ridgerun (http://www.ridgerun.com). 
##$L$

set -e
# Install directory
readonly INSTALL_DIR=${DEVDIR}/images/sourcedistro
LICENSE_FILE=copyrights.xml

# Package name
PKG_NAME=$(grep --max-count=1 "<name" $LICENSE_FILE | cut -d ">" -f2 | cut -d "<" -f1)

# Download the toolchain source package 
DOWNLOAD_URL=$(grep --max-count=1 "<downloadLink" $LICENSE_FILE | cut -d ">" -f2 | cut -d "<" -f1)
wget $DOWNLOAD_URL

# Toolchain source tarball name
TOOLCHAIN_SRC_TARBALL=$(echo $DOWNLOAD_URL |rev|cut -f1 -d'/'|rev)

# Untar the toolchain source package
tar -xjf $TOOLCHAIN_SRC_TARBALL

# Find and untar the glibc source package
GLIB_TARBALL=`find . -name "$PKG_NAME-*"`
tar -xjf $GLIB_TARBALL

# Removing toolchain directories
rm -rf ${TOOLCHAIN_SRC_TARBALL%.src*} ${TOOLCHAIN_SRC_TARBALL}

# Copy the package to the install directory
cp -r `find . -name "$PKG_NAME*"` $INSTALL_DIR

# Removing the package
rm -r $PKG_NAME*

exit 0
