#!/usr/bin/env python
# ==========================================================================
#
# Copyright (C) 2013-2014 RidgeRun, LLC (http://www.ridgerun.com)
# All Rights Reserved.
#
# Author: Jose Pablo Carballo <jose.carballo@ridgerun.com>
#
# The contents of this software are proprietary and confidential to RidgeRun,
# LLC.  No part of this program may be photocopied, reproduced or translated
# into another programming language without prior written consent of 
# RidgeRun, LLC.
#
# Memory map calculations for nand installation mode, DM36x board.
#
# ==========================================================================


# ==========================================================================
# Imports
# ==========================================================================

import os
import utils
from utils import hexutils
from partition import NandPartition
import geometry
import prettytable
import ConfigParser

from mmaps.mmap import MemoryMap, MemoryMapException

# ==========================================================================
# CONSTANT
# ==========================================================================


# Extra NAND blocks to spare to the kernel, to have some grow margin
KERNEL_EXTRA_BLKS = 3

# Extra NAND blocks to spare to the filesystem (heuristic) - for a block size
# of 128Kb, each 8 extra blocks adds 1Mb.
FS_EXTRA_BLKS = 32

# ==========================================================================
# Public Classes
# ==========================================================================

class NandInfoDm36x():
    nand_blk_size = None
    nand_page_size = None
    mtdparts = None

class NandMemoryMapDm36x(MemoryMap):
    
    names = {
        'ipl': 'ubl',
        'bootloader': 'uboot',
        'kernel': 'kernel',
        'fs': 'rootfs'
    }

    imgs = {
        'ipl': 'images/ubl_nand.nandbin',
        'ipl_multi': 'images/multi_ubl_nand.nandbin',
        'bootloader': 'images/bootloader.nandbin',
        'kernel': 'images/kernel.uImage',
        'fs': 'images/fsimage.uImage'
    }
    
    FS_NFS = 'nfs'
    FS_SD = 'sd'
    FS_INITRD = 'initrd'
    FS_JFFS2 = 'jffs2'
    FS_UBIFS = 'ubifs'
    FS_CRAMFS = 'cramfs'
    FS_ROMFS = 'romfs'
    
    def __init__(self, devdir, nand_blk_size=geometry.NAND_BLK_SIZE,
                 nand_page_size=geometry.NAND_PAGE_SIZE):
        self._c = utils.config.get_global_config()
        self._l = utils.logger.get_global_logger()
        self._devdir = devdir
        self._partitions = []
        self._nand_blk_size = nand_blk_size
        if self._nand_blk_size == None:
            self._nand_blk_size = geometry.NAND_BLK_SIZE
        self._nand_page_size = nand_page_size
        if self._nand_page_size == None:
            self._nand_page_size = geometry.NAND_PAGE_SIZE
        self._info = NandInfoDm36x()
        
    def __get_nand_blk_size(self):
        return self._nand_blk_size
    
    def __set_nand_blk_size(self, size):
        self._nand_blk_size = size
    
    nand_blk_size = property(__get_nand_blk_size, __set_nand_blk_size, 
                           doc="""NAND block size (bytes).""")
    
    def __get_nand_page_size(self):
        return self._nand_page_size
    
    def __set_nand_page_size(self, size):
        self._nand_page_size = size
    
    nand_page_size = property(__get_nand_page_size, __set_nand_page_size, 
                           doc="""NAND page size (bytes).""")
    
    def validate_config(self):
        if (not self._c.has_option('CONFIG_INSTALLER_MODE_ATTACHED_BOARD') and
            not self._c.has_option('CONFIG_INSTALLER_MODE_SD_CARD_INSTALLER')):
            raise MemoryMapException('You are asking to generate the NAND ' 
                'memory map, but neither CONFIG_INSTALLER_MODE_ATTACHED_BOARD '
                'or CONFIG_INSTALLER_MODE_SD_CARD_INSTALLER are set.')
            
        if not self._c.has_option('CONFIG_BSP_ARCH_INSTALLER_IPL_FLASH_BLK_START'):
            self._l.warning('Missing CONFIG_BSP_ARCH_INSTALLER_IPL_FLASH_BLK_START')
            
        if not self._c.has_option('CONFIG_BSP_ARCH_INSTALLER_UBOOT_FLASH_BLK_START'):
            self._l.warning('Missing CONFIG_BSP_ARCH_INSTALLER_UBOOT_FLASH_BLK_START')
            
        if not self._c.has_option('CONFIG_INSTALLER_UBOOT_SIZE_IN_BLKS'):
            self._l.warning('Missing CONFIG_INSTALLER_UBOOT_SIZE_IN_BLKS')
            
        if not self._c.has_option('CONFIG_INSTALLER_KERNEL_SIZE_IN_BLKS'):
            self._l.warning('Missing CONFIG_INSTALLER_KERNEL_SIZE_IN_BLKS')
            
        if not self._c.has_option('CONFIG_FS_TARGET_NFSROOT'):
            if not self._c.has_option('CONFIG_INSTALLER_FS_SIZE_IN_BLKS'):
                self._l.warning('Missing CONFIG_INSTALLER_FS_SIZE_IN_BLKS')
        
        if self._c.has_option('CONFIG_INSTALLER_MTD_UBOOT_INTEGRATION'):        
            if not self._c.has_option('CONFIG_INSTALLER_MTD_DEVICE_NAME'):
                self._l.warning('Missing CONFIG_INSTALLER_MTD_DEVICE_NAME')

    def _bytes_to_blks(self, size_b):
        size_blks = (size_b / self.nand_blk_size)
        if (size_b % self.nand_blk_size != 0):
            size_blks += 1
        return size_blks

    def _check_imgs(self):
        for img in self.imgs.items():
            component = img[0]
            filename = '%s/%s' % (self._devdir, img[1])
            if component is 'fs':
                if self._fs_name() == NandMemoryMapDm36x.FS_NFS:
                    continue
            if not os.path.isfile(filename):
                raise MemoryMapException("File not found: %s" % filename)

    def generate_info(self):
        if self._nand_blk_size:
            self._info.nand_blk_size = self._nand_blk_size
        if self._nand_page_size:
            self._info.nand_page_size = self._nand_page_size
        self._info.mtdparts = self._generate_mtdparts()

    def generate_mmap(self):
        self._check_imgs()
        self._generate_ipl()
        self._generate_bootloader()
        self._generate_kernel()
        if (self._fs_name() != NandMemoryMapDm36x.FS_NFS and
            self._fs_name() != NandMemoryMapDm36x.FS_SD):
            self._generate_fs()

    def _generate_ipl(self):
        start_blk = 0
        if self._c.has_option('CONFIG_BSP_ARCH_INSTALLER_IPL_FLASH_BLK_START'):
            start_blk = int(self._c.get_clean('CONFIG_BSP_ARCH_INSTALLER_IPL_FLASH_BLK_START'), 16)
        if self._c.has_option('CONFIG_ARCH_IPL_COPIES'):
            img = '%s/%s' % (self._devdir, self.imgs['ipl_multi'])
        else:
            img = '%s/%s' % (self._devdir, self.imgs['ipl'])
        size = os.path.getsize(img)
        size_blks = self._bytes_to_blks(size)
        ipl = NandPartition(self.names['ipl'])
        ipl.image = img
        ipl.start_blk = start_blk
        ipl.size_blks = size_blks
        self._partitions.append(ipl)

    def _generate_bootloader(self):
        start_blk = 0
        ipl_last_blk = 0
        if self._c.has_option('CONFIG_BSP_ARCH_INSTALLER_UBOOT_FLASH_BLK_START'):
            start_blk = int(self._c.get_clean('CONFIG_BSP_ARCH_INSTALLER_UBOOT_FLASH_BLK_START'), 16)
        for part in self._partitions: 
            if part.name == self.names['ipl']:
                ipl_last_blk = part.start_blk + part.size_blks
        if start_blk < ipl_last_blk:
            if self._c.has_option('CONFIG_BSP_ARCH_INSTALLER_UBOOT_FLASH_BLK_START'):
                raise MemoryMapException("IPL ends at block %s, can't start the "
                    "bootloader partition at block %s, please check "
                    "CONFIG_BSP_ARCH_INSTALLER_UBOOT_FLASH_BLK_START" % 
                    (hex(ipl_last_blk), hex(start_blk)))
            start_blk = ipl_last_blk
        img = '%s/%s' % (self._devdir, self.imgs['bootloader'])
        size = os.path.getsize(img)
        size_blks = self._bytes_to_blks(size)
        if self._c.has_option('CONFIG_INSTALLER_UBOOT_SIZE_IN_BLKS'):
            uboot_last_blk = start_blk + size_blks
            uboot_last_allowed_blk = int(self._c.get_clean('CONFIG_INSTALLER_UBOOT_SIZE_IN_BLKS'))
            if uboot_last_blk > uboot_last_allowed_blk:
                raise MemoryMapException("The allowed space for %s and %s "
                "(CONFIG_INSTALLER_UBOOT_SIZE_IN_BLKS = %s) is smaller than "
                "the required one (%s NAND blocks), please reconfigure your SDK"
                % (self.names['ipl'], self.names['bootloader'],
                   uboot_last_allowed_blk, uboot_last_blk))
        uboot = NandPartition(self.names['bootloader'])
        uboot.image = img
        uboot.start_blk = start_blk
        uboot.size_blks = size_blks
        self._partitions.append(uboot)

    def _generate_kernel(self):
        start_blk = 0
        if self._c.has_option('CONFIG_INSTALLER_UBOOT_SIZE_IN_BLKS'):
                    uboot_last_blk = int(self._c.get_clean('CONFIG_INSTALLER_UBOOT_SIZE_IN_BLKS'))
                    start_blk = uboot_last_blk 
        else:
            for part in self._partitions: 
                if part.name == self.names['bootloader']:
                    start_blk = part.start_blk + part.size_blks
        img = '%s/%s' % (self._devdir, self.imgs['kernel'])
        size = os.path.getsize(img)
        size_blks = self._bytes_to_blks(size)
        size_blks += KERNEL_EXTRA_BLKS
        if self._c.has_option('CONFIG_INSTALLER_KERNEL_SIZE_IN_BLKS'):
            min_size_blks = int(self._c.get_clean('CONFIG_INSTALLER_KERNEL_SIZE_IN_BLKS'))
            if size_blks < min_size_blks:
                size_blks = min_size_blks
        kernel = NandPartition(self.names['kernel'])
        kernel.image = img
        kernel.start_blk = start_blk
        kernel.size_blks = size_blks
        self._partitions.append(kernel)

    def _generate_fs(self):
        start_blk = 0
        for part in self._partitions: 
            if part.name == self.names['kernel']:
                start_blk = part.start_blk + part.size_blks
        img = '%s/%s' % (self._devdir, self.imgs['fs'])
        size = os.path.getsize(img)
        size_blks = self._bytes_to_blks(size)
        size_blks += FS_EXTRA_BLKS
        if self._c.has_option('CONFIG_INSTALLER_FS_SIZE_IN_BLKS'):
            min_size_blks = int(self._c.get_clean('CONFIG_INSTALLER_FS_SIZE_IN_BLKS'))
            if size_blks < min_size_blks:
                size_blks = min_size_blks
        fs = NandPartition(self.names['fs'])
        fs.image = img
        fs.start_blk = start_blk
        fs.size_blks = size_blks
        fs.filesystem = self._fs_name()
        self._partitions.append(fs)

    def _fs_name(self):
        nfs = self._c.get_clean('CONFIG_FS_TARGET_NFSROOT')
        sd = self._c.get_clean('CONFIG_FS_TARGET_SD')
        initrd = self._c.get_clean('CONFIG_FS_TARGET_INITRD')
        jffs2 = self._c.get_clean('CONFIG_FS_TARGET_JFFS2FS')
        ubifs = self._c.get_clean('CONFIG_FS_TARGET_UBIFS')
        cramfs = self._c.get_clean('CONFIG_FS_TARGET_CRAMFS')
        romfs = self._c.get_clean('CONFIG_FS_TARGET_ROMFS')
        if nfs and nfs == 'y': return NandMemoryMapDm36x.FS_NFS
        elif sd and sd == 'y': return NandMemoryMapDm36x.FS_SD
        elif initrd and initrd == 'y': return NandMemoryMapDm36x.FS_INITRD
        elif jffs2 and jffs2 == 'y': return NandMemoryMapDm36x.FS_JFFS2
        elif ubifs and ubifs == 'y': return NandMemoryMapDm36x.FS_UBIFS
        elif cramfs and cramfs == 'y': return NandMemoryMapDm36x.FS_CRAMFS
        elif romfs and romfs == 'y': return NandMemoryMapDm36x.FS_ROMFS
        else: return ''

    def draw_str(self):
        """
        Returns the string holding the human readable drawing of the
        partitions in the memory map.
        """
        
        table = prettytable.PrettyTable(["Name",
                                         "Start blk",
                                         "Last blk",
                                         "Size* (blk)",
                                         "Offset",
                                         "Size (b)",
                                         "Size (b)",
                                         "Size (mb)",
                                         "Filesystem"])
        table.sortby = "Start blk"
        table.align["Name"] = "l" # Left align names
        for part in self._partitions:
            off = part.start_blk * self._nand_blk_size
            size_b  = int(part.size_blks * self._nand_blk_size)
            size_mb = size_b / float(1024 * 1024)
            table.add_row([part.name,
                           part.start_blk,
                           part.start_blk + part.size_blks - 1,
                           part.size_blks, 
                           hexutils.hex_format(off),
                           hexutils.hex_format(size_b),
                           size_b,
                           "%.02f" % size_mb,
                           part.filesystem])
        return table.get_string()

    def _generate_mtdparts(self):
        mtdparts = ''
        if self._c.has_option('CONFIG_INSTALLER_MTD_DEVICE_NAME'):
            mtd_device = self._c.get_clean('CONFIG_INSTALLER_MTD_DEVICE_NAME')
            mtdparts = "mtdparts=%s:" % mtd_device
            for part in self._partitions:
                size_k = (part.size_blks * self.nand_blk_size) / 1024
                off_k = (part.start_blk * self.nand_blk_size) / 1024
                mtdparts += '%sk@%sk(%s),' % (size_k, off_k, part.name.upper())
            if self._c.has_option('CONFIG_INSTALLER_MTD_EXTRA_PARTITIONS'):
				mtdparts += self._c.get_clean('CONFIG_INSTALLER_MTD_EXTRA_PARTITIONS')
        return mtdparts.rstrip(',')

    def draw(self):
        """
        Prints a human readable drawing of the partitions in the memory map.
        """
        
        self._l.info('')
        self._l.info('  NAND memory map')
        self._l.info(self.draw_str())
        self._l.info('  * NAND block size: %s (bytes)' % self._nand_blk_size)
        self._l.info('')

    def save(self, filename):
        config = ConfigParser.RawConfigParser()
        config.add_section('info')
        if self._info.nand_blk_size:
            config.set('info', 'nand_blk_size', self._info.nand_blk_size)
        if self._info.nand_page_size:
            config.set('info', 'nand_page_size', self._info.nand_page_size)
        if self._info.mtdparts:
            config.set('info', 'mtdparts', self._info.mtdparts)
        for part in self._partitions:
            for name in self.names.items():
                if name[1] == part.name:
                    section_name = name[0]
            config.add_section(section_name)
            config.set(section_name, 'name', part.name)
            config.set(section_name, 'start_blk', part.start_blk)
            config.set(section_name, 'size_blks', part.size_blks)
            config.set(section_name, 'fs', part.filesystem)
            config.set(section_name, 'image', part.image)
        with open(filename, 'wb') as config_file:
            config.write(config_file)
        self._l.info('Generated NAND memory map to %s' % filename)
