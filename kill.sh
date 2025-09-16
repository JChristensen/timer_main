#!/bin/bash
# Kill the timer_main program
pkill --pidfile timer_main.pid --signal sigterm
