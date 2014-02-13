###############################################################################
# MINI AUTOMATION SERVER (MAS)
###############################################################################

from ctypes import util
from ctypes import *
from threading import Timer
from datetime import datetime
import getopt, sys, time, threading, re

###############################################################################
# FAKE LIBRARY - FOR TESTING ONLY
###############################################################################
class DebugLibrary:
	def __init__(self):
		pass

	def log(self, function, devices):
		time = datetime.now()
		print("")
		print(time)
		print(function)
		print(devices)
		print("")

	def turn_on(self,devices):
		self.log("Turn on", devices)			

	def turn_off(self,devices):
		self.log("Turn off", devices)			
				
	def dim(self,devices,dim_level):
		self.log("Dim to level: "+str(dim_level), devices)

###############################################################################
# TELLSTICK LIBRARY
###############################################################################
class TelldusLibrary:
	TURNON  = 1
	TURNOFF = 2
	BELL    = 4
	TOGGLE  = 8
	DIM     = 16
	LEARN   = 32
	ALL_METHODS = TURNON | TURNOFF | BELL | TOGGLE | DIM | LEARN
	library = None

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
		self.library.tdLastSentValue.restype = c_char_p
		self.library.tdGetProtocol.restype = c_char_p
		self.library.tdGetModel.restype = c_char_p
		self.library.tdGetErrorString.restype = c_char_p
		self.library.tdLastSentValue.restype = c_char_p

	def turn_on(self,devices):
		for device in devices:
			if(self.library.tdMethods(device,self.TURNON) & 
			self.TURNON):
				self.library.tdTurnOn(device)
			else:
				#@@@@ err log
				print(str(device) + " cannot be turned on")
	
	def turn_off(self,devices):
		for device in devices:
			if(self.library.tdMethods(device,self.TURNOFF) & 
			self.TURNOFF):
				self.library.tdTurnOff(device)
				#time.sleep(1)
			else:
				#@@@@ err log
				print(str(device) + " cannot be turned off")					
				
	def dim(self,devices,dim_level):
		for device in devices:
			if(self.library.tdMethods(device,self.DIM) & 
			self.DIM):
				self.library.tdDim(device,dim_level)
				#time.sleep(1)
			else:
				#@@@@ err log
				print(str(device) + " cannot be dimmed")				
				
###############################################################################
# LOAD CONFIGURATION FILE HANDLING
###############################################################################
def parse_EVENT(line, control_library, groups):
	hour   = 0
	minute = 0
	weekday =  None
	restriction = 0
	function = None
	
	words = line.split()
	if((len(words) < 3) or (len(words) > 5)):
		raise Exception("EVENT must have 3 - 5 arguments\n   " + " | ".join(words))
		
	# Parse <time>
	if(words[1] == "Sunrise"):
		hour = TimeEvent.TIME_SUNRISE
	elif(words[1] == "Sunset"):
		hour = TimeEvent.TIME_SUNSET
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
			restriction = TimeEvent.RESTRICTION_SUNUP
		elif(words[word_index]=="Sundown"):
			restriction = TimeEvent.RESTRICTION_SUNDOWN	
		else:
			raise Exception("invalid restriction. Valid values are "+ 
			"'Sunup' or 'Sundown'\n   "	+ line)
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
				elif (first_word == "EVENT"):
					event = parse_EVENT(line, control_library, groups)
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
		return True
	except Exception as e:
		raise Exception("Syntax error in '" + filename + "'\n" +
		"  Line " + str(line_nbr + 1) + ": " +e.args[0])

###############################################################################
# GROUP
###############################################################################		
class Group:
	id = 0
	name = ""
	devices = []
	def __init__(self, id, name, devices):
		self.id = id
		self.name = name
		self.devices = devices

class Groups:
	groups = []
	def __init__(self):
		pass
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
	event = None
	event_list = None
	
	def __init__(self, event_list):
		threading.Thread.__init__(self)
		self.event = threading.Event()
		self.event_list = event_list

	def run(self):
		while not self.event.is_set():
			time = datetime.now()
			for event in self.event_list:
				if(event.time_match(time)):
					event.execute()
			self.event.wait( 60 - time.second + 2 )

	def stop(self):
		self.event.set()

class TimeEvent:
	TIME_SUNSET  = -1
	TIME_SUNRISE = -2
	hour    = 0
	minute  = 0
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
			
	def __lt__(self, other):
		return (self.hour*60 + self.minute) < (other.hour*60 + other.minute)
		
	def time_match(self, time):
		return ((self.hour == time.hour) and (self.minute == time.minute) 
		and self.weekday[time.weekday()])
	
	def execute(self):
		self.function.execute()
	
###############################################################################
# MAIN PROGRAM
###############################################################################
def usage():
	print("Usage: "+sys.argv[0]+" [option] ...\n")
	print("  -c file : specify configuration file")
	print("  -?      : this help")
			
def main():
	events = []
	groups = Groups()
	control_library = None
	config_file = "MAS.config"
	
	try:
		opts, args = getopt.getopt(sys.argv[1:], "?c:", ["?","config="])
	except getopt.GetoptError as e:
		print(str(e)+"\n")
		usage()
		exit(2)
		
	for o, a in opts:
		if o in ("-c", "--config"):
			config_file = a	
		else:
			usage()
			exit(2)
			
	try:
		control_library = TelldusLibrary();
		#@@@@ control_library = DebugLibrary();
	except:
		sys.stderr.write("Telldus core library is missing. " + 
		"Please install before use.\n")
		exit(3)

	try:
		load_config_file(config_file, control_library, 
		events, groups)
	except Exception as e:
		sys.stderr.write(e.args[0]+"\n")
		exit(3)
	
	timer_thread = TimerThread(events)
	timer_thread.start()
	
	print("Running Mini Automation Server")
	print("Use Ctrl-C to quit.")
	
	try:
		while True:	
			time.sleep(600)
	except KeyboardInterrupt:
		pass
		
	print("Shutting down...")
	timer_thread.stop()
	exit()
	
	
if __name__ == '__main__':
	main()
