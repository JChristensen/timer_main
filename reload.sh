#!/bin/bash
# Reload the config file
pkill --pidfile timer_main.pid --signal sighup
