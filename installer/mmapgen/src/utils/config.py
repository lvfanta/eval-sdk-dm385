#!/usr/bin/env python
# ==========================================================================
#
# Copyright (C) 2012-2013 RidgeRun, LLC (http://www.ridgerun.com)
# All Rights Reserved.
#
# Author: Jose Pablo Carballo <jose.carballo@ridgerun.com>
#
# The contents of this software are proprietary and confidential to RidgeRun,
# LLC.  No part of this program may be photocopied, reproduced or translated
# into another programming language without prior written consent of 
# RidgeRun, LLC.
#
# The config module facilitates reading a .config file.
#
# ==========================================================================

"""
The config module facilitates reading a .config file.
"""

# ==========================================================================
# Imports
# ==========================================================================

import ConfigParser

# ==========================================================================
# Globals
# ==========================================================================

_config = None

# ==========================================================================
# Functions
# ==========================================================================

def init_global_config(config_file=None):
    """
    Inits the global :class:`Config` instance.
    
    :param config_file: Path to the configuration file that will be
        tied to the global :class:`Config` instance.
    :returns: The global :class:`Config` instance. 
    """
    
    global _config
    if not _config:
        _config = Config(config_file)    
    return _config

def get_global_config():
    """
    Gets the  global :class:`Config` instance.
    
    :returns: The global :class:`Config` instance. 
    """
        
    return _config

# ==========================================================================
# Private classes
# ==========================================================================

class _FakeSecHead(object):
    """
    Class used to fake a section header in a configuration file.
    
    Source: http://stackoverflow.com/questions/2819696/parsing-properties
    -file-in-python/2819788#2819788
    """
    
    def __init__(self, fp, fakesection='SECTION'):
        self.fp = fp
        self.sechead = '[' + fakesection + ']\n'
        
    def readline(self):
        if self.sechead:
            try:
                return self.sechead
            finally:
                self.sechead = None
        else:
            return self.fp.readline()

# ==========================================================================
# Public classes
# ==========================================================================

class Config(object):
    """
    Class to parse configuration files that follows the format of the
    Linux kernel's .config file. Based on `ConfigParser`.
    
    Sample of a .config file content:
    ::
        ...
        CONFIG_ARM=y
        CONFIG_VECTORS_BASE=0xffff0000
        CONFIG_DEFCONFIG_LIST="/lib/modules/$UNAME_RELEASE/.config"
        CONFIG_CONSTRUCTORS=y
        # CONFIG_SWAP is not set
        ...
    """
    
    def __init__(self, config_file):
        """
        :param config_file: Path to the configuration file that will be
            tied to this instance.
        :raise IOError: Upon failure to open the configuration file.
        """
        
        self.parser  = ConfigParser.RawConfigParser()
        self.section = 'SECTION' 
        self.parser.readfp(_FakeSecHead(open(config_file), self.section))
        
    def has_option(self, option):
        """
        Returns true if an option is present in the configuration file,
        false otherwise.
        """
        
        if self.parser.has_option(self.section, option):
            return True
        else:
            return False
    
    def get(self, option):
        """
        Returns the requested option if exists; None otherwise.
        """
        
        if self.parser.has_option(self.section, option):
            return self.parser.get(self.section, option)
        else:
            return None

    def get_clean(self, option):
        """
        Returns the requested option (stripped, no quotes) if exists;
        None otherwise.
        """
        
        if self.has_option(option):
            return self.get(option).strip('" ')
        else:
            return None
