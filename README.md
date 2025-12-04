# Timer Main Control Program
https://github.com/JChristensen/timer_main  
README file  

## License
Timer Main Control Program Copyright (C) 2025 Jack Christensen GNU GPL v3.0

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License v3.0 as published by the Free Software Foundation.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/gpl.html>

## Overview
This project was conceived as a more convenient replacement for several digital lamp timers that worked well enough but were tedious to program. My solution was to have a single main control program for any number of "remote" timer units. The main program works from a simple text file that contains the on/off schedules for all the remote units.

The main control program is written in Python and is meant to run on a Raspberry Pi as a systemd service. The remote units use Raspberry Pi Pico W (or 2W) microcontrollers. The main program and the remotes communicate via MQTT. Both the main control program and the MQTT broker can easily run on a Raspberry Pi Zero 2W or even on a 32-bit Pi Zero W, using Raspberry Pi OS Lite in a headless configuration.

The timer_main program writes log files so its operation can be monitored.

## Signals
Sending SIGHUP to the timer_main program will cause it to re-read and re-process the schedule file.  
Sending SIGTERM or SIGINT will terminate the program.

## See also
[Microcontroller firmware.](https://github.com/JChristensen/timer_remote)  
[PCB for the remote units.](https://github.com/JChristensen/remote_wifi_timer)  
