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
# The mmapgen tool generates memory maps according to the associated
# installation configuration.
#
# ==========================================================================

"""
The mmapgen tool generates memory maps according to the associated
installation configuration.
"""

# ==========================================================================
# Imports
# ==========================================================================

import os
import sys
import argparse
import utils
import signal
import logging

from mmaps.sdcard import *
from mmaps.board import *
from mmaps import MemoryMapException

# ==========================================================================
# Global variables
# ==========================================================================

_args = []
_parser  = None
_logger  = None
_config  = None

# ==========================================================================
# Constants
# ==========================================================================

MODE_SD = 'sd'
MODE_SD_FS = 'sd-fs'
MODE_SD_SCRIPT = 'sd-script'
MODE_NAND = 'nand'

# ==========================================================================
# Functions
# ==========================================================================

def _init_logging():
    global _logger
    _program_name = os.path.basename(sys.argv[0])
    _logger = utils.logger.init_global_logger(_program_name)
    _logger.setLevel(logging.DEBUG)
    streamhandler = logging.StreamHandler()
    streamhandler.setFormatter(logging.Formatter('%(msg)s'))
    if _args.verbose:
        streamhandler.setLevel(logging.DEBUG)
    else:
        streamhandler.setLevel(logging.INFO)
    if _args.quiet:
        streamhandler.setLevel(logging.CRITICAL)
    _logger.addHandler(streamhandler)

def _clean_exit(code=0):
    if code != 0: _logger.debug('Exiting with code %d' % code)
    exit(code)

def _abort_mmapgen():
    _logger.error('Memory map generation aborted')
    _clean_exit(-1)

def _sigint_handler(signal, frame):
    _logger.error('\nMemory map generation interrupted')
    _clean_exit(0)

def _check_is_int(val, arg):
    try:
        int(val)
    except ValueError:
        _logger.error('%s must be an integer (%s)' % (arg, val))
        _abort_mmapgen()

# ==========================================================================
# Command line arguments
# ==========================================================================

def _parse_args():
    global _args    
    global _parser
    global _config
    
    _parser = argparse.ArgumentParser()

    boards = ['dm36x', 'dm816x', 'dm814x']
    _parser.add_argument('--board',
                       help="Board name. Supported: %s" %
                       ''.join('%s, ' % b for b in boards).rstrip(', '),
                       metavar='<board>',
                       dest='board',
                       choices=boards,
                       required=True)
    
    installation_modes = [MODE_SD, MODE_SD_FS, MODE_SD_SCRIPT, MODE_NAND]
    _parser.add_argument('-m', '--mode',
                       help="Installation mode: %s" % installation_modes,
                       metavar='<mode>',
                       dest='mode',
                       required=True,
                       choices=installation_modes)
    
    _parser.add_argument('--devdir',
                       help="DEVDIR path",
                       metavar='<path>',
                       dest='devdir')
    
    _parser.add_argument('--nand-page-size',
                       help="NAND page size (bytes)",
                       metavar='<size>',
                       dest='nand_page_size',
                       default=None)
    
    _parser.add_argument('--nand-block-size',
                       help="NAND block size (bytes)",
                       metavar='<size>',
                       dest='nand_block_size',
                       default=None)
    
    _parser.add_argument('--draw',
                       help="Draw the memory map",
                       dest="draw",
                       action='store_true',
                       default=False)
    
    _parser.add_argument('-v', '--verbose',
                       help="Enable debug",
                       dest="verbose",
                       action='store_true')
    
    _parser.add_argument('-q', '--quiet',
                       help="As quiet as possible",
                       dest="quiet",
                       action='store_true')
    
    _args = _parser.parse_args()
    
def _check_args():
    if not _args.devdir:
        try:
            _args.devdir = os.environ['DEVDIR']
        except KeyError:
            _logger.error('Unable to obtain the $DEVDIR path from the environment.')
            _clean_exit(-1)
    _args.devdir = _args.devdir.rstrip('/')
            
    bspconfig = '%s/bsp/mach/bspconfig' % _args.devdir.rstrip('/')
    if not os.path.isfile(bspconfig):
        _logger.error('File not found: %s' % bspconfig)
        _clean_exit(-1)
    _config = utils.config.init_global_config(bspconfig)
    
    if _args.nand_block_size:
        _check_is_int(_args.nand_block_size, '--nand-block-size')
        _args.nand_block_size = int(_args.nand_block_size)
    if _args.nand_page_size:
        _check_is_int(_args.nand_page_size, '--nand-page-size')
        _args.nand_page_size = int(_args.nand_page_size)

def _make_mmap():
    mmap = None
    if _args.mode == MODE_SD:
        mmap = SDCardMemoryMap()
    if _args.mode == MODE_SD_FS:
        mmap = SDCardFsMemoryMap()
    if _args.mode == MODE_SD_SCRIPT:
        mmap = SDCardExternalInstallerMemoryMap()
    if _args.mode == MODE_NAND:
        if _args.board == 'dm36x':
            mmap = NandMemoryMapDm36x(_args.devdir,
                                 nand_blk_size=_args.nand_block_size,
                                 nand_page_size=_args.nand_page_size)
        if _args.board == 'dm816x':
            mmap = NandMemoryMapDm816x(_args.devdir,
                                 nand_blk_size=_args.nand_block_size,
                                 nand_page_size=_args.nand_page_size)
        if _args.board == 'dm814x':
            mmap = NandMemoryMapDm814x(_args.devdir,
                                 nand_blk_size=_args.nand_block_size,
                                 nand_page_size=_args.nand_page_size)
    return mmap

# ==========================================================================
# Main logic
# ==========================================================================

def main():
    signal.signal(signal.SIGINT, _sigint_handler)
    signal.signal(signal.SIGTERM, _sigint_handler)
    _parse_args()
    _init_logging()
    _check_args()
    mmap = _make_mmap()
    try:
        mmap.validate_config()
        mmap.generate_mmap()
        mmap.generate_info()
        if _args.draw:
            mmap.draw()
        filename = "%s/images/%s-mmap.config" % (_args.devdir, _args.mode)
        mmap.save(filename)
    except MemoryMapException as e:
        _logger.error(e)
        _abort_mmapgen()
    _clean_exit(0)

if __name__ == '__main__':
    main()
