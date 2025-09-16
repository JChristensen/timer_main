"""Classes for the timer_main program."""

import logging
import pprint
import sys
import time
import yaml

logger = logging.getLogger('timer_main')

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
                print(f'New schedule in effect: {self.name} {self.last_sched}')

    def print(self):
        print(f'\nRemote name: {self.name}')
        print(f'Random factor: {self.random}')
        print('Schedule:')
        for s in self.sched:
            print(s)


class Controller:
    """A class to manage and communicate with one or more remotes."""

    def __init__(self):
        self.remotes = []

    def init_controller(self):
        if self.remotes:
            for r in self.remotes:
                del r
            self.remotes = []

        # read the config file and convert to a dictionary object (d)
        filename = 'config.yaml'
        with open(filename, 'r') as yamlfile:
            d = yaml.safe_load(yamlfile)

        # instantiate Remote objects and add them to the list
        for k, v in d.items():
            self.remotes.append(Remote(k, v))

        for r in self.remotes:
            r.process()

        # for testing only
        print(f'Remote count: {len(self.remotes)}')
        for r in self.remotes:
            r.print()

    def process(self):
        print(f'Remote count: {len(self.remotes)}')
        for r in self.remotes:
            r.process()

    def sleep_minute(self):
        """Sleep until the minute rolls over."""
        now = time.time()
        l = time.localtime(now)
        sleep_sec = 60 - l.tm_sec
        print(time.strftime("%F %T"), l.tm_hour*100+l.tm_min)
        time.sleep(sleep_sec)

    def check_config(self):
    # check the config file for syntax errors
        try:
            filename = 'config.yaml'
            with open(filename, 'r') as yamlfile:
                d = yaml.safe_load(yamlfile)
            print('\nConfiguration file parsed successfully!\n')
            pprint.pprint(d)
        except Exception as e:
            print(f'\nParse failed!\n\n{str(e)}')
            sys.exit(1)
