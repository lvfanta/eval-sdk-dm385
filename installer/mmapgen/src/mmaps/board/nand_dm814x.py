#!/usr/bin/env python
# ==========================================================================
#
# Copyright (C) 2014 RidgeRun, LLC (http://www.ridgerun.com)
# All Rights Reserved.
#
# Author: Jose Pablo Carballo <jose.carballo@ridgerun.com>
#
# The contents of this software are proprietary and confidential to RidgeRun,
# LLC.  No part of this program may be photocopied, reproduced or translated
# into another programming language without prior written consent of 
# RidgeRun, LLC.
#
# Memory map calculations for nand installation mode, DM814x board.
#
# ==========================================================================


# ==========================================================================
# Imports
# ==========================================================================

import nand_dm816x

class NandMemoryMapDm814x(nand_dm816x.NandMemoryMapDm816x):
    
    imgs = {
        'ipl': 'images/u-boot.min.nand',
        'bootloader': 'images/bootloader.nandbin',
        'kernel': 'images/kernel.uImage',
        'fs': 'images/fsimage.uImage'
    }
    