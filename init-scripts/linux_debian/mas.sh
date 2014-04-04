#!/bin/sh
#
#   - Mini Automation Server (MAS) init.d script -
#
#   Modify the variables below to locate the mas scripts, configurations 
#   and logging files.
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
### BEGIN INIT INFO
# Provides:          mas
# Required-Start:    $remote_fs $syslog
# Required-Stop:     $remote_fs $syslog
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Start/stop Mini Automation Server
# Description:       This is the init script for the Mini Automation Server.
### END INIT INFO
 
DIR=/home/pi/mas
CONFIG_FILE=$DIR/mas.config
LOG_FILE=$DIR/mas.log
DAEMON=$DIR/mas.py
DAEMON_OPTS="-c $CONFIG_FILE -l $LOG_FILE"
DAEMON_NAME=mas
DAEMON_USER=root
PIDFILE=/var/run/$DAEMON_NAME.pid
 
. /lib/lsb/init-functions
 
do_start () {
    if [ -e $PIDFILE ]; then
     status_of_proc -p $PIDFILE "$DAEMON_NAME" "$DAEMON" && status="0" || status="$?"
     # If the status is SUCCESS then don't need to start again.
     if [ $status = "0" ]; then
      exit # Exit
     fi
    fi
    log_daemon_msg "Starting system $DAEMON_NAME daemon"
    start-stop-daemon --start --background --pidfile $PIDFILE --make-pidfile --user $DAEMON_USER --chuid $DAEMON_USER --exec $DAEMON -- $DAEMON_OPTS
    log_end_msg $?
}
do_stop () {
    log_daemon_msg "Stopping system $DAEMON_NAME daemon"
    start-stop-daemon --stop --pidfile $PIDFILE --retry 10
    log_end_msg $?
}
 
case "$1" in
 
    start|stop)
        do_${1}
        ;;
 
    restart|reload|force-reload)
        do_stop
        do_start
        ;;
 
    status)
        status_of_proc -p $PIDFILE "$DAEMON_NAME" "$DAEMON" && exit 0 || exit $?
        ;;
    *)
        echo "Usage: /etc/init.d/$DAEMON_NAME {start|stop|restart|status}"
        exit 1
        ;;
 
esac
exit 0