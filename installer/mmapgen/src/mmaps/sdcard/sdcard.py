#!/usr/bin/env python
# ==========================================================================
#
# Copyright (C) 2012-2014 RidgeRun, LLC (http://www.ridgerun.com)
# All Rights Reserved.
#
# Author: Jose Pablo Carballo <jose.carballo@ridgerun.com>
#
# The contents of this software are proprietary and confidential to RidgeRun,
# LLC.  No part of this program may be photocopied, reproduced or translated
# into another programming language without prior written consent of 
# RidgeRun, LLC.
#
# Memory map calculations for sd-card installation mode.
#
# ==========================================================================

"""
Memory map calculations for sd-card installation mode.
"""

# ==========================================================================
# Imports
# ==========================================================================

import os
import utils
import utils.hexutils as hexutils
import math
from partition import Partition
import geometry
import ConfigParser
import prettytable
from mmaps.mmap import MemoryMap, MemoryMapException

# ==========================================================================
# Public Classes
# ==========================================================================

class SDCardMemoryMap(MemoryMap):
    """
    Class to handle the memory map of the SD-card installation mode.
    
    It supports only a boot partition, and one optional filesystem
    partition (rootfs).
    """
    
    def __init__(self):
        """
        Constructor.
        """
        
        self._config = utils.config.get_global_config()
        self._logger = utils.logger.get_global_logger()
        
        self._partitions = []
        
    def validate_config(self):
        """
        Returns true if the associated bspconfig has all the required
        configurations for this installation mode; false otherwise.
        """
        
        if not self._config.has_option('CONFIG_INSTALLER_MODE_SD_CARD'):
            self._logger.warning('You are asking to generate the SD card ' + 
                            'memory map, but CONFIG_INSTALLER_MODE_SD_CARD ' +
                            'is not set.')
        
        if not self._config.has_option('CONFIG_INSTALLER_UBOOT_PARTITION_SIZE'):
            raise MemoryMapException('Missing CONFIG_INSTALLER_UBOOT_PARTITION_SIZE.')
        
        if self._config.has_option('CONFIG_FS_TARGET_SD'):
            
            if not self._config.has_option('CONFIG_INSTALLER_SD_ROOTFS_SIZE'):
                raise MemoryMapException('Missing CONFIG_INSTALLER_SD_ROOTFS_SIZE.')
            
            if (not self._config.has_option('CONFIG_INSTALLER_SD_ROOTFS_TYPE_EXT3') and
                not self._config.has_option('CONFIG_INSTALLER_SD_ROOTFS_TYPE_EXT4') and
                not self._config.has_option('CONFIG_INSTALLER_SD_ROOTFS_TYPE_EXT4_NO_JOURNAL')):
                self._logger.warning('Missing CONFIG_INSTALLER_SD_ROOTFS_TYPE_EXT*, ' +
                                     'assuming Linux native, ext4.')
    
    def generate_info(self):
        pass
    
    def generate_mmap(self):
        """
        Generates the mmap given the current information in the configuration
        file.
        
        Assumes that all the required configurations exist in the bspconfig
        file, which should be verified by the caller using validate_config().
        """
        
        self._generate_boot_partition()
        self._generate_rootfs_partition()
    
    def _generate_boot_partition(self):
        """
        Generates the start and size (in cylinders) of the boot partition.
        """
    
        boot = Partition('boot')
        
        # Config variables
        boot_partition_size_mb = \
            self._config.get_clean('CONFIG_INSTALLER_UBOOT_PARTITION_SIZE')
        
        if self._config.has_option('CONFIG_BSP_ARCH_SD_CARD_INSTALLER_BOOTLOADER_OUT_OF_FS'):
            boot.start = 1 # Leave room for the MBR at cylinder 0
        else:
            boot.start = 0
        
        if boot_partition_size_mb == geometry.FULL_SIZE:
            boot.size = geometry.FULL_SIZE
        else:
            boot_partition_size_b = float(int(boot_partition_size_mb) << 20)
            boot_partition_size   = math.ceil(boot_partition_size_b /
                                               geometry.CYLINDER_BYTE_SIZE)
            boot.size = int(boot_partition_size)
            
        # Boot partition is bootable
        boot.bootable = True
        
        # Boot partition is FAT32/VFAT
        boot.type = Partition.TYPE_FAT32_LBA
        boot.filesystem = Partition.FILESYSTEM_VFAT
        
        # Boot components are: bootloader and kernel.
        boot.components = [boot.COMPONENT_BOOTLOADER, boot.COMPONENT_KERNEL]
            
        self._partitions.append(boot)
        
    def _generate_rootfs_partition(self):
        """
        Generates the start and size (in cylinders) of the rootfs (filesystem)
        partition.
        
        Note that the rootfs partition might not be appended if
        CONFIG_FS_TARGET_SD is not set, or the boot partition size is '-',
        since it means that the boot partition took all the available space.
        
        Assumes that the boot partition has already been appended to the
        partitions list.
        """
        
        # Check that the uboot partition has been appended
        if not self._partitions:
            self._logger.error('No info for the boot partition, '
                               'refused to generate rootfs partition info.')
            return
        
        # We need some info from the boot partition later on
        boot   = self._partitions[0]
        rootfs = Partition('rootfs')
        
        # Config variables
        rootfs_in_sd = self._config.get_clean('CONFIG_FS_TARGET_SD')
        rootfs_partition_size_mb = self._config.get_clean('CONFIG_INSTALLER_SD_ROOTFS_SIZE')
        
        rootfs_partition_fs = Partition.FILESYSTEM_UNKNOWN
        if self._config.has_option('CONFIG_INSTALLER_SD_ROOTFS_TYPE_EXT3'):
            rootfs_partition_fs = Partition.FILESYSTEM_EXT3
        elif self._config.has_option('CONFIG_INSTALLER_SD_ROOTFS_TYPE_EXT4'): 
            rootfs_partition_fs = Partition.FILESYSTEM_EXT4
        elif self._config.has_option('CONFIG_INSTALLER_SD_ROOTFS_TYPE_EXT4_NO_JOURNAL'): 
            rootfs_partition_fs = Partition.FILESYSTEM_EXT4_WRITEBACK
        
        rootfs_partition_type = Partition.TYPE_UNKNOWN
        if (rootfs_partition_fs == Partition.FILESYSTEM_EXT3 or
            rootfs_partition_fs == Partition.FILESYSTEM_EXT4 or
            rootfs_partition_fs == Partition.FILESYSTEM_EXT4_WRITEBACK):
            rootfs_partition_type = Partition.TYPE_LINUX_NATIVE

        # Populate the rootfs partition
        if rootfs_in_sd == 'y' and boot.size != geometry.FULL_SIZE:
            
            # rootfs is installed next to the boot partition            
            rootfs.start = int(boot.start + boot.size)
            
            if rootfs_partition_size_mb == geometry.FULL_SIZE:
                rootfs.size = geometry.FULL_SIZE
            else:
                rootfs_partition_size_b = \
                    float(int(rootfs_partition_size_mb) << 20)
                rootfs_partition_size = math.ceil(rootfs_partition_size_b /
                                                geometry.CYLINDER_BYTE_SIZE)
                rootfs.size = int(rootfs_partition_size)

            # If the partition type for rootfs was not specified, assume
            # Linux native, ext4. A warning should've been raised already 
            # by validate_config().
            if rootfs_partition_type == Partition.TYPE_UNKNOWN:
                rootfs_partition_fs = Partition.FILESYSTEM_EXT4
                rootfs_partition_type = Partition.TYPE_LINUX_NATIVE
            
            rootfs.type = rootfs_partition_type
            rootfs.filesystem = rootfs_partition_fs
            
            # Rootfs components are: rootfs
            rootfs.components = [rootfs.COMPONENT_ROOTFS]
                
            self._partitions.append(rootfs)
    
    def draw_str(self):
        """
        Returns the string holding the human readable drawing of the
        partitions in the memory map.
        """
        
        table = prettytable.PrettyTable(["Name",
                                         "Start (cyl)",
                                         "Size* (cyl)",
                                         "Start (b)",
                                         "Size (b)",
                                         "Size (mb)",
                                         "Bootable",
                                         "Type",
                                         "Filesystem"])
        
        table.sortby = "Start (cyl)"
        table.align["Name"] = "l" # Left align names
        
        for part in self._partitions:    
            
            # Start info - bytes
            start_b = part.start * geometry.CYLINDER_BYTE_SIZE
            start_b = hexutils.hex_format(start_b)
        
            # Size info - bytes and mbytes
            size_b  = geometry.FULL_SIZE
            size_mb = geometry.FULL_SIZE
            
            if part.size != geometry.FULL_SIZE:
                size_b  = int(part.size * geometry.CYLINDER_BYTE_SIZE)
                size_mb = int(size_b) >> 20
            
            table.add_row([part.name,
                           part.start,
                           part.size,
                           start_b,
                           size_b,
                           size_mb,
                           '*' if part.is_bootable else '',
                           Partition.decode_partition_type(part.type),
                           part.filesystem])
        
        return table.get_string()
        
    def draw(self):
        """
        Prints a human readable drawing of the partitions in the memory map.
        """
        self._logger.info('')
        self._logger.info('  SD card memory map')
        self._logger.info(self.draw_str())
        self._logger.info('  * Cylinder size: %s (bytes)' %
                          geometry.CYLINDER_BYTE_SIZE)
        self._logger.info("  ** Size '-' represents all the available space in "
                          "the given storage device")
        self._logger.info('')
        
    
    def save(self, filename):
        """
        Saves the uboot and fs partitions information -if any- to the
        specified file.
        
        Assumes all the parent directories to the file are created and
        writable.
        """
        
        if not self._partitions:
            self._logger.warning('No partitions, try calling generate().')
            return

        config = ConfigParser.RawConfigParser()
        
        # uboot partition info
        config.add_section('boot')
        config.set('boot', 'name', self._partitions[0].name)
        config.set('boot', 'start', str(self._partitions[0].start))
        config.set('boot', 'size', str(self._partitions[0].size))
        config.set('boot', 'bootable', self._partitions[0].is_bootable)
        config.set('boot', 'type', self._partitions[0].type)
        config.set('boot', 'filesystem', self._partitions[0].filesystem)
        
        components = ''
        for comp in self._partitions[0].components:
            components += comp + ", "
        config.set('boot', 'components', components)
            
        # fs partition info
        if len(self._partitions) == 2:
            config.add_section('rootfs')
            config.set('rootfs', 'name', self._partitions[1].name)
            config.set('rootfs', 'start', str(self._partitions[1].start))
            config.set('rootfs', 'size', str(self._partitions[1].size))
            config.set('rootfs', 'bootable', self._partitions[1].is_bootable)
            config.set('rootfs', 'type', self._partitions[1].type)
            config.set('rootfs', 'filesystem', self._partitions[1].filesystem)
            
            components = ''
            for comp in self._partitions[1].components:
                components += comp + ", "
            config.set('rootfs', 'components', components)
            
        with open(filename, 'wb') as config_file:
            config.write(config_file)
            
        self._logger.info('Generated SD card memory map to %s' % filename)
        
    def read(self, filename):
        """
        Reads the partitions information from the given file.
        
        Side effect: Existing information for partitions will be overwritten.  
        """
        
        if not os.path.exists(filename):
            self._logger.error('File %s does not exist' % filename)
            return
        
        # Reset the list
        self._partitions[:] = []
        
        config = ConfigParser.RawConfigParser()
        
        config.readfp(open(filename))
        
        # Uboot
        if config.has_section("boot"):
            
            name = ""
            size = ""
            start = ""
            part_type = ""
            filesystem = ""
            bootable = False
            
            if config.has_option("boot", "name"):
                name  = config.get("boot", "name")
            if config.has_option("boot", "start"):
                start = config.get("boot", "start")
            if config.has_option("boot", "size"):
                size  = config.get("boot", "size")
            if config.has_option("boot", "bootable"):
                bootable = config.getboolean("boot", "bootable")
            if config.has_option("boot", "type"):
                part_type  = config.get("boot", "type")
            if config.has_option("boot", "filesystem"):
                filesystem = config.get("boot", "filesystem")
                
            uboot = Partition(name)
            uboot.start = int(start)
            if size == geometry.FULL_SIZE:
                uboot.size = size
            else:
                uboot.size = int(size)
            uboot.bootable = bootable
            uboot.type = part_type
            uboot.filesystem = filesystem
            
            self._partitions.append(uboot)
        
        # Filesystem
        if config.has_section("rootfs"):
            
            name = ""
            size = ""
            start = ""
            part_type = ""
            filesystem = "" 
            bootable = False
            
            if config.has_option("rootfs", "name"):
                name  = config.get("rootfs", "name")
            if config.has_option("rootfs", "start"):
                start = config.get("rootfs", "start")
            if config.has_option("rootfs", "size"):
                size  = config.get("rootfs", "size")
            if config.has_option("rootfs", "bootable"):
                bootable = config.getboolean("rootfs", "bootable")
            if config.has_option("rootfs", "type"):
                part_type  = config.get("rootfs", "type")
            if config.has_option("rootfs", "filesystem"):
                filesystem = config.get("rootfs", "filesystem")
                
            fs = Partition(name)
            fs.start = int(start)
            if size == geometry.FULL_SIZE:
                fs.size = size
            else:
                fs.size = int(size)
            fs.bootable = bootable
            fs.type = part_type
            fs.filesystem = filesystem
            
            self._partitions.append(fs)

class SDCardFsMemoryMap(SDCardMemoryMap):
    """
    Class to handle the memory map of the SD-card installation mode, for
    when the SD card will hold the filesystem.
    
    It supports only one partition for the filesystem (rootfs).
    """
    
    def __init__(self):
        """
        Constructor.
        """
        
        SDCardMemoryMap.__init__(self)
        
    def validate_config(self):
        """
        Returns true if the associated bspconfig has all the required
        configurations for this installation mode; false otherwise.
        """
        
        if self._config.has_option('CONFIG_FS_TARGET_SD'):
            if (not self._config.has_option('CONFIG_INSTALLER_SD_ROOTFS_TYPE_EXT3') and
                not self._config.has_option('CONFIG_INSTALLER_SD_ROOTFS_TYPE_EXT4') and
                not self._config.has_option('CONFIG_INSTALLER_SD_ROOTFS_TYPE_EXT4_NO_JOURNAL')):
                self._logger.warning('Missing CONFIG_INSTALLER_SD_ROOTFS_TYPE_EXT*, ' +
                                     'assuming rootfs partition type ext4.')
        else:
            raise MemoryMapException('Missing CONFIG_FS_TARGET_SD.')
    
    def generate_mmap(self):
        """
        Generates the mmap given the current information in the configuration
        file.
        
        Assumes that all the required configurations exist in the bspconfig
        file, which should be verified by the caller using validate_config().
        """
        
        self._generate_rootfs_partition()
    
    def _generate_rootfs_partition(self):
        """
        Generates the information for the rootfs (filesystem) partition.
        """
        
        rootfs = Partition('rootfs')
        
        rootfs.filesystem = Partition.FILESYSTEM_UNKNOWN
        if self._config.has_option('CONFIG_INSTALLER_SD_ROOTFS_TYPE_EXT3'):
            rootfs.filesystem = Partition.FILESYSTEM_EXT3
        elif self._config.has_option('CONFIG_INSTALLER_SD_ROOTFS_TYPE_EXT4'):
            rootfs.filesystem = Partition.FILESYSTEM_EXT4
        elif self._config.has_option('CONFIG_INSTALLER_SD_ROOTFS_TYPE_EXT4_NO_JOURNAL'):
            rootfs.filesystem = Partition.FILESYSTEM_EXT4_WRITEBACK
        
        rootfs.type = Partition.TYPE_UNKNOWN
        if (rootfs.filesystem == Partition.FILESYSTEM_EXT3 or
            rootfs.filesystem == Partition.FILESYSTEM_EXT4 or
            rootfs.filesystem == Partition.FILESYSTEM_EXT4_WRITEBACK):
            rootfs.type = Partition.TYPE_LINUX_NATIVE
        
        # If the partition filesystem for rootfs was not specified, assume
        # Linux native, ext4.
        if rootfs.filesystem == Partition.FILESYSTEM_UNKNOWN:
            rootfs.filesystem = Partition.FILESYSTEM_EXT4
            rootfs.type = Partition.TYPE_LINUX_NATIVE
        
        # Take the whole SD card
        rootfs.start = 1
        rootfs.size = geometry.FULL_SIZE
        rootfs.bootable = False
        rootfs.components = [rootfs.COMPONENT_ROOTFS]
        self._partitions.append(rootfs)

    def save(self, filename):
        """
        Saves the fs partition information to the specified file.
        
        Assumes all the parent directories to the file are created and
        writable.
        """
        
        if not self._partitions:
            self._logger.warning('No partitions, try calling generate().')
            return

        config = ConfigParser.RawConfigParser()
        
        # fs partition info
        config.add_section('rootfs')
        config.set('rootfs', 'name', self._partitions[0].name)
        config.set('rootfs', 'start', str(self._partitions[0].start))
        config.set('rootfs', 'size', str(self._partitions[0].size))
        config.set('rootfs', 'bootable', self._partitions[0].is_bootable)
        config.set('rootfs', 'type', self._partitions[0].type)
        config.set('rootfs', 'filesystem', self._partitions[0].filesystem)
        
        components = ''
        for comp in self._partitions[0].components:
            components += comp + ", "
        config.set('rootfs', 'components', components)
            
        with open(filename, 'wb') as config_file:
            config.write(config_file)
            
        self._logger.info('Generated SD card memory map to %s' % filename)

class SDCardExternalInstallerMemoryMap(SDCardMemoryMap):
    """
    Class to handle the memory map of the SD-card installation mode, for
    when the SD card will hold an installer script capable of programming flash
    memory.
    
    It supports only one boot partition.
    """
    
    def __init__(self):
        """
        Constructor.
        """
        
        SDCardMemoryMap.__init__(self)
        
    def validate_config(self):
        """
        Returns true if the associated bspconfig has all the required
        configurations for this installation mode; false otherwise.
        """
        
        if not self._config.has_option('CONFIG_INSTALLER_MODE_SD_CARD_INSTALLER'):
            raise MemoryMapException('You are asking to generate the SD card memory ' 
                'map, but CONFIG_INSTALLER_MODE_SD_CARD_INSTALLER is not set.')
    
    def generate_mmap(self):
        """
        Generates the mmap given the current information in the configuration
        file.
        
        Assumes that all the required configurations exist in the bspconfig
        file, which should be verified by the caller using validate_config().
        """
        
        self._generate_boot_partition()
    
    def _generate_boot_partition(self):    
        boot = Partition('boot')
        if self._config.has_option('CONFIG_BSP_ARCH_SD_CARD_INSTALLER_BOOTLOADER_OUT_OF_FS'):
            boot.start = 1 # Leave room for the MBR at cylinder 0
        else:
            boot.start = 0
        boot.size = geometry.FULL_SIZE
        boot.bootable = True
        boot.type = Partition.TYPE_FAT32_LBA
        boot.filesystem = Partition.FILESYSTEM_VFAT
        boot.components = [boot.COMPONENT_BOOTLOADER]
        self._partitions.append(boot)
    