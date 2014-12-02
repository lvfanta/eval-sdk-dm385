#!/usr/bin/python
import sys, os, logging, ConfigParser
import unittest

import pygst
pygst.require('0.10')
import gst
import gobject
gobject.threads_init ()

import threading

logging.debug("%s starting" % __name__)

"""
RidgeRun module to expose GStreamer pipelines in a python friendly manner.
"""

class Streamer(object):
    """
    Streamer encapsulates the GStreamer audio / video streaming framework into
    a much simplier API.  Text representations of pipelines are read from a 
    configuration file.  Each pipeline can be controlled individually along
    with each of the element's parameters that are in a pipeline.  Streamer 
    works best if you avoid using tee elements and mux elements and instead 
    break the pipeline down into segments which are connected using the 
    interpipe elements.
    """

    # Pipeline states
    STATE_NULL = 0
    STATE_PAUSED = 1
    STATE_PLAY = 2
    STATE_ERROR = -1
    
    def _state_to_gst(self, state):
        """ Convert Streamer state into GStreamer state."""

        retstate = None

        if self.STATE_NULL == state:
            retstate = gst.STATE_NULL
        elif self.STATE_PAUSED == state:
            retstate = gst.STATE_PAUSED
        elif self.STATE_PLAY == state:
            retstate = gst.STATE_PLAYING
        
        return retstate

    def _gst_to_state(self, gststate):
        """ Convert GStreamer state into Streamer state."""
        retstate = None

        if gst.STATE_NULL == gststate:
            retstate = self.STATE_NULL
        elif gst.STATE_PAUSED == gststate:
            retstate = self.STATE_PAUSED
        elif gst.STATE_PLAY == gststate:
            retstate = self.STATE_PLAYING

        return retstate

    class Pipeline(object):
        """Container for an individual pipeline.  No exposed methods."""

        name = None
        pipeline = None
        desc = None
    
    def __init__(self):
        """Start glib main loop."""
        logging.debug("Creating streamer object")
        self.pipelines = {};
        self.mainloop = gobject.MainLoop()
        self.mainloop_thread = threading.Thread(target=self.mainloop.run, name="mainloop")
        self.mainloop_thread.start() # Start gobject mainloop in separate thread

    def fini(self):
        """Release resources used by all pipeline and stop glib main loop."""

        self.__del__()

    def __del__(self):
        logging.debug("Destroying streamer object")
        self.pipelines = None
        if self.mainloop:
            self.mainloop.quit()
        self.mainloop = None
        if self.mainloop_thread:
            self.mainloop_thread.join()
        self.mainloop_thread = None

    def load_pipelines(self, pipedescs, group, build=True):
        """
        Loads a group of pipelines from a config file.  The config file is in 
        python ConfigParser format; a set of named groups containing named pipelines.
        Each pipeline can be controlled using the name assigned in the config file.
        :param pipedescs: config filename.  File needs to be in python ConfigParser format.
        :param group: config file group name specifying which pipelines are used.
        :param build: if set to true then the pipelines are built and left in the null state.
        """

        logging.debug("Loading %s pipelines from %s"%(pipedescs, group))

        if not os.path.isfile(pipedescs):
            logging.error("Unable to find %s"%pipedescs)
            return -1

        parser = ConfigParser.ConfigParser()
        parser.read(pipedescs)

        if not parser.has_section(group):
            logging.error("%s doesn't contain the %s group"%(pipedescs,group))
            return -1

        for name,desc in parser.items(group):
            logging.debug("Loaded pipeline %s"%name)
            pipe = self.Pipeline()
            pipe.name = name
            pipe.desc = desc
            self.pipelines[name] = pipe

        if build:
            self._build_pipelines(self.pipelines)

        return 0

    def _build_pipelines(self, pipelines):
        """
        Builds all the pipelines in the dictionary converting the text representation of 
        each GStreamer pipeline into a controllable GStreamer pipeline.
        :param pipelines: dictionary of Pipelines to build.
        :return: dictionary of return status values for each pipeline that was constructed.
        """
        ret = {}

        if not pipelines:
            logging.warning("Attempted to build invalid pipeline dictionary")
            return ret

        for name,pipe in pipelines.items():
            logging.debug("Building pipeline %s"%name)
            try:
                pipe.pipeline = gst.parse_launch(pipe.desc)
                bus = pipe.pipeline.get_bus()
                bus.add_watch(self._bus_callback)
                ret[name] = 0
            except gobject.GError as e:
                logging.error("Unable to build %s: %s", name, e)
                pipe.pipeline = None
                ret[name] = -1
            
        return ret

    def pipeline_set_state(self, requested_states):
        """                                                                  
        Set the pipelines' state. The only parameter,
        requested_state, is a dictionary where the keys are the name
        of the pipelines to modify and the values are the Pipeline.STATE_*
        states to set them to. The special name "all" sets all the
        pipelines to a given state. "all" may be used in combination with
        pipeline names in order to set most of the pipelines to a given
        state, but specify a few other pipelines by name to set them to 
        a different state.
        :requested_states: dictionary of requested states
        :return: dictionary of return status values for each pipeline whose state was changed.
        """                                                                  
        
        # First ask if "all" is going to be used and build the dictionary
        globaldict = {}
        if "all" in requested_states:
            globalstate = requested_states["all"]
            globaldict = {key:globalstate for key in self.pipelines}
            
        ret = {}
        for name,state in requested_states.items():
            if name in self.pipelines:
                ret[name] = self._set_state(name, state)
            elif name is "all":
                ret = self.pipeline_set_state(globaldict)
            else:
                logging.warning("Nonexistent pipeline: %s"%name)
                ret[name] = -1

        return ret

    def pipeline_get_state(self, requested_pipes):
        """
        Gets the current state of one or more pipelines.  The special 
        name "all" will query the state of all the pipelines; this 
        name may not be used in combination with other names.
        :param requested_pipe: dictionary who's keys are the names of the pipelines to query.
        :return: dictionary of return pipeline states for each pipeline listed in requested_pipes.
        """
        ret = {}
        
        # First process the special "all" pipe name
        if "all" in requested_pipes:
            if len(requested_pipes) > 1:
                logging.error("The special name \"all\" may not be used in combination with other pipeline names")
                ret = {"all": -1}
            else:
                ret = {key:self._get_state(key) for key in self.pipelines}
                
            return ret

        # This is the "normal" case where pipelines are specifically requested
        for name in requested_pipes:
            if name not in self.pipelines:
                logging.error("Nonexistent pipeline %s", name)
                ret[name] = -1
            else:
                state = self._get_state(name)
                logging.debug("Returning pipe %s with state %d", name, state)
                ret[name] = state

        return ret
            

    def pipeline_set_parameter(self, requested_parameters):
        """
        Sets the given parameters on the given elements of the given
        pipelines.
        :param requested_parameters: is a dictionary of dictionaries in 
        the following format
        
        requested_parameters= 
        {
          "pipe1_name" : {
                           "element1_name" : {
                                               "param1_name": param1_value,
                                               "param2_name": param2_value
                                             },
                           "element2_name" : {
                                               "param1_name": param1_value
                                             }
                         },
          "pipe2_name" : {
                           "element1_name: {
                                             "param1_name": param1_value,
                                 .
                                 .
                                 .
                                           }
                         }
        }

        :return: the requested_parameters dictionary but with the values that were actually set.
        """
        return self._manage_parameters(requested_parameters, True)

    def pipeline_get_parameter(self, requested_parameters):
        """
        Queries the given parameters on the given elements of the given
        pipelines.
        :param requested_parameters: is a dictionary of dictionaries
        in the following format
        
        requested_parameters= 
        {
          "pipe1_name" : {
                           "element1_name" : {
                                               "param1_name": None,
                                               "param2_name": None
                                             },
                           "element2_name" : {
                                               "param1_name": None
                                             }
                         },
          "pipe2_name" : {
                           "element1_name: {
                                             "param1_name": None,
                                 .
                                 .
                                 .
                                           }
                         }
        }

       :return: the requested_parameters dictionary but with the current values set.
       """
        return self._manage_parameters(requested_parameters, False)

    def _manage_parameters(self, requested_parameters, setparam):
        """
        Optionally sets element parameters and then queries the actual value.
        :param requested_parameters: is a dictionary of dictionaries
        :param setparm: if set to true, the parameters are set before the current value is retrieved.
        :return: the requested_parameters dictionary but with the current values set.
        """

        ret = requested_parameters.copy()

        for pipe_name,elements in requested_parameters.items():
            # Test for pipeline existence
            if pipe_name not in self.pipelines:
                logging.error("Non existent pipeline: %s"%pipe_name)
                ret[pipe_name] = -1
                continue
            else:
                pipe = self.pipelines[pipe_name].pipeline
            
            for element_name, params in elements.items():
                # Test for element existence
                if not self._has_element(pipe, element_name):
                    logging.error("Non existent element %s on pipeline %s"%(element_name,pipe_name))
                    ret[pipe_name][element_name] = -1
                    continue
                else:
                    element = pipe.get_by_name(element_name)

                for param_name, value in params.items():
                    #Test for parameter existence
                    if not self._has_param(element, param_name):
                        logging.error("Non existent parameter %s on element %s on pipeline %s"%(param_name,element_name,pipe_name))
                        ret[pipe_name][element_name][param_name] = -1
                        continue
                    else:
                        if setparam:
                            logging.debug("Setting %s on %s of %s to %s"%(param_name, element_name, pipe_name, value))
                            element.set_property(param_name, value)
                        ret[pipe_name][element_name][param_name] = element.get_property(param_name)

        return ret

    def _has_element(self, pipe, elementname):
        """Returns true if pipe has an element named elementname"""

        exists = pipe.get_by_name(elementname)
        if exists:
            return True
        else:
            return False

    def _has_param(self, element, paramname):
        """Returns true if element has an parameter named paramname"""

        # Hyphens are replaced with underscores on property names
        newparam = paramname.replace('-', '_')

        return newparam in dir(element.props)
            
    def _set_state(self, name, state):
        """Sets the state of a named pipeline"""

        gststate = self._state_to_gst(state)
        pipe = self.pipelines[name]
        gstret = pipe.pipeline.set_state(gststate)

        if gst.STATE_CHANGE_FAILURE == gstret:
            logging.error("Failed to set %s to %d"%(name, state))
            ret = -1
        else:
            logging.debug("Successfully set %s to %d"%(name, state))
            ret = 0
        
        return ret                    

    def _get_state(self, name):
        """Gets the state of a named pipeline"""

        pipe = self.pipelines[name]
        if not pipe.pipeline:
            logging.error("Pipeline %s is not properly built")
            state = self.STATE_ERROR
            return state

        gststates = pipe.pipeline.get_state()

        state = self._gst_to_state(gststates[1])
        if state != None:
            logging.debug("Queried state %d for pipe %s"%(state, name))
        else:
            logging.error("Invalid state on pipe %s"%name)
            state = self.STATE_ERROR

        return state

    def _bus_callback(self, bus, message):
        """
        Message bus callback. This function will be called by GStreamer to 
        receive various messages and notify user about important ones. It is 
        also used to receive EOS notifications meaning file completion in 
        filesink based pipelines.
        """
        _type = message.type
        _src = message.src.get_name()

        if gst.MESSAGE_INFO == _type:
            error, debug = message.parse_info()
            logging.info("%s: %s"%(_src,debug))
        elif gst.MESSAGE_ERROR == _type:
            error, debug = message.parse_error()
            logging.error("%s: %s:%s"%(_src,error,debug))

        return True

# =============================================================================
# Unit tests cases
# =============================================================================
class TestStreamer(unittest.TestCase):
    def setUp(self):
        self.streamer = Streamer()
        
    def test_load_pipelines(self):
        logging.info ("===Testing load_pipelines===");

        # Testing invalid files
        self.assertEqual(self.streamer.load_pipelines("invalid file name", None, False), -1);

        # Testing invalid groups
        self.assertEqual(self.streamer.load_pipelines("pipelines.gst", "invalid-group", False), -1);

        # Testing correct loading
        self.streamer.load_pipelines("pipelines.gst", "Test", False)
        self.assertEqual(len(self.streamer.pipelines), 3);
        self.assertEqual(self.streamer.pipelines['mockpipeline'].desc, 'mockdescription')

    def test_build_pipelines(self):
        logging.info ("===Testing build_pipelines===")

        self.streamer.load_pipelines("pipelines.gst", "Test", False)
        pipelines = self.streamer.pipelines
        ret = self.streamer._build_pipelines(pipelines)

        self.assertEqual(ret['mockpipeline'], -1)
        self.assertEqual(pipelines['mockpipeline'].pipeline, None)
        self.assertEqual(ret['realpipeline'], 0)
        self.assertEqual(type(pipelines['realpipeline'].pipeline), gst.Pipeline)


    def test_pipeline_set_state(self):
        logging.info ("===Testing set state===")
        
        self.streamer.load_pipelines("pipelines.gst", "Test")
        self.streamer._build_pipelines(self.streamer.pipelines)

        # Testing individual states
        states = {'realpipeline': Streamer.STATE_PLAY, 'failpipeline': Streamer.STATE_PLAY}
        ret = self.streamer.pipeline_set_state(states)
        self.assertEqual(ret['realpipeline'], 0)
        self.assertEqual(ret['failpipeline'], -1)

        # Testing global state
        del self.streamer.pipelines['mockpipeline']
        ret = self.streamer.pipeline_set_state({'all': Streamer.STATE_NULL})
        self.assertEqual(ret['realpipeline'], 0)
        self.assertEqual(ret['failpipeline'], 0)
        x,realstate,x = self.streamer.pipelines['realpipeline'].pipeline.get_state()
        x,failstate,x = self.streamer.pipelines['failpipeline'].pipeline.get_state()
        self.assertEqual(realstate, gst.STATE_NULL)
        self.assertEqual(failstate, gst.STATE_NULL)

    def test_pipeline_get_state(self):
        logging.info ("===Testing get state===")

        self.streamer.load_pipelines("pipelines.gst", "Test")

        # Testing global state
        ret = self.streamer.pipeline_get_state({'all': None})
        self.assertEqual(len(ret), 3)
        self.assertEqual(ret['mockpipeline'], -1)
        self.assertEqual(ret['realpipeline'], Streamer.STATE_NULL)

        # Speciall "all" pipeline should be unique
        ret = self.streamer.pipeline_get_state({'all':None, 'mockpipeline': None})
        self.assertEqual(ret['all'], -1)
        self.assertEqual(len(ret), 1)
        
        # Specific pipeline query
        ret = self.streamer.pipeline_get_state({'nonexistent':None, 'realpipeline':None})
        self.assertEqual(ret['nonexistent'], -1)
        self.assertEqual(ret['realpipeline'], Streamer.STATE_NULL)
        self.assertEqual(len(ret), 2)

    def test_pipeline_set_parameter(self):
        logging.info ("===Testing set_parameter===")
        
        self.streamer.load_pipelines("pipelines.gst", "Test")

        ret = self.streamer.pipeline_set_parameter({"realpipeline": {"fakesrc0": {"num-buffers": 1, "failureparam": True}, "failureelement":{}}, "failurepipeline": {}})
        self.assertEqual(ret['realpipeline']['fakesrc0']['num-buffers'], 1)
        self.assertEqual(ret['realpipeline']['fakesrc0']['failureparam'], -1)
        self.assertEqual(ret['realpipeline']['failureelement'], -1)
        self.assertEqual(ret['failurepipeline'], -1)

    def test_pipeline_get_parameter(self):
        logging.info ("===Testing get_parameter===")
        
        self.streamer.load_pipelines("pipelines.gst", "Test")

        ret = self.streamer.pipeline_get_parameter({"realpipeline": {"fakesrc0": {"name": None}}})
        self.assertEqual(ret['realpipeline']['fakesrc0']['name'], 'fakesrc0')

    def tearDown(self):
        self.streamer.fini()
        del self.streamer

    

if __name__ == '__main__':
    from logging.handlers import SysLogHandler

#    sysloghandler = SysLogHandler(address='/dev/log')
    sysloghandler = SysLogHandler()
    sysloghandler.setLevel(logging.DEBUG)
    sysloghandler.setFormatter(logging.Formatter('%(levelname)s:%(filename)s:%(lineno)s: %(msg)s'))

    logger = logging.getLogger('')
    logger.addHandler(sysloghandler)
    logger.setLevel(logging.DEBUG)

    unittest.main()
    
        
