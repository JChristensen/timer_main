#!/home/jack/.venv/bin/python3
#
# TODO: Add command line argument to read alternate config file.
# TODO: Include mqtt parameters (broker, port, topic) in config file.
# TODO: Process schedules a week at a time, not a day at a time.

import logging
import signal
import sys
import time
import yaml

import controller as timer

def main():
    global controller
    global logger
    controller = timer.Controller(__file__)
    logger = logging.getLogger('timer_main')

    # register the signal handlers
    signal.signal(signal.SIGINT,  sigint_handler)
    signal.signal(signal.SIGTERM, sigterm_handler)
    signal.signal(signal.SIGHUP,  sighup_handler)

    controller.init_controller()

    while True:
        if controller.mqtt_connected:
            controller.sleep_minute()
            controller.process_retries()
            controller.process()
        else:
            time.sleep(10)


# signal handler for SIGINT: terminate program
def sigint_handler(signal, frame):
    global logger
    logger.info('Received SIGINT, exiting.')
    controller.remove_pidfile()
    sys.exit(0)


# signal handler for SIGTERM: terminate program
def sigterm_handler(signal, frame):
    global logger
    logger.info('Received SIGTERM, exiting.')
    controller.remove_pidfile()
    sys.exit(0)


# signal handler for SIGHUP: reprocess config file
def sighup_handler(signal, frame):
    global controller
    global logger
    logger.info('Received SIGHUP, reloading configuration.')
    controller.init_controller()


if __name__ == '__main__':
    main()
