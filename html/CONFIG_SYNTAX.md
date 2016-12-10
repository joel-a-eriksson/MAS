## MAS Configuration File Syntax

### Comments

	#[comment text]

Example:

	# This is a comment

	
### Location (needed for sunrise / sunset)

	LAT_LONG <latitude> <longitude>

Example for Stockholm / Sweden:

	LAT_LONG 59.17 18.3


### Group definitions

	GROUP <groupID> "<name>" <ID1> [<ID2> .. <IDn>]
	
*<groupID>* = G<ID>, for example G1 or G23. The G prefix is not required
*<IDx>* = Identity of the devices to include in the group

Example:

	GROUP G1 "Christmas Lights upstairs" 5 9


### Events

	EVENT <time> [<dayofweek>] [<restriction>] <function>

*<time>* = *<hour>:<minute>*, *Sunrise* or *Sunset*

An optional offset in hours can be give to Sunrise and Sunset.
For example Sunrise+1.5 Sunrise-3 Sunset+0.25

**NOTE** Sunrise and Sunset requires LAT_LOG to be set.

*<dayofweek>* = Mon/Tue/Wen/Thu/Fri/Sat/Sun

Any day may be omitted, for example Mon/Fri/Sun, will only trigger
the event on Mondays, Fridays and Sundays. If omitted event will be 
trigged all days.

*<restriction>* = *Sunup* or *Sundown*

Will not trigger the event if the restriction is fullfilled.

**NOTE** Sunup and Sundown requires LAT_LOG to be set.

*<function>* = *on(<ID>)* or *off(<ID>)* or *dim(<ID>,<level>)*

The <ID> might be a device ID or a group ID (prefix G is needed).

Valid dim levels are 0 - 255

Example 1:

	EVENT Sunset+0.5 on(11)

Will turn on device with ID 11 30 minutes after sunset every day.

Example 2:

	EVENT 11:00 Tue/Sat off(G4)

Will turn off all devices in group with ID 4 every Tuesday and Saturday at 11:00.

Example 3:

	EVENT 23:00 Sundown dim(5, 128)

Will dim the device with ID 5 to ~50% at 23:00 everyday, but only
if the sun is down.