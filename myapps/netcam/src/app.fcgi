#!/usr/bin/python
# Copyright (C) 2014 RidgeRun, LLC (http://www.ridgerun.com)
import sys, os, logging
from logging.handlers import SysLogHandler
sys.path.append('/usr/share/pyshared')
from flup.server.fcgi import WSGIServer

sys.path.append('/usr/share/netcam')
from app import app

program_name = os.path.basename(sys.argv[0])

sysloghandler = logging.handlers.SysLogHandler(address='/dev/log')
sysloghandler.setLevel(logging.DEBUG)
sysloghandler.setFormatter(logging.Formatter('%(levelname)s:%(filename)s:%(lineno)s: %(msg)s'))

logger = logging.getLogger('')
logger.addHandler(sysloghandler)
logger.setLevel(logging.DEBUG)

logging.debug("%s starting" % program_name)

WSGIServer(app).run()
