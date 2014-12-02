#!/usr/bin/env python
# ==========================================================================
#
# Copyright (C) 2013 RidgeRun, LLC (http://www.ridgerun.com)
# All Rights Reserved.
#
# Author: Jose Pablo Carballo <jose.carballo@ridgerun.com>
#
# The contents of this software are proprietary and confidential to RidgeRun,
# LLC.  No part of this program may be photocopied, reproduced or translated
# into another programming language without prior written consent of 
# RidgeRun, LLC.
#
# Tests for the nand module.
#
# ==========================================================================

import sys, os
import unittest
import check_env

sys.path.insert(1, os.path.abspath('..'))

import rrutils

from nand import NandMemoryMap
from partition import NandPartition

devdir = check_env.get_devdir()
if not devdir: sys.exit(-1)

class NandMemoryMapTestCase(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        bspconfig = '%s/bsp/mach/bspconfig' % devdir
        rrutils.config.get_global_config(bspconfig)
        rrutils.logger.basic_config(verbose=False)
        logger = rrutils.logger.get_global_logger('NandInstaller')
        logger.setLevel(rrutils.logger.DEBUG)
        
    def setUp(self):
        self._mmap = NandMemoryMap()
    
    def tearDown(self):
        pass
    
    def testGenerate(self):
        ipl_img = '%s/images/ubl_nand.nandbin' % devdir
        bootloader_img = '%s/images/bootloader.nandbin' % devdir
        kernel_img = '%s/images/kernel.uImage' % devdir
        fs_img = '%s/images/fsimage.uImage' % devdir
        fs_name = NandPartition.FILESYSTEM_UBIFS
        self._mmap.validate_config()
        self._mmap.generate(ipl_img,
                            bootloader_img,
                            kernel_img,
                            fs_img,
                            fs_name)
        self._mmap.draw()
        self._mmap.save('%s/images/nand-mmap.config' % devdir)
    
if __name__ == '__main__':
    loader = unittest.TestLoader() 
    suite = loader.loadTestsFromTestCase(NandMemoryMapTestCase)
    unittest.TextTestRunner(verbosity=2).run(suite)
    