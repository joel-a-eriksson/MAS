import unittest
import MAS, Sun, datetime

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
        
    def test_parse_LAT_LONG_pass(self):
        lat_long = MAS.parse_LAT_LONG('LAT_LONG 59.17 18.3')
        self.assertTrue(lat_long[0] == 59.17)
        self.assertTrue(lat_long[1] == 18.3)         
        
    def test_parse_LAT_LONG_wrong_format(self):
        with self.assertRaises(Exception):
            MAS.parse_LAT_LONG('LAT_LONG 59.17 18.3 23')
        with self.assertRaises(Exception):
            MAS.parse_LAT_LONG('LAT_LONG 59.17')        
        with self.assertRaises(Exception):
            MAS.parse_LAT_LONG('LAT_LONG aa bb')  
            
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
        self.telldus_library, self.groups, False)
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
        
    def test_parse_EVENT_lat_long_not_set(self):
        with self.assertRaises(Exception):
            MAS.parse_EVENT("EVENT 01:23 Sundown on(1)",  
                    self.telldus_library, groups, False)
        with self.assertRaises(Exception):
            MAS.parse_EVENT("EVENT 01:23 Sunup on(1)",  
                    self.telldus_library, groups, False)
        with self.assertRaises(Exception):
            MAS.parse_EVENT("EVENT Sunrise on(1)",  
                    self.telldus_library, groups, False)
        with self.assertRaises(Exception):
            MAS.parse_EVENT("EVENT Sunset on(1)",  
                    self.telldus_library, groups, False)
                    
class TestSun(unittest.TestCase):
    # NOTE! These test cases will only pass if script is executed
    # on a computer located in Sweden or in a country with equal
    # UTC offset and daylight saving times as Sweden.

    TOLERANCE_SECONDS = 6 * 60 # Tolerance in seconds
        
    def test_stockholm_sunrise_sunset(self):
        lat  = 59.20
        long = 18.3
        test_set = [
            # Test data input from www.sunset-and-sunrise.com
            # [year, month, day, sunrise_h, sunrise_m, sunset_h, sunset_m]
            [2014, 1, 1,   8,43,   14,59],
            [2014, 1,17,   8,26,   15,29],
            [2014, 2, 1,   7,56,   16, 6],
            [2014, 2,21,   7,10,   16,51],
            [2014, 3,15,   6, 2,   17,50],
            [2014, 3,29,   5,21,   18,23],
            [2014, 3,30,   6,18,   19,26], # Daylight saving start
            [2014, 4,15,   5,31,   20, 4],
            [2014, 5,15,   4,13,   21,15],
            [2014, 6,15,   3,30,   22, 5],
            [2014, 7,15,   3,58,   21,49],
            [2014, 8,15,   5, 6,   20,37],
            [2014, 9,15,   6,17,   19, 8],
            [2014,10,15,   7,26,   17,40],
            [2014,10,25,   7,50,   17,12], 
            [2014,10,26,   6,53,   16, 9], # Daylight saving end
            [2014,11,15,   7,42,   15,22],
            [2014,12,15,   8,38,   14,47]
        ]
        for t in test_set:
            self._test_sunrise_sunset(lat, long, t[0], t[1], 
                t[2], t[3], t[4], t[5], t[6])

    def _test_sunrise_sunset(self, lat, long, year, month, day, 
                expected_sunrise_hour, expected_sunrise_minute, 
                expected_sunset_hour, expected_sunset_minute):
        date = datetime.date(year, month, day)
        s = Sun.Sun(lat, long, Sun.LocalTimezone())
        sunrise = s.sunrise(date)
        sunset = s.sunset(date)
        status1=self._compare_time(sunrise, expected_sunrise_hour, 
                            expected_sunrise_minute)
        status2=self._compare_time(sunset, expected_sunset_hour, 
                            expected_sunset_minute)	
        self.assertFalse((status1 != "Ok") or (status2 != "Ok"), str(year)+"-"+
            str(month)+"-"+str(day)+" Sunrise: "+status1+" Sunset: "+status2)
    
    def _compare_time(self, time1, hour, minute):
        time2 = datetime.time(hour, minute)
        date = datetime.date(2000, 1, 1) #Dummy
        diff = abs(datetime.datetime.combine(date, time2) - 
                    datetime.datetime.combine(date, time1))
        if((diff.days != 0) or (diff.seconds > self.TOLERANCE_SECONDS)):
            return "Got: "+str(time1)+" Expected: "+str(time2)
        return "Ok"
    
if __name__ == '__main__':
    unittest.main()