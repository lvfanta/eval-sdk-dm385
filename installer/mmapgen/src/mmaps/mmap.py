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
# Memory map interface
#
# ==========================================================================


class MemoryMapException(Exception):
    pass

class MemoryMap(object):
    
    def validate_config(self):
        raise NotImplementedError
    
    def generate_mmap(self):
        raise NotImplementedError
    
    def generate_info(self):
        raise NotImplementedError
    
    def draw(self):
        raise NotImplementedError
    
    def save(self):
        raise NotImplementedError 
