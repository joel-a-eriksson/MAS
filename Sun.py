from math import cos,sin,acos,asin,tan
from math import degrees as deg, radians as rad
from datetime import date,datetime,time, tzinfo, timedelta
import sys
import time as _time

class LocalTimezone(tzinfo):
    '''
    This class represent the local time zone (on the computer
    which the script is executed on)
    '''
    def utcoffset(self, dt):
        if self._isdst(dt):
            return timedelta(seconds = -_time.altzone)
        else:
            return timedelta(seconds = -_time.timezone)
            
    def dst(self, dt):
        if self._isdst(dt):
            return (timedelta(seconds = -_time.altzone) - 
                    timedelta(seconds = -_time.timezone))
        else:
            return timedelta(0)
            
    def tzname(self, dt):
        return _time.tzname[self._isdst(dt)]

    def _isdst(self, dt):
        tt = (dt.year, dt.month, dt.day,
                dt.hour, dt.minute, dt.second,
                dt.weekday(), 0,0)
        stamp = _time.mktime(tt)
        tt = _time.localtime(stamp)
        return tt.tm_isdst > 0	

class Sun:
    ''' 
    Calculate sunrise and sunset based on equations from NOAA
    http://www.srrb.noaa.gov/highlights/sunrise/calcdetails.html

    typical use, calculating the sunrise at the present day
    '''
    
    def __init__(self,lat,long,timezone=None):
        '''   
        If none is given for timezone a local time zone is assumed 
        (including daylight saving if present)
        '''
        self.lat=lat
        self.long=long
        if timezone == None : self.timezone = LocalTimezone()
        self.timezone = timezone
        
    def sunrise(self,when=None):
        '''
        return the time of sunrise as a datetime.time object
        when is a datetime.date object. If no date is given
        current date is assumed.
        '''
        if when is None : when = date.today()
        self.__preptime(when)
        self.__calc()
        return self.__timefromdecimalday(self.sunrise_t)
      
    def sunset(self,when=None):
        if when is None : when = date.today()
        self.__preptime(when)
        self.__calc()
        return self.__timefromdecimalday(self.sunset_t)
      
    def solarnoon(self,when=None):
        if when is None : when = date.today()
        self.__preptime(when)
        self.__calc()
        return self.__timefromdecimalday(self.solarnoon_t)
        
    def __timefromdecimalday(self, day):
        '''
        returns a datetime.time object.
        
        day is a decimal day between 0.0 and 1.0, e.g. noon = 0.5
        '''
        hours  = 24.0*day
        h      = int(hours)
        minutes= (hours-h)*60
        m      = int(minutes)
        seconds= (minutes-m)*60
        s      = int(seconds)
        return time(hour=h,minute=m,second=s)

    def __preptime(self,when):
        '''
        Extract information in a suitable format from when, 
        a datetime.date object.
        '''
        # Create a datetime object from the date object. Set
        # hour to 12 (noon).
        t = time(hour=12, tzinfo=self.timezone)
        dt = datetime.combine(when, t)
        
        # datetime days are numbered in the Gregorian calendar
        # while the calculations from NOAA are distibuted as
        # OpenOffice spreadsheets with days numbered from
        # 1/1/1900. The difference are those numbers taken for 
        # 18/12/2010
        self.day = dt.toordinal()-(734124-40529)
        self.time= (t.hour + t.minute/60.0 + t.second/3600.0)/24.0
        
        self.offset=0
        utc_offset=dt.utcoffset()
        if not utc_offset is None:
            self.offset=utc_offset.seconds/3600.0+(utc_offset.days*24)
        
    def __calc(self):
        '''
        Perform the actual calculations for sunrise, sunset and
        a number of related quantities.
        
        The results are stored in the instance variables
        sunrise_t, sunset_t and solarnoon_t
        '''
        offset = self.offset # in hours, east is positive
        longitude= self.long # in decimal degrees, east is positive
        latitude = self.lat  # in decimal degrees, north is positive
        
        time  = self.time # percentage past midnight, i.e. noon  is 0.5
        day   = self.day  # daynumber 1=1/1/1900
        
        Jday     =day+2415018.5+time-offset/24 # Julian day
        Jcent    =(Jday-2451545)/36525    # Julian century
        
        Manom    = 357.52911+Jcent*(35999.05029-0.0001537*Jcent)
        Mlong    = 280.46646+Jcent*(36000.76983+Jcent*0.0003032)%360
        Eccent   = 0.016708634-Jcent*(0.000042037+0.0001537*Jcent)
        Mobliq   = 23+(26+((21.448-Jcent*(46.815+Jcent*(0.00059-Jcent*0.001813))))/60)/60
        obliq    = Mobliq+0.00256*cos(rad(125.04-1934.136*Jcent))
        vary     = tan(rad(obliq/2))*tan(rad(obliq/2))
        Seqcent  = sin(rad(Manom))*(1.914602-Jcent*(0.004817+0.000014*Jcent))+sin(rad(2*Manom))*(0.019993-0.000101*Jcent)+sin(rad(3*Manom))*0.000289
        Struelong= Mlong+Seqcent
        Sapplong = Struelong-0.00569-0.00478*sin(rad(125.04-1934.136*Jcent))
        declination = deg(asin(sin(rad(obliq))*sin(rad(Sapplong))))
        
        eqtime   = 4*deg(vary*sin(2*rad(Mlong))-2*Eccent*sin(rad(Manom))+4*Eccent*vary*sin(rad(Manom))*cos(2*rad(Mlong))-0.5*vary*vary*sin(4*rad(Mlong))-1.25*Eccent*Eccent*sin(2*rad(Manom)))
        
        hourangle= deg(acos(cos(rad(90.833))/(cos(rad(latitude))*cos(rad(declination)))-tan(rad(latitude))*tan(rad(declination))))
        
        self.solarnoon_t=(720-4*longitude-eqtime+offset*60)/1440
        self.sunrise_t  =self.solarnoon_t-hourangle*4/1440
        self.sunset_t   =self.solarnoon_t+hourangle*4/1440

if __name__ == "__main__":
    if (len(sys.argv)>1):
        s=Sun(float(sys.argv[1]),float(sys.argv[2]), LocalTimezone())
    else:
        s = Sun(59.17,18.3, LocalTimezone()) # Default Stockholm / Sweden
        
    print("Time now: " + str(datetime.now()))
    print("Sunrise: "+str(s.sunrise())+"  Solarnoon: "+str(s.solarnoon())+"  Sunset: " +str(s.sunset()))