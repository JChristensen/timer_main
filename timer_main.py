#!/home/jack/.venv/bin/python3

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

    # initialize
    controller.init_controller()
    last_mday = time.localtime().tm_mday
    controller.sleep_minute()

    # main loop
    while True:
        if controller.mqtt_connected:
            t = time.localtime(time.time() + 0.5)   # round up fractional seconds
            # time for the daily reprocess? (to generate any new random times)
            if t.tm_mday != last_mday:
                last_mday = t.tm_mday
                logger.debug(f'Starting daily schedule reprocess.')
                controller.init_controller()
                logger.debug(f'Reprocess complete.')
            else:
                controller.process_retries()
                controller.process()
            controller.sleep_minute()
        else:
            time.sleep(1)


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
