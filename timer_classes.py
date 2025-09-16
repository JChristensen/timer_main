"""Classes for the timer_main program."""

import argparse
import logging
import logging.handlers
import os
import sys
import time
import yaml

logger = logging.getLogger('timer_main.py')

class Remote:
    """A single remote unit that we control with a schedule."""

    def __init__(self, name, props):
        self.name = name
        self.random = props.get('random', 0)
        self.sched = sorted(props["sched"], reverse=True, key=lambda t: t[0])
        # the schedule in effect at the last call to process()
        self.last_sched = []

        # make the days field lower case and expand special values
        for s in self.sched:
            s[2] = s[2].lower()
            if s[2] == 'all':
                s[2] = 'sun mon tue wed thu fri sat'
            elif s[2] == 'weekdays':
                s[2] = 'mon tue wed thu fri'
            elif s[2] == 'weekends':
                s[2] = 'sat sun'

    def process(self):
        """process a remote and send an mqtt command to update its state
        if the currently applicable schedule item has changed."""

        # calculate current time as an integer, hhmm
        localtime = time.localtime(time.time())
        now = localtime.tm_hour * 100 + localtime.tm_min
        day = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'][localtime.tm_wday]

        # make a list of the schedules in effect for today
        todays_sched = [s for s in self.sched if day in s[2]]

        # find the current schedule item in effect.
        # if the current time is less than the earliest schedule, or greater
        # than or equal to the last schedule, then the last schedule is in
        # effect. remember, the schedules are sorted in reverse order.

        if todays_sched:    # it is possible that there are none
            if now < todays_sched[-1][0] or now >= todays_sched[0][0]:
                current_sched = todays_sched[0]
            # else, step through the schedule items to find which is in effect
            else:
                for s in todays_sched:
                    if now >= s[0]:
                        current_sched = s
                        break

            if current_sched != self.last_sched:
                self.last_sched = current_sched
                print(f'Schedule in effect: {self.name} {self.last_sched}')

    def print(self):
        print(f'\nRemote name: {self.name}')
        print(f'Random factor: {self.random}')
        print('Schedule:')
        for s in sorted(self.sched):
            print(s)


class Controller:
    """A class to manage and communicate with one or more remotes."""

    def __init__(self, mainfile):
        self.remotes = []

        # various informational stuff
        self.progpath = os.path.dirname(os.path.realpath(mainfile))
        self.prognamepy = os.path.basename(sys.argv[0])  # name.py
        self.progname = self.prognamepy.split(sep='.')[0]     # name only
        # get the git hash for the current commit
        cmd = os.popen(f'git -C {self.progpath} log -1 --format="%h %ai %an"')
        self.git_hash = cmd.read().replace('\n', '')
        cmd.close()
        self.write_pidfile()
        version_info = f'{self.prognamepy} PID {str(os.getpid())} {self.git_hash}'
        log_filename = f'{self.progpath}{os.sep}.{self.progname}.log'

        # set up logging
        global logger
        logger = logging.getLogger(self.prognamepy)
        logger.setLevel(logging.DEBUG)
        handler = logging.handlers.TimedRotatingFileHandler(
                log_filename, when='midnight', backupCount=7)
        logger.addHandler(handler)
        f = logging.Formatter(
                fmt='%(asctime)s\t%(levelname)s\t%(name)s\t%(message)s',
                datefmt='%Y-%m-%d %H:%M:%S')
        handler.setFormatter(f)
        logger.info(f'Start {version_info}')

        # process command line arguments
        parser = argparse.ArgumentParser(
            description='Timer main: Control program for remote timers.',
            epilog='Manages schedules and communicates with one or more remote timers.')
        parser.add_argument("-s", "--syntax", help="Check config file for syntax errors and exit.", action="store_true")
        self.args = parser.parse_args()

    def init_controller(self):
        if self.remotes:
            for r in self.remotes:
                del r
            self.remotes = []

        # read the config file and convert to a dictionary object (d).
        # if not just checking syntax, and parsing the config file fails,
        # then the program will continue running but doing nothing.
        try:
            filename = 'config.yaml'
            d = {}
            with open(filename, 'r') as yamlfile:
                d = yaml.safe_load(yamlfile)
                logger.debug('Config file parsed successfully.')
        except Exception as e:
            logger.error('Error parsing config file!')
            if self.args.syntax:
                print(f'\nParse failed!\n\n{str(e)}')
                sys.exit(1)

        # instantiate Remote objects and add them to the list
        for k, v in d.items():
            self.remotes.append(Remote(k, v))

        if self.args.syntax:
            print('\nConfiguration file parsed successfully!')
            for r in self.remotes:
                r.print()
            logger.info('Exiting: Syntax check only.')
            sys.exit(0)

        for r in self.remotes:
            r.process()

    def process(self):
        for r in self.remotes:
            r.process()

    def sleep_minute(self):
        """Sleep until the minute rolls over."""
        now = time.time()
        l = time.localtime(now)
        sleep_sec = 60 - l.tm_sec
        time.sleep(sleep_sec)
        #print(time.strftime("%F %T"))

    def write_pidfile(self):
        with open (f'{self.progname}.pid', 'w') as p:
            p.write(f'{str(os.getpid())}\n')

    def remove_pidfile(self):
        os.remove(f'{self.progname}.pid')
