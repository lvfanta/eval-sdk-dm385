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
# Geometry associated definitions.
#
# ==========================================================================

# ==========================================================================
# Constants
# ==========================================================================

# Geometry

#: NAND block size (bytes)
NAND_BLK_SIZE = 131072

#: NAND page size (bytes)
NAND_PAGE_SIZE = 2048

#: From uboot*/src/include/configs/davinci_dm368leopard.h (a.k.a CONFIG_SYS_NAND_BASE_LIST)
NAND_BASE_ADDR = '0x02000000'

