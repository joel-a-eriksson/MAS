import unittest
import MAS

class TestParsing(unittest.TestCase):
	telldus_library = None
	groups = None
	
	def SetUp(self):
		try:
			self.telldus_library = MAS.TelldusLibrary();
		except:
			sys.stderr.write("Telldus core library is missing. " + 
			"Please install before use.\n")
			exit(3)
		self.groups = MAS.Groups()

	def test_parse_GROUP_pass1(self):
		group = MAS.parse_GROUP('GROUP 12 "My name" 2 4 6')
		self.assertTrue(group.id == 12)
		self.assertTrue(group.name == "My name")
		self.assertTrue(group.devices == [2,4,6])
		
	def test_parse_GROUP_pass2(self):
		group = MAS.parse_GROUP('GROUP 1 "A" 456')
		self.assertTrue(group.id == 1)
		self.assertTrue(group.name == "A")
		self.assertTrue(group.devices == [456])

	def test_parse_GROUP_pass3(self):
		group = MAS.parse_GROUP('GROUP G8 "a group name" 0')
		self.assertTrue(group.id == 8)
		self.assertTrue(group.name == "a group name")
		self.assertTrue(group.devices == [0])
		
	def test_parse_GROUP_no_wrong_format(self):
		with self.assertRaises(Exception):
			MAS.parse_GROUP('GROUP 1 456')
		with self.assertRaises(Exception):
			MAS.parse_GROUP('GROUP 456 "Hello there"')
		with self.assertRaises(Exception):
			MAS.parse_GROUP('GROUP "Hello there" 3')
		
	def test_parse_EVENT_too_short(self):
		with self.assertRaises(Exception):
			MAS.parse_EVENT("EVENT 01:23", self.telldus_library, 
			self.groups)
		with self.assertRaises(Exception):
			MAS.parse_EVENT("EVENT", self.telldus_library, 
			self.groups)			

	def test_parse_EVENT_too_long(self):
		with self.assertRaises(Exception):
			MAS.parse_EVENT("EVENT 01:23 Sunup illegal off(1)", 
			self.telldus_library, self.groups)	

	def test_parse_EVENT_wrong_time(self):
		with self.assertRaises(Exception):
			MAS.parse_EVENT("EVENT 1344 Sunup off(1)", 
			self.telldus_library, self.groups)
		with self.assertRaises(Exception):
			MAS.parse_EVENT("EVENT 25:23 Sunup off(1)", 
			self.telldus_library, self.groups)			
		with self.assertRaises(Exception):
			MAS.parse_EVENT("EVENT 23:61 Sunup off(1)", 
			self.telldus_library, self.groups)

	def test_parse_EVENT_function(self):
		with self.assertRaises(Exception):
			MAS.parse_EVENT("EVENT 12:10 Sunup dummy(1)", 
			self.telldus_library, self.groups)
	
	def test_parse_EVENT_on(self):
		event = MAS.parse_EVENT("EVENT 00:01 Mon/Tue on(43)", 
		self.telldus_library, self.groups)
		self.assertTrue(event.hour == 0)
		self.assertTrue(event.minute == 1)
		self.assertTrue(event.weekday == 
		[True,True,False,False,False,False,False])
		self.assertTrue(event.restriction == 
		MAS.TimeEvent.RESTRICTION_NONE)
		self.assertTrue(isinstance(event.function,
		MAS.FunctionOn))
		self.assertTrue(event.function.devices == [43])
		
	def test_parse_EVENT_off(self):
		event = MAS.parse_EVENT("EVENT 01:23 Sunup off(1)", 
		self.telldus_library, self.groups)
		self.assertTrue(event.hour == 1)
		self.assertTrue(event.minute == 23)
		self.assertTrue(event.restriction == 
		MAS.TimeEvent.RESTRICTION_SUNUP)
		self.assertTrue(isinstance(event.function,
		MAS.FunctionOff))
		self.assertTrue(event.function.devices == [1])
	
	def test_parse_EVENT_dim(self):
		event = MAS.parse_EVENT("EVENT 01:23 Sundown dim(5,50)",  
		self.telldus_library, self.groups)
		self.assertTrue(isinstance(event.function,
		MAS.FunctionDim))
		self.assertTrue(event.function.devices == [5])
		self.assertTrue(event.function.dim_level == 50)
		
	def test_parse_EVENT_group_pass(self):
		groups = MAS.Groups()
		groups.add(MAS.parse_GROUP('GROUP 3 "My name" 2 4 6'))
		event = MAS.parse_EVENT("EVENT 01:23 Sundown on(G3)",  
		self.telldus_library, groups)
		self.assertTrue(event.function.devices == [2,4,6])

	def test_parse_EVENT_group_pass2(self):
		groups = MAS.Groups()
		groups.add(MAS.parse_GROUP('GROUP 1 "g1" 2 4 6'))
		groups.add(MAS.parse_GROUP('GROUP 2 "g2" 3'))
		groups.add(MAS.parse_GROUP('GROUP 3 "g3" 1 7'))
		event = MAS.parse_EVENT("EVENT 01:23 Sundown on(G2)",  
		self.telldus_library, groups)
		self.assertTrue(event.function.devices == [3])
		
	def test_parse_EVENT_group_does_not_exist(self):
		groups = MAS.Groups()
		with self.assertRaises(Exception):
			MAS.parse_EVENT("EVENT 01:23 Sundown on(G2)",  
		self.telldus_library, groups)
		
if __name__ == '__main__':
	unittest.main()