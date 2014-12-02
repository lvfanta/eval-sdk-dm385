#!/usr/bin/python

import readline
import logging
import sys
import urllib
import urllib2
import json


logging.basicConfig(level=logging.ERROR)

class Command(object):
    def __init__(self, _name, _syntax, _help, _argc, _callback, _extra=None):
        self.name = _name
        self.syntax = _syntax
        self.help = _help
        self.argc = _argc
        self.callback = _callback
        self.extra = _extra
    def __str__(self):
        return "%s\t%s\t%s"%(self.name,self.syntax,self.help)
    def __gt__(self, other):
        return self.name > other.name
    def __lt__(self, other):
        return self.name < other.name

class NetCamCli(object):
    
    def __init__(self):
        self.interactive = True
        self.message = 'NetCam: '
        self.currenturl = 'http://dm365.local/'
        readline.set_completer(self.complete)
        readline.parse_and_bind('tab: complete')
        self.commands = sorted([
            Command('help', 
                    'help [command]', 
                    'Displays the list of available commands. If an argument is provided then the help for the particular command will be displayed', 
                    -1, 
                    self.help), 
            Command('quit', 
                    'quit', 
                    'Quits NetCam client application', 
                    0, 
                    self.quit), 
            Command('exit', 
                    'exit', 
                    'Quits NetCam client application', 
                    0, 
                    self.quit),
            Command('url',
                    'url [URL]',
                    'Sets the URL to send requests to. If no argument is provided then the URL currently configured will be printed. The format is typically http://domain:port',
                    -1,
                    self.url),
            Command('play', 
                    'play', 
                    'Starts camera capture', 
                    0, 
                    self.request),
            Command('stop', 
                    'stop', 
                    'Stops camera capture', 
                    0, 
                    self.request),
            Command('set_bitrate', 
                    'set_bitrate <bitrate>', 
                    'Sets the new target bitrate for the H264 encoder', 
                    1, 
                    self.request,
                    'bitrate'),
            Command('set_framerate', 
                    'set_framerate <framerate>', 
                    'Sets the new framerate to decimate the stream to (in frames per second)', 
                    1, 
                    self.request,
                    'fps'),
            Command('get_info', 
                    'get_info', 
                    'Returns server general information', 
                    0, 
                    self.request)
            ])
    
    def complete(self, text, state):
        response = None
        if state == 0:
            # This is the first time for this text, so build a match list.
            if text:
                self.matches = [c.name 
                                for c in self.commands 
                                if c.name.startswith(text)]
            else:
                self.matches = [c.name for c in self.commands]
            
            logging.debug('%s matches: %s', repr(text) if text else '(emtpy)', self.matches)
        
        try:
            response = self.matches[state]
        except IndexError:
            response = None
        logging.debug('complete(%s, %s) => %s', 
                      repr(text), state, repr(response))
        return response

    def _find_command(self, command):
        for cmd in self.commands:
            if command[0] == cmd.name:
                return cmd
        return None

    # Main loop
    def run(self, argc, argv):
        while (self.interactive):
            if argc == 0:
                command = raw_input(self.message).split()
            else:
                self.interactive = False
                command = argv

            self.process_command(command)

    def process_command(self,command):
        logging.debug ("Attempting to process %s", command)

        cmd = self._find_command(command)
        if not cmd:
            logging.error("Unknown command: %s"%command)
            return

        # Checking for correct number of arguments
        if len(command[1:]) != cmd.argc and cmd.argc != -1:
            print "Error: I need %d argument(s)"%cmd.argc
            return
        
        # Call the actual command
        cmd.callback(command)
        print "Success: %s"%cmd.name

    def quit(self, dummy):
        self.interactive = False

    def help(self, command=None):
        try:
            cmdlist = [self._find_command(command[1:])]
        except (TypeError, IndexError):
            cmdlist = self.commands

        if not cmdlist[0]:
            logging.error("Unknown command: %s", command[1])
            return self.help()

        print "Name\tSyntax\tHelp"
        for cmd in cmdlist:
            print cmd

    def url(self, command):
        try:
            url = command[1]
            self.currenturl = url
            logging.debug("Current URL set to %s",url)
        except IndexError:
            print "Current URL: %s"%self.currenturl

    def request(self, cmdspec):
        cmd = self._find_command(cmdspec)

        if cmd.extra:
            data = {cmd.extra: int(cmdspec[1])}
        else:
            data = {}
        logging.debug ("Using %s as payload", data)
        payload = json.dumps(data)

        url = self.currenturl+'/'+cmd.name
        req = urllib2.Request(url)
        req.add_header('Content-Type', 'application/json')

        try:
            response = urllib2.urlopen(req, payload)
            print response.read()
        except (ValueError,urllib2.URLError) as e:
            print "Error: %s"%e

if __name__ == '__main__':
    argv = sys.argv[1:]
    argc = len(argv)
    cli = NetCamCli()

    cli.run(argc, argv)

