#!/usr/bin/python3
#import random
#import string
#''.join(random.choices(string.hexdigits, k=16))

import argparse
import logging
import os
import pprint
import signal
import sys
import time
import yaml

import timer_classes as timer

def main():
    global controller
    controller = timer.Controller()

    # register signal handlers
    signal.signal(signal.SIGINT,  sigint_handler)
    signal.signal(signal.SIGTERM, sigterm_handler)
    signal.signal(signal.SIGHUP,  sighup_handler)

    controller.init_controller()

    while True:
        controller.sleep_minute()
        controller.process()


def setup():
    """Initialize logging, process cmdline args."""

    # various informational stuff
    progpath = os.path.dirname(os.path.realpath(__file__))
    prognamepy = os.path.basename(sys.argv[0])  # name.py
    progname = prognamepy.split(sep='.')[0]     # name only
    # get the git hash for the current commit
    cmd = os.popen(f'git -C {progpath} log -1 --format="%h %ai"')
    git_hash = cmd.read().replace('\n', '')
    cmd.close()
    version_info = f'{prognamepy} {git_hash}'
    log_filename = f'{progpath}{os.sep}.{progname}.log'

    # set up logging
    myLog = logging.getLogger(prognamepy)
    myLog.setLevel(logging.DEBUG)
    handler = logging.handlers.TimedRotatingFileHandler(
            log_filename, when='midnight', backupCount=7)
    myLog.addHandler(handler)
    f = logging.Formatter(
            fmt='%(asctime)s\t%(levelname)s\t%(name)s\t%(message)s',
            datefmt='%Y-%m-%d %H:%M:%S')
    handler.setFormatter(f)
    pid = str(os.getpid())
    myLog.info(f'Start {version_info} PID {pid}')
    with open (f'{progname}.pid', 'w') as p:
        p.write(f'{pid}\n')

    # process command line arguments
    parser = argparse.ArgumentParser(
        description='Timer main: Control program for remote timers.',
        epilog='Manages schedules and communicates with one or more remote timers.')
    parser.add_argument("-s", "--syntax", help="Check config file for syntax errors and exit.", action="store_true")
    args = parser.parse_args()


# signal handler for SIGINT: terminate program
def sigint_handler(signal, frame):
    # global myLog
    # myLog.info('Received SIGINT, exiting.')
    print('Received SIGINT, exiting.')
    sys.exit(0)


# signal handler for SIGTERM: terminate program
def sigterm_handler(signal, frame):
    # global myLog
    # myLog.info('Received SIGTERM, exiting.')
    print('Received SIGTERM, exiting.')
    sys.exit(0)


# signal handler for SIGHUP: reprocess config file
def sighup_handler(signal, frame):
    global controller
    # global myLog
    # myLog.info('Received SIGHUP, reloading configuration.')
    print('Received SIGHUP, reloading configuration.')
    controller.init_controller()


if __name__ == '__main__':
    main()
