#!/usr/bin/env python
#
###############################################################################
#   - Mini Automation Server (MAS) -
#
#   Author: Joel Eriksson (joel.a.eriksson@gmail.com)
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
###############################################################################
   
from ctypes import util
from ctypes import *
from threading import Timer
from datetime import datetime, timedelta
import getopt, sys, time, threading, re, logging, sunstate, bottle, json, os
import signal, shutil

__version__ = "1.2.3"

###############################################################################
# TELLDUS TELLSTICK LIBRARY
###############################################################################
class TelldusLibrary:
    DIM_LEVEL_MIN = 0
    DIM_LEVEL_MAX = 255
    TURNON  = 1
    TURNOFF = 2
    BELL    = 4
    TOGGLE  = 8
    DIM     = 16
    LEARN   = 32
    ALL_METHODS = TURNON | TURNOFF | BELL | TOGGLE | DIM | LEARN
    PARAMETERS = ["devices", "house", "unit", "code", "system", "units", "fade"]

    def __init__(self):
        library_name = "TelldusCore"
        if sys.platform == "linux2":
            library_name = "telldus-core"

        library_location = util.find_library(library_name)
        if library_location == None:
            raise Exception()

        if sys.platform == "win32":
            self.library = windll.LoadLibrary(library_location)
        else:
            self.library = cdll.LoadLibrary(library_location)

        self.library.tdGetName.restype = c_char_p
        self.library.tdSetName.argtypes = [ c_int, c_char_p ]
        self.library.tdSetName.restype = c_int
        self.library.tdLastSentValue.restype = c_char_p
        self.library.tdGetProtocol.restype = c_char_p
        self.library.tdSetProtocol.argtypes = [ c_int, c_char_p ]
        self.library.tdGetModel.restype = c_char_p
        self.library.tdSetModel.argtypes = [ c_int, c_char_p ]
        self.library.tdGetDeviceParameter.argtypes = [ c_int, c_char_p, c_char_p]
        self.library.tdGetDeviceParameter.restype = c_char_p
        self.library.tdSetDeviceParameter.argtypes = [ c_int, c_char_p, c_char_p]
        self.library.tdGetErrorString.restype = c_char_p
        self.library.tdLastSentValue.restype = c_char_p

    def get_device_IDs(self):
        devices = []
        number_devices = self.library.tdGetNumberOfDevices()
        for i in range(number_devices):
            devices.append(int(self.library.tdGetDeviceId(i)))
        return devices
    
    def new_device(self):
        device_id = self.library.tdAddDevice();
        if(device_id < 0):
            error_msg = self.library.tdGetErrorString(device_id)
            raise Exception("Could create new device.\n\n" + error_msg)
        return device_id
        
    def supports_on_off(self, device_id):
        if((self.library.tdMethods(device_id,self.TURNON)  & self.TURNON) and
           (self.library.tdMethods(device_id,self.TURNOFF) & self.TURNOFF)):
            return True
        else:
            return False

    def supports_dim(self, device_id):
        if(self.library.tdMethods(device_id,self.DIM) & self.DIM):
            return True
        else:
            return False
        
    def supports_learn(self, device_id):
        if(self.library.tdMethods(device_id,self.LEARN) & self.LEARN):
            return True
        else:
            return False
            
    def get_name(self, device_id):
        name = self.library.tdGetName(device_id)
        return name

        
    def set_name(self, device_id, name):
        logging.debug("Change name of device " + str(device_id) + " to : " + name)
        encoded_name = name.encode('utf-8')
        if(self.library.tdSetName(device_id, encoded_name) == 0):
             raise Exception("Could not change device name '" + name.strip() + 
                             "'. Secure that tellstick.conf is writeable.")

    def delete_device(self, device_id):
        logging.debug("Deleting device " + str(device_id))
        if(self.library.tdRemoveDevice(device_id) == 0):
             raise Exception("Could not delete device with id '" + str(device_id) + 
                             "'. Secure that tellstick.conf is writeable.")

    def get_protocol(self, device_id):
        return self.library.tdGetProtocol(device_id)
       
    def set_protocol(self, device_id, protocol):
        if(self.library.tdSetProtocol(device_id, protocol) == 0):
             raise Exception("Could set device protocol for '" + str(device_id) + 
                             "'. Secure that tellstick.conf is writeable.")

    def get_model(self, device_id):
        return self.library.tdGetModel(device_id)

    def set_model(self, device_id, model):
        if(self.library.tdSetModel(device_id, model) == 0):
             raise Exception("Could set device model for '" + str(device_id) + 
                             "'. Secure that tellstick.conf is writeable.")
        
    def get_parameters(self, device_id):
        result = {}
        for parameter in self.PARAMETERS:
            result[parameter] = self.library.tdGetDeviceParameter(device_id, parameter, "")
        return result
        
    def set_parameters(self, device_id, parameters):
        for parameter, value in parameters.items():
            if(parameter not in self.PARAMETERS):
                raise Exception("Unknown parameter '" + parameter + "'")
            if(self.library.tdSetDeviceParameter(device_id, parameter, value) == 0):
                if (value != ""):
                    raise Exception("Could set device parameter '" + parameter + 
                                    "' to '" + value +"' for device '" + 
                                    str(device_id) + "'.")        
                             
    def turn_on(self,devices):
        ''' Turn on one or more devices. Will try on all IDs. 
               devices -- List of device IDs to turn on       '''
        for device in devices:     
            if(self.supports_on_off(device)):
                logging.debug("Turning ON device " + str(device))
                self.library.tdTurnOn(device)
            else:
                logging.warning(str(device) + " cannot be turned on")
    
    def turn_off(self,devices):
        ''' Turn off one or more devices. Will try on all IDs. 
               devices -- List of device IDs to turn off       '''
        for device in devices:
            if(self.supports_on_off(device)):
                logging.debug("Turning OFF device " + str(device))
                self.library.tdTurnOff(device)
            else:
                logging.warning(str(device) + " cannot be turned off")     
                
    def dim(self,devices,dim_level):
        ''' Dim one or more devices. Will try on all IDs. 
               devices   -- List of device IDs to dim        
               dim_level -- Integer between 0-255          '''
        if((dim_level < self.DIM_LEVEL_MIN) or 
           (dim_level > self.DIM_LEVEL_MAX)):
            logging.warning("Dim level: '" + str(dim_level) + "' not valid")
        else:
            for device in devices:
                if(self.supports_dim(device)):
                    logging.debug("Dimming device " + str(device) + " to level " + str(dim_level))
                    self.library.tdDim(device,dim_level)
                else:
                    logging.warning(str(device) + " cannot be dimmed")
    
    def learn(self,devices):
        ''' Learn one or more devices. Will try on all IDs. 
               devices -- List of device IDs to learn       '''
        for device in devices:
            if(self.supports_learn(device)):
                logging.debug("Send LEARN to device " + str(device))
                self.library.tdLearn(device)
            else:
                logging.warning(str(device) + " cannot be learned")    
  
    def last_cmd_was_on(self, device_id):
        ''' True if last command sent to the device was on.
            Note that this don't necessary means that the device is on since
            the device could have been turned off by something else than the
            Tellstick. '''
        return (self.library.tdLastSentCommand(device_id, 1) == 1)
        
    def last_dim_level(self, device_id):
        ''' Return the last dim level sent to the device.
            Note that this don't necessary means that the device currently 
            has this dim value since device could have been dimmed by  
            something else than the Tellstick. ''' 
        try:
            value = int(self.library.tdLastSentValue(device_id))
        except:
            value = 0
        return value     
        
###############################################################################
# LOAD CONFIGURATION FILE HANDLING
###############################################################################
def parse_LAT_LONG(line):
    words = line.split()
    if(len(words) != 3):
        raise Exception("LAT_LONG must have 2 arguments\n   " + 
                        " | ".join(words))
    
    lat = float(words[1])
    long = float(words[2])
    
    return [lat, long]

def parse_EVENT_offset(s):
    result = 0
    offset = s.split('+')
    if(len(offset)>1):
        result = int(round(float(offset[1])*60,0))
    else:
        offset = s.split('-')
        if(len(offset)>1):
            result = int(round(float(offset[1])*-60,0))
    if((result <= -(24*60)) or (result >= (24*60))):
        raise Exception("Offset must be > -24 and < 24\n   " + s)
    return result
    
def parse_EVENT(line, control_library, groups, lat_long_is_set = True):
    hour   = 0
    minute = 0
    weekday =  None
    restriction = 0
    function = None
    
    words = line.split()
    if((len(words) < 3) or (len(words) > 5)):
        raise Exception("EVENT must have 3 - 5 arguments\n   " + 
                        " | ".join(words))
        
    # Parse <time>
    if(words[1].startswith("Sunrise")):
        if(not lat_long_is_set):
            raise Exception("Sunrise requires LAT_LONG to be set\n   " + line)
        hour = TimeEvent.TIME_SUNRISE
        minute = parse_EVENT_offset(words[1])
    elif(words[1].startswith("Sunset")):
        if(not lat_long_is_set):
            raise Exception("Sunset requires LAT_LONG to be set\n   " + line)
        hour = TimeEvent.TIME_SUNSET
        minute = parse_EVENT_offset(words[1])
    else:
        time = words[1].split(":")
        if(len(time) != 2):
            raise Exception("time should be HH:MM\n   " + line)
        hour = int(time[0])
        if((hour < 0) or (hour > 24)):
                raise Exception("hour must be 0 to 24\n   " + line)
        minute = int(time[1])
        if((minute < 0) or (minute > 60)):
                raise Exception("minute must be 0 to 60\n   " + line)
    
    # Parse <dayofweek> 
    word_index = 2
    if((len(words)>3) and (words[2] != "Sunup") and (words[2] != "Sundown")):
        weekday = [False, False, False, False, False, False, False]
        weekday_text = ["Mon","Tue","Wen","Thu","Fri","Sat","Sun"]
        days = words[2].split("/")
        for day in days:
            try:
                weekday[weekday_text.index(day)]=True
            except:
                raise Exception("'" + day + "' is not a valid day\n   " + 
                line)
        word_index = 3
        
    # Parse <restriction>
    if(len(words) == (word_index + 2)):
        if(words[word_index]=="Sunup"):
            if(not lat_long_is_set):
                raise Exception("Sunup requires LAT_LONG to be set\n   " + line)
            restriction = TimeEvent.RESTRICTION_SUNUP
        elif(words[word_index]=="Sundown"):
            if(not lat_long_is_set):
                raise Exception("Sundown requires LAT_LONG to be set\n   " + line)
            restriction = TimeEvent.RESTRICTION_SUNDOWN 
        else:
            raise Exception("invalid restriction. Valid values are "+ 
            "'Sunup' or 'Sundown'\n   "    + line)
        word_index = word_index + 1
                    
    # Parse <function>
    function_name_parameter = words[word_index].split("(")
    function_name = function_name_parameter[0]
    function_parameters = function_name_parameter[1].strip(")").split(",")
    if(function_parameters[0].startswith('G')):
        # Parse <groupid>
        groupid = int(function_parameters[0][1:])
        group = groups.get(groupid)
        if(group == None):
            raise Exception("group '"+groupid+"' does not exist.\n   " 
            + line)    
        devices = group
    else:
        devices = int(function_parameters[0])
    parameter2 = -1
    if(len(function_parameters) == 2):
        parameter2 = int(function_parameters[1]) 
        
    if(function_name == "on"):
        function = FunctionOn(devices, control_library)
    elif(function_name == "off"):
        function = FunctionOff(devices, control_library)
    elif(function_name == "dim"):
        function = FunctionDim(devices, parameter2, control_library)
    else:
        raise Exception("invalid function " + function_name + 
        "\n   " +line) 
    
    return TimeEvent(hour, minute, weekday, restriction, function)

def parse_GROUP(line):
    name = ""
    groupid = 0    
    devices = []

    #Parse name
    name_split = line.split('"')
    if(len(name_split) != 3):
        raise Exception('group name missing. Must be within "".\n   '
        + line)    
    name = name_split[1]
 
    #Parse group id
    id_split = name_split[0].split()
    if(len(id_split) != 2):
        raise Exception('group id is missing missing.\n   '
        + line)
    if(id_split[1].startswith('G')):
        groupid = int(id_split[1][1:])
    else:
        groupid = int(id_split[1])

    #Parse device id:s
    device_split = name_split[2].split()
    if(len(device_split) == 0):
        raise Exception('at least one device id must be given.\n   '
        + line)    
    for device in device_split:
        devices.append(int(device))
    
    return Group(groupid, name, devices)
    
def load_config_file(filename, control_library, events, groups):
    line_nbr = 0
    lat_long = None
    try:
        fo = open(filename,"r")
    except Exception:
        raise Exception("Unable to open: " + filename + "\nUse -? for options")
    try:
        for line_nbr, line in enumerate(fo):
            word_list = line.split()
            if (len(word_list) > 0):
                first_word = word_list[0]
                if (first_word.startswith("#")):
                    pass
                elif (first_word == "LAT_LONG"):
                    lat_long = parse_LAT_LONG(line)
                elif (first_word == "EVENT"):
                    event = parse_EVENT(line, control_library, groups, 
                                        lat_long != None)
                    events.append(event)
                elif (first_word == "GROUP"):
                    group = parse_GROUP(line)
                    if(not groups.add(group)):
                        raise Exception("group '" + group.id + 
                        "' defined twice.\n   " + line)
                else:
                    raise Exception("unknown command '" + first_word + 
                    "'.\n   " + line)
        fo.close()
        return lat_long
    except Exception as e:
        raise Exception("Syntax error in '" + filename + "'\n" +
        "  Line " + str(line_nbr + 1) + ": " +e.args[0])

###############################################################################
# GROUP
###############################################################################        
class Group:
    def __init__(self, id, name, devices):
        self.id = id
        self.name = name
        self.devices = devices

class Groups:
    def __init__(self):
        self.groups = []
    def add(self, group):
        for g in self.groups:
            if (g.id == group.id):
                return False
        self.groups.append(group)
        return True
    def get(self, id):
        for group in self.groups:
            if (group.id == id):
                return group
        return None
        
###############################################################################
# FUNCTIONS
###############################################################################        
class FunctionBase(object):
    devices = 0
    control_library = None
    def __init__(self, device_or_group, control_library):
        if(isinstance(device_or_group,Group)):
            self.devices = device_or_group.devices
        else:
            self.devices = [device_or_group]
        self.control_library = control_library
        
class FunctionOn(FunctionBase):        
    def execute(self):
        self.control_library.turn_on(self.devices)

class FunctionOff(FunctionBase):        
    def execute(self):
        self.control_library.turn_off(self.devices)        

class FunctionDim(FunctionBase):
    dim_level = 0
    def __init__(self, device_or_group, dim_level, control_library):
        self.dim_level = dim_level
        super(FunctionDim, self).__init__(device_or_group, control_library)
    def execute(self):
        self.control_library.dim(self.devices, self.dim_level)        
        
###############################################################################
# TIMER HANDLING
###############################################################################
class TimerThread(threading.Thread):
    
    def __init__(self, event_list, sun):
        threading.Thread.__init__(self)
        self.run_event = threading.Event() # Used to order thread stop run
        self.semaphore = threading.Semaphore() # Used to block thread from run
        self.event_list = event_list
        self.sun = sun
        self.last_date = None
    
    def change_data(self, event_list, sun):
        self.semaphore.acquire()
        self.event_list = event_list
        self.sun = sun
        self.last_date = None # Force recalculation of sunset and sunrise
        self.semaphore.release()
        
    def run(self):
        sunrise_time = None
        sunset_time = None
        while not self.run_event.is_set():
            self.semaphore.acquire()
            
            dt = datetime.now()
            # Only recalculate sunset and sunrise once a day
            if ((self.last_date != dt.date()) and (self.sun != None)):
                sunrise_time = self.sun.sunrise()
                sunset_time = self.sun.sunset()
                self.last_date = dt.date()
                
            for event in self.event_list:
                if(event.time_match(dt, sunrise_time, sunset_time)):
                    event.execute()
                    
            self.semaphore.release()
            self.run_event.wait(60 - dt.second + 2)

    def stop(self):
        self.run_event.set()
        self.join()

class TimeEvent:
    TIME_SUNRISE = -1
    TIME_SUNSET  = -2
    hour    = 0 # Might be TIME_SUNRISE or TIME_SUNSET
    minute  = 0 # Total offset in minutes if TIME_SUNSET or TIME_SUNRISE
    weekday = [True, True, True, True, True, True, True]    
    RESTRICTION_NONE    = 0
    RESTRICTION_SUNDOWN = 1
    RESTRICTION_SUNUP   = 2    
    restriction = 0
    function = None
    
    def __init__(self, hour, minute, weekday, restriction, function):
        self.hour = hour
        self.minute = minute
        if(weekday != None):
            self.weekday = weekday
        self.restriction = restriction
        self.function = function
            
    def time_match_with_offset(self, dt, hour, minute):
        dt_trig = (datetime(dt.year,dt.month,dt.day,hour,minute) + 
                 timedelta(minutes = self.minute)) 
        return ((dt.hour == dt_trig.hour) and (dt.minute == dt_trig.minute))
        
    def time_match(self, dt, sunrise_time, sunset_time):
        match = False
        
        # Check time
        if(self.hour == self.TIME_SUNRISE):
            match = self.time_match_with_offset(dt, sunrise_time.hour, 
                                                sunrise_time.minute) 
        elif(self.hour == self.TIME_SUNSET):
            match = self.time_match_with_offset(dt, sunset_time.hour, 
                                                sunset_time.minute)
        else:
            match = ((self.hour == dt.hour) and (self.minute == dt.minute))
        
        # Check day of week
        if(match):
            match = self.weekday[dt.weekday()]
            
        # Check restriction
        if(match and (self.restriction == self.RESTRICTION_SUNUP)):
            match = ((dt.time() > sunrise_time) and (dt.time() < sunset_time)) 
        elif(match and (self.restriction == self.RESTRICTION_SUNDOWN)):
            match = ((dt.time() < sunrise_time) or (dt.time() > sunset_time))    
            
        return match
        
    def execute(self):
        self.function.execute()

###############################################################################
# WEB API
###############################################################################
class WebAPI:
    
    def _select_server(self):
        # Check if Cherrypy is installed or select WSGIRef 
        #(requires no installation)
        try:
            from cherrypy import wsgiserver
            return "cherrypy"
        except ImportError:
            return "wsgiref"
    
    def __init__(self, host, port, server, control, groups, config_file, 
                 log_file, timer_thread):
        self.host = host
        self.port = port
        if(server == ""):
            server = self._select_server()
        logging.info("Server: " + server)
        self.backend_server = server
        self.control = control
        self.groups = groups
        self.config_file = config_file
        self.log_file = log_file
        self.timer_thread = timer_thread
        self.app = bottle.Bottle()
        self._route()

    def _route(self):                  
        self.app.route('/devices', method="GET", 
                       callback=self._get_devices)
        self.app.route('/devices/config', method="GET", 
                       callback=self._get_devices_config)
        self.app.route('/devices/config', method="POST", 
                       callback=self._new_device_config)
        self.app.route('/device/<id:int>', method="GET", 
                       callback=self._get_device)
        self.app.route('/device/<id:int>/config', method="GET", 
                       callback=self._get_device_config)
        self.app.route('/device/<id:int>/config', method="PUT", 
                       callback=self._put_device_config)
        self.app.route('/device/<id:int>/config', method="DELETE", 
                       callback=self._delete_device_config)
        self.app.route('/device/<id:int>/on', method="GET", 
                       callback=self._turn_on_device)
        self.app.route('/device/<id:int>/off', method="GET", 
                       callback=self._turn_off_device)
        self.app.route('/device/<id:int>/dim/<level:int>', method="GET", 
                       callback=self._dim_device)
        self.app.route('/device/<id:int>/learn/<level:int>', method="GET", 
                       callback=self._learn_device)
        self.app.route('/groups', method="GET", 
                       callback=self._get_groups)
        self.app.route('/group/<id:int>', method="GET", 
                       callback=self._get_group)
        self.app.route('/group/<id:int>/on', method="GET", 
                       callback=self._turn_on_group)
        self.app.route('/group/<id:int>/off', method="GET", 
                       callback=self._turn_off_group)
        self.app.route('/group/<id:int>/dim/<level:int>', method="GET", 
                       callback=self._dim_group)
        self.app.route('/configuration', method="GET", 
                       callback=self._get_config)
        self.app.route('/configuration', method="POST", 
                       callback=self._set_config)
        self.app.route('/log', method="GET", 
                       callback=self._get_log)                       
        self.app.route('/', method="GET", 
                       callback=self._index)   
        self.app.route('/<path:path>', method="GET", 
                       callback=self._file) 
                       
    def start(self):
        self.app.run(server=self.backend_server, host=self.host, 
                     port=self.port, debug=True)

    def _return_success(self):
        bottle.response.content_type = 'application/json'
        return {'result' : 'success' }
        
    def _index(self):
        return bottle.static_file("index.html", 
                                  root=os.path.dirname(__file__) + "/html/")

    def _file(self, path):
        return bottle.static_file(path, 
                                  root=os.path.dirname(__file__) + "/html/")
        
    def _get_device(self, id):
        if id in self.control.get_device_IDs():        
            device = {
                'id'              : id,
                'name'            : self.control.get_name(id),
                'supports_on_off' : self.control.supports_on_off(id),
                'supports_dim'    : self.control.supports_dim(id),
                'last_cmd_was_on' : self.control.last_cmd_was_on(id)
            }
            if(self.control.supports_dim(id)):
                device.update({
                    'dim_level_min'   : self.control.DIM_LEVEL_MIN,
                    'dim_level_max'   : self.control.DIM_LEVEL_MAX,
                    'dim_level_last'  : self.control.last_dim_level(id)
                })
            bottle.response.content_type = 'application/json'
            return device
        else:
            bottle.abort(400, "Device with ID '" + str(id) + "' not found")

    def _get_device_config(self, id):
        if id in self.control.get_device_IDs():        
            config = {
                'id'              : id,
                'name'            : self.control.get_name(id),
                'protocol'        : self.control.get_protocol(id),
                'model'           : self.control.get_model(id),
                'parameters'      : self.control.get_parameters(id)
            }
            bottle.response.content_type = 'application/json'
            return config
        else:
            bottle.abort(400, "Device with ID '" + str(id) + "' not found")

    def _check_device_config_request(self, id, device):
        if( device == None):
            bottle.response.status = 400
            return "Could not parse JSON - secure that content type is application/json"
        elif(id != device["id"]):
            bottle.response.status = 400
            return "Device ID in request does not match URI ID"
        elif (len(device["name"]) < 1):
            bottle.response.status = 400
            return "Device name cannot be empty"
        elif (len(device["protocol"]) < 1):
            bottle.response.status = 400
            return "Device protocol cannot be empty"
        return ""
            
    def _update_device_config(self, device):
        id = int(device["id"])
        try:
            self.control.set_name(id, device["name"])
            self.control.set_protocol(id, device["protocol"])
            self.control.set_model(id, device["model"])
            self.control.set_parameters(id, device["parameters"])
        except Exception as e:
            bottle.response.status = 500
            return "Unable update device. \n\n" + e.args[0]
        return ""    
            
    def _put_device_config(self, id):
        device = bottle.request.json
        result = self._check_device_config_request(id, device)
        if(result != ""):
            return result
        return self._update_device_config(device)
 
    def _new_device_config(self):
        device = bottle.request.json
        result = self._check_device_config_request(-1, device)
        if(result != ""):
            return result
        try:
            device["id"] = self.control.new_device()
        except Exception as e:
            bottle.response.status = 500
            return "Unable to create new device. \n\n" + e.args[0]
        return self._update_device_config(device)

    def _delete_device_config(self, id):
        self.control.delete_device(id)        
        
    def _get_devices(self):
        result = []
        for id in self.control.get_device_IDs():
            result.append(self._get_device(id))
        return json.dumps(result)
        
    def _get_devices_config(self):
        result = []
        for id in self.control.get_device_IDs():
            result.append(self._get_device_config(id))
        return json.dumps(result)

    def _turn_on_device(self, id):
        if id not in self.control.get_device_IDs():    
            bottle.abort(400, "Device with ID '" + str(id) + "' not found") 
        elif (self.control.supports_on_off(id) == False):
            bottle.abort(400, "Device ID '" + str(id) + "' don't support on")        
        else:
            self.control.turn_on([id])
            return self._return_success()

    def _turn_off_device(self, id):
        if id not in self.control.get_device_IDs():    
            bottle.abort(400, "Device with ID '" + str(id) + "' not found") 
        elif (self.control.supports_on_off(id) == False):
            bottle.abort(400, "Device ID '" + str(id) + "' don't support off")        
        else:
            self.control.turn_off([id])
            return self._return_success()
            
    def _dim_device(self, id, level):
        if id not in self.control.get_device_IDs():    
            bottle.abort(400, "Device with ID '" + str(id) + "' not found") 
        elif (self.control.supports_dim(id) == False):
            bottle.abort(400, "Device ID '" + str(id) + "' don't support dim")
        elif ((level < self.control.DIM_LEVEL_MIN) or 
              (level > self.control.DIM_LEVEL_MAX)):
            bottle.abort(400, "Dim level '" + str(level) + "' invalid")            
        else:
            self.control.dim([id],level)
            return self._return_success()

    def _learn_device(self, id):
        if id not in self.control.get_device_IDs():    
            bottle.abort(400, "Device with ID '" + str(id) + "' not found") 
        elif (self.control.supports_learn(id) == False):
            bottle.abort(400, "Device ID '" + str(id) + "' don't support learn")        
        else:
            self.control.learn([id])
            return self._return_success()   

    def _get_group(self, id):
        supports_on_off = False
        supports_dim = False
        group = self.groups.get(id)
        if(group == None):
            bottle.abort(400, "Group with ID '" + str(id) + "' not found")
        else:
            for device_id in group.devices:
                if (self.control.supports_on_off(device_id)):
                    supports_on_off = True
                    break
            for device_id in group.devices:
                if (self.control.supports_dim(device_id)):
                    supports_dim = True
                    break       
            group_ret = {
                'id'              : id,
                'name'            : group.name,
                'devices'         : group.devices,
                'supports_on_off' : supports_on_off,                
                'supports_dim'    : supports_dim            
            }
            if (supports_dim):
                group_ret.update(
                    {
                    'dim_level_min' : self.control.DIM_LEVEL_MIN,
                    'dim_level_max' : self.control.DIM_LEVEL_MAX
                    })                 
            bottle.response.content_type = 'application/json'
            return group_ret
                
    def _get_groups(self):
        result = []
        for group in self.groups.groups:
            result.append(self._get_group(group.id))
        return json.dumps(result)            
            
    def _turn_on_group(self, id):
        group = self.groups.get(id)
        if(group == None):
            bottle.abort(400, "Group with ID '" + str(id) + "' not found") 
        else:
            self.control.turn_on(group.devices)
            return self._return_success()

    def _turn_off_group(self, id):
        group = self.groups.get(id)
        if(group == None):
            bottle.abort(400, "Group with ID '" + str(id) + "' not found") 
        else:
            self.control.turn_off(group.devices)
            return self._return_success()            
            
    def _dim_group(self, id, level):
        group = self.groups.get(id)
        if(group == None):
            bottle.abort(400, "Group with ID '" + str(id) + "' not found") 
        elif ((level < self.control.DIM_LEVEL_MIN) or 
              (level > self.control.DIM_LEVEL_MAX)):
            bottle.abort(400, "Dim level '" + str(level) + "' invalid")
        else:
            self.control.dim(group.devices,level)
            return self._return_success()
            
    def _get_config(self):
        bottle.response.content_type = 'text/plain'
        try:
            fo = open(self.config_file,"r")
            result = fo.read()
            fo.close()
            return result
        except Exception:
            bottle.response.status = 500
            return "Unable to open: " + self.config_file          

    def _set_config(self):
        bottle.response.content_type = 'text/plain'
        
        # Save configuration to temporary file
        temp_file = self.config_file + ".tmp"
        try:
            fo = open(temp_file,mode="w")
            fo.write(bottle.request.body.read())
            fo.close()
        except Exception as e:
            bottle.response.status = 500
            return "Unable to save temporary config file. \n\n" + e.args[0]

        # Try to parse the temporary file (validate syntax etc.)
        events = []
        groups = Groups()
        lat_long = None
        try:
            lat_long = load_config_file(temp_file, self.control, 
                                        events, groups)
        except Exception as e:
            bottle.response.status = 500
            return e.args[0]
            
        # Make a backup of the current configuration
        try:
            shutil.copyfile(self.config_file, self.config_file + ".bk")
        except Exception as e:
            bottle.response.status = 500
            return "Unable to backup configuration. \n\n" + e.args[0]

        # Copy temporary file to original file
        try:
            shutil.copyfile(temp_file, self.config_file)
        except Exception as e:
            bottle.response.status = 500
            return "Unable create configuration file. \n\n" + e.args[0]          
        
        # Create a new sun object
        if(lat_long != None):
            sun = sunstate.Sun(lat_long[0], lat_long[1], sunstate.LocalTimezone())
        
        # Update the timer thread with new events and sun
        self.timer_thread.change_data(events, sun)
        
        # Update the groups
        self.groups = groups

        return self._return_success() 
 
    def _get_log(self):
        bottle.response.content_type = 'text/plain'
        try:
            fo = open(self.log_file,"r")
            result = fo.read()
            fo.close()
            return result
        except Exception:
            bottle.response.status = 500
            return "Unable to open: " + self.log_file 
 
###############################################################################
# MAIN PROGRAM
###############################################################################
def usage():
    print("Usage: "+sys.argv[0]+" [option] ...\n")
    print("  -c file   : specify configuration file (default 'mas.config')")
    print("  -l file   : specify log file (default 'mas.log')")
    print("  -w ipaddr : enable WebAPI and use provided ip address (default disabled)")
    print("  -p port   : port for WebAPI (default 8080)")
    print("  -d        : debug mode (more info written to log)")
    print("  -s        : server (default: prio 1 'cherrypy', prio 2 'wsgiref')")
    print("  -?        : this help")
            
def main():
    events = []
    groups = Groups()
    control_library = None
    lat_long = None
    sun = None
    path = os.path.dirname(__file__) + "/"
    config_file = path + "mas.config"
    log_file = path + "mas.log"
    ip_address = ""
    server = ""
    port = 8080
    logging_level = logging.INFO    
    
    try:
        opts, args = getopt.getopt(sys.argv[1:], "?c:l:w:p:ds:")
    except getopt.GetoptError as e:
        print(str(e)+"\n")
        usage()
        exit(2)
        
    for o, a in opts:
        if o == "-c":
            config_file = a.strip()
        elif o == "-l":
            log_file = a.strip()
        elif o == "-w":
            ip_address = a.strip()
        elif o == "-p":
            port = int(a.strip())
        elif o == "-d":
            logging_level = logging.DEBUG 
        elif o == "-s":
            server = a.strip()
        else:
            usage()
            exit(2)

    logging.basicConfig(filename=log_file,level=logging_level,
        format="%(asctime)s - %(levelname)s - %(message)s")
    logging.info('Mini Automation Sever ' + __version__ + ' Initiated')
    logging.info('config file: ' + config_file)
    logging.info('log file:    ' + log_file)
    
            
    try:
        control_library = TelldusLibrary();

    except:
        errmsg = "Telldus core library is missing. Please install before use."
        logging.error(errmsg)    
        sys.stderr.write(errmsg+"\n")
        exit(3)

    try:
        lat_long = load_config_file(config_file, control_library, 
        events, groups)
    except Exception as e:
        logging.error(e.args[0])
        sys.stderr.write(e.args[0]+"\n")
        exit(3)
    
    if(lat_long != None):
        sun = sunstate.Sun(lat_long[0], lat_long[1], sunstate.LocalTimezone())
        
    timer_thread = TimerThread(events, sun)
    timer_thread.start()
    
    print("Running Mini Automation Server "+__version__)
    
    # Check if WebAPI should be started or not
    if(ip_address != ""):
        logging.info("WebAPI started on IP: "+ip_address+" Port: "+str(port))
        try:
            webApi = WebAPI(ip_address, port, server, control_library, groups,
                            config_file, log_file, timer_thread)
            webApi.start()
        except Exception as e:
            logging.error("Exception in WebAPI")
            sys.stderr.write("Exception in WebAPI: \n\n")
            timer_thread.stop()
            # Raise exception further so that the user can find out the 
            # problem
            raise e
            
    else:
        print("Hit Ctrl-C to quit.")
        try:
            while True:    
                time.sleep(600)
        except KeyboardInterrupt:
            pass
        
    print("Shutting down...")
    logging.info('Mini Automation Sever Exit')

    timer_thread.stop()
    exit()
    
    
if __name__ == '__main__':
    main()
