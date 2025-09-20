import logging
import time

logger = logging.getLogger('timer_main')

class Remote:
    """A single remote unit with a schedule."""

    def __init__(self, name, props):
        """props is a dictionary with keys sched and random. random is
        optional. sched is a list of lists giving the schedule for the
        remote. each sub-list is [time, state, days]"""

        # the config file can pass syntax checking but be structured in ways
        # that we do not expect. if so, we pass error information back
        # in the object, which then needs to be checked by the caller.
        try:
            self.name = name
            self.enabled = props.get('enabled', True)
            self.random = props.get('random', 0)
            self.sched = sorted(props['sched'], reverse=True, key=lambda t: t[0])
        except Exception as e:
            logger.error(f'Unexpected structure in config file: {str(e)}')
            self.name = 'error'
            self.error_msg = str(e)
            return

        # we keep the schedule item that was in effect the last time that a
        # new state was sent to the remote, i.e. the last call to process()
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
        """process schedules for a given remote. if the current schedule
        is different from the last time we checked, then return the list
        for the current schedule, else return an empty list."""

        # calculate current time as an integer, hhmm, and get the current dow
        localtime = time.localtime(time.time())
        now = localtime.tm_hour * 100 + localtime.tm_min
        day = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'][localtime.tm_wday]

        # make a list of the schedules in effect for today
        todays_sched = [s for s in self.sched if day in s[2]]

        # find the current schedule item in effect.
        # if the current time is less than the earliest schedule, or greater
        # than or equal to the latest schedule, then the latest schedule is in
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
                return self.last_sched
            else:
                return []


    def print(self):
        """print the schedule and related info for this remote.
        used when checking syntax."""
        print(f'\nRemote name: {self.name}')
        print(f'Enabled: {self.enabled}')
        print(f'Random factor: {self.random}')
        print('Schedule:')
        for s in sorted(self.sched):
            print(s)
