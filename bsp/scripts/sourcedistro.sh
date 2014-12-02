#! /bin/bash

#$L$
# Copyright (C) 2013 Ridgerun (http://www.ridgerun.com). 
##$L$

set -e

# ensure DEVDIR is set
if ! [ -n "${DEVDIR}" ]
then
	echo "DEVDIR is not set"
	exit 1
fi

# some constants
readonly MAKE_CONF="${DEVDIR}/bsp/mach/Make.conf"
readonly APP_DIRS="fs/apps proprietary"
readonly KERNEL=$(grep -E --max-count=1 "^\s*KERNEL\s*[\?:]?=" $MAKE_CONF | cut -d "=" -f 2)
readonly BOOTLOADER=$(grep -E --max-count=1 "^\s*BOOTLOADER\s*[\?:]?=" $MAKE_CONF | cut -d "=" -f 2)
readonly TOOLCHAIN=$(grep -E --max-count=1 "^\s*TOOLCHAIN\s*[\?:]?=" $MAKE_CONF | cut -d "=" -f 2)

# create empty list of all software components
COMPONENTS=""

#Add the toolchain to the list of all components
COMPONENTS="$COMPONENTS ${DEVDIR}/toolchain/$TOOLCHAIN"

# find all apps and libs in the SDK
APPS=""
for APP_DIR in ${APP_DIRS}
do
	APPS="$APPS $(find "${DEVDIR}/${APP_DIR}" -mindepth 1 -maxdepth 1 \( -type d -or -type l \) -and -not -name "\.svn" | sort)"
done

# check, which apps & libs are selected (in bspconfig)
for APP in $APPS
do
	if ${DEVDIR}/bsp/scripts/metainfo -c -p $APP   
	then
		if [ "$APP" != "${DEVDIR}/fs/apps/sysvinit-2011.5.11" ]
		then
			COMPONENTS="$COMPONENTS $APP"
		fi
	fi
done

# Create the install directory
readonly INSTALL_DIR=${DEVDIR}/images/sourcedistro
rm -rf ${INSTALL_DIR} # ensure INSTALL_DIR is always empty
mkdir -p ${INSTALL_DIR}

# Copy the kernel package to install directory
mkdir -p ${INSTALL_DIR}/$KERNEL
cp -rf ${DEVDIR}/kernel/$KERNEL ${INSTALL_DIR}/$KERNEL
cp -rfL ${DEVDIR}/kernel/patches ${DEVDIR}/kernel/series ${INSTALL_DIR}/$KERNEL

# Copy the bootloader package to install directory
mkdir -p ${INSTALL_DIR}/$BOOTLOADER
cp -rf ${DEVDIR}/bootloader/$BOOTLOADER/src ${INSTALL_DIR}/$BOOTLOADER
cp -rfL ${DEVDIR}/bootloader/$BOOTLOADER/patches ${DEVDIR}/bootloader/$BOOTLOADER/series ${INSTALL_DIR}/$BOOTLOADER

# Iterate over all selected components and copy all the open source packages to the install directory.
for COMPONENT in $COMPONENTS
do
	COPYRIGHTS=$COMPONENT/copyrights.xml
	SRCDISTRO_HELP=$COMPONENT/sourcedistro-help.sh
	if [ -x "$SRCDISTRO_HELP" ]
	then
		cd $COMPONENT
		./sourcedistro-help.sh	
	else
		if [ -r "$COPYRIGHTS" ]
		then
			LICENSE_TYPE=$(grep --max-count=1 "license type" $COPYRIGHTS | cut -d '"' -f2)
			if [ "$LICENSE_TYPE" != "Proprietary" ] && [ "$LICENSE_TYPE" != "Private" ]
			then
				mkdir -p ${INSTALL_DIR}/$(basename $COMPONENT)
				make -C $COMPONENT rrfetched rrpatched
				cp -rf $COMPONENT/src ${INSTALL_DIR}/$(basename $COMPONENT)
				if [ -d $COMPONENT/patches ]
				then 
					cp -rfL $COMPONENT/patches $COMPONENT/series ${INSTALL_DIR}/$(basename $COMPONENT)
				fi
			fi
		else
			echo "*** ERROR: failed to read ${COPYRIGHTS}"
			exit 1
		fi
	fi
done

# Remove all the .svn directories
cd ${INSTALL_DIR}
find . -name ".svn" | xargs rm -rf

#Create the tar file
cd ${INSTALL_DIR}/..
tar -cvzf $(basename $INSTALL_DIR).tar.gz $(basename $INSTALL_DIR)
rm -rf ${INSTALL_DIR}

exit 0
