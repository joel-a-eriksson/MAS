#!/bin/bash

### BEGIN INIT INFO
# Provides: MAS
# Required-Start: $remote_fs $syslog
# Required-Stop: $remote_fs $syslog
# Default-Start: 2 3 4 5
# Default-Stop: 0 1 6
# Short-Description: Mini Automation Server
### END INIT INFO

cd /home/pi/MAS/ && 
python MAS.py &

