#!/usr/bin/python
import sys, os, logging, json, urllib, signal
sys.path.append('/usr/lib/python2.7/dist-packages')
from flask import Flask, render_template, send_file, redirect, request, send_from_directory, make_response
import controller

logging.debug("%s starting" % __name__)

####
# Private methods
####

# from http://stackoverflow.com/questions/956867/how-to-get-string-objects-instead-of-unicode-ones-from-json-in-python
def _decode_list(data):
    rv = []
    for item in data:
        if isinstance(item, unicode):
            item = item.encode('utf-8')
        elif isinstance(item, list):
            item = _decode_list(item)
        elif isinstance(item, dict):
            item = _decode_dict(item)
        rv.append(item)
    return rv

def _decode_dict(data):
    rv = {}
    for key, value in data.iteritems():
        if isinstance(key, unicode):
            key = key.encode('utf-8')
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        elif isinstance(value, list):
            value = _decode_list(value)
        elif isinstance(value, dict):
            value = _decode_dict(value)
        rv[key] = value
    return rv

# REVISIT: replace with yaml.loads(data)
# until then, this logic handles unicode
def _loads(data):
    try:
        return json.loads(data, object_hook=_decode_dict)
    except:
        logging.error("Could not decode JSON encoded data: %s" % data)
        return None

app = Flask(__name__, static_folder='templates', static_url_path='')
cntlr = controller.Controller()

@app.route('/')
def home():
    """Render homepage and startup server."""
    logging.debug("Home page requested")
    return render_template('netcam.html')

@app.route('/play', methods=['POST'])
def play():
    """Streams live video out using RTP protocol."""
    parms = _loads(request.data)
    return json.dumps(cntlr.play(parms))

@app.route('/stop', methods=['POST'])
def stop():
    """Stops live streaming."""
    parms = _loads(request.data)
    return json.dumps(cntlr.stop(parms))

@app.route('/set_bitrate', methods=['POST'])
def set_bitrate():
    """Sets the video encoder bitrate. Accepts dictionary with member 'bitrate'"""
    parms = _loads(request.data)
    return json.dumps(cntlr.set_bitrate(parms))

@app.route('/set_framerate', methods=['POST'])
def set_framerate():
    """Sets the video framerate in frames per second. Accepts dictionary with member 'fps'"""
    parms = _loads(request.data)
    return json.dumps(cntlr.set_framerate(parms))

# =============================================================================
# App independent API
# =============================================================================
@app.route('/get_info', methods=['POST'])
def get_info():
    """Get general server info."""
    parms = _loads(request.data)
    return json.dumps(cntlr.get_info(parms))

# =============================================================================
# Standalone, startup development server
# =============================================================================

if __name__ == '__main__':
    from logging.handlers import SysLogHandler
    sys.path.append('/usr/share/pyshared')
    from flup.server.fcgi import WSGIServer

    def handle_signals(signal, frame) :
        """Closes all open resources and exits"""
        logging.debug("Shutting down controller")
        logging.debug("Exiting %s" % __name__)
        cntlr.fini()
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

    logging.debug("%s starting" % program_name)
    logging.debug("Starting python HTTP server outside web server for code development")

    app.run(host='0.0.0.0', port=88, threaded=True)
