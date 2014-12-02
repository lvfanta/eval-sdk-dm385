#!/usr/bin/python
import sys, os, logging, streamer, platform, socket, ConfigParser

logging.debug("%s starting" % __name__)

class Controller(object):
    """
    RidgeRun network camera supporting both live video with controls using a 
    web browser or camera control using JSON HTTP commands.
    """
    sms = None
    mach = None
    info = {}
    props = {}
    infofile = "/tmp/netcam.info"
    
    properties = {
        'x86_64': { 
            'fps': 'max-rate',
            'bitrate': 'bitrate',
            'source': 'listen-to'
            },
        'armv5tejl': {
            'fps': 'max-rate',
            'bitrate': 'targetbitrate',
            'source': 'listen-to'
            }
        }

    def __init__(self):
        logging.debug("Creating controller object")
        self.sms= streamer.Streamer()

        # One time server info retrieval
        self.info = self.get_info(None)
            
        # Save machine dependent properties
        self.props = self.properties[self.info['mach']]
        
        self.sms.load_pipelines("pipelines.gst", self.info['mach'])

        # Set defaults
        self.sms.pipeline_set_parameter({'unicast': {'src': {self.props['source']: 'camera'}}})

        #To reduce lag when starting pipe we set it to PAUSED
        self.sms.pipeline_set_state({'all': self.sms.STATE_PAUSED})
        
    def play(self, parms):
        """Streams live video out using RTP protocol."""
        logging.debug("play(%s)" % parms)
        results = {}
        results["status"] = self.sms.pipeline_set_state({'all': self.sms.STATE_PLAY})['camera']
        return results

    def stop(self, parms):
        """Stops live streaming."""
        logging.debug("stop(%s)" % parms)
        results = {}
        results["status"] = self.sms.pipeline_set_state({'all': self.sms.STATE_PAUSED})['camera']
        return results

    def set_bitrate(self, parms):
        """Sets the video encoder bitrate. Accepts dictionary with member 'bitrate'"""
        logging.debug("set_bitrate(%s)" % parms)
        results = {}
        results["status"] = 0

        rate = parms.get("bitrate")
        if rate == None:
             logging.error("Missing bitrate parameter")
             results["status"] = -1
        else:
            newparams = self.sms.pipeline_set_parameter({'unicast': {'encoder': {self.props['bitrate']: rate}}})
            if rate == newparams['unicast']['encoder'][self.props['bitrate']]:
                results["status"] = 0
            else:
                results["status"] = -1

        return results

    def set_framerate(self, parms):
        """Sets the video framerate in frames per second. Accepts dictionary with member 'fps'"""
        logging.debug("set_framerate(%s)" % parms)
        results = {}
        results["status"] = 0

        fps = parms.get("fps")
        if fps == None:
             logging.error("Missing fps parameter")
             results["status"] = -1
        else:
            newparams = self.sms.pipeline_set_parameter({'unicast': {'videorate': {self.props['fps']: fps}}})
            if fps == newparams['unicast']['videorate'][self.props['fps']]:
                results["status"] = 0
            else:
                results["status"] = -1

        return results

    def get_info(self, parms):
        info = {}
        if not self.info:
            parser = ConfigParser.ConfigParser()
            parser.read(self.infofile)
            # Convert to a dictionary
            for key,value in parser.items('info'):
                info[key] = value
            logging.info ("Parsed server info: %s"%info)
        else:
            info = self.info

        return info

    def fini(self):
        self.__del__()

    def __del__(self):
        logging.debug("Freeing controller object")
        if self.sms:
            self.sms.pipeline_set_state({'all': self.sms.STATE_NULL})
            self.sms.fini()
            self.sms = None
        

# =============================================================================
# Unit tests cases
# =============================================================================

if __name__ == '__main__':
    import signal
    from logging.handlers import SysLogHandler
    sys.path.append('/usr/share/pyshared')
    from flup.server.fcgi import WSGIServer

    def handle_signals(signal, frame) :
        """Closes all open resources and exits"""
        logging.debug("Shutting down controller")
        controller.fini()
        logging.debug("Exiting %s" % __name__)
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_signals)
    signal.signal(signal.SIGINT, handle_signals)

    program_name = os.path.basename(sys.argv[0])

#    sysloghandler = logging.handlers.SysLogHandler(address='/dev/log')
    sysloghandler = logging.handlers.SysLogHandler()
    sysloghandler.setLevel(logging.DEBUG)
    sysloghandler.setFormatter(logging.Formatter('%(levelname)s:%(filename)s:%(lineno)s: %(msg)s'))

    logger = logging.getLogger('')
    logger.addHandler(sysloghandler)
    logger.setLevel(logging.DEBUG)

    logging.debug("Unit tests for %s" % program_name)
