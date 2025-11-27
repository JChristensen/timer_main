import logging
import random
import time

logger = logging.getLogger('timer_main')

class Remote:
    """A single remote unit with a schedule."""

    def __init__(self, name, props):
        """props is a dictionary with keys sched, random and enabled.
        random and enabled are optional. sched is a list of lists giving
        the schedule for the remote. each sub-list is [time, state, days].
        we build self.sched and then use it to build the weekly
        schedule, self.week_sched. we keep self.sched just to print
        as part of the syntax check command line option."""

        self.days = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
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
            if 'all' in s[2]:
                s[2] = s[2].replace('all', 'sun mon tue wed thu fri sat')
            if 'weekdays' in s[2]:
                s[2] = s[2].replace('weekdays', 'mon tue wed thu fri')
            if 'weekends' in s[2]:
                s[2] = s[2].replace('weekends', 'sat sun')

        # create the weekly schedule, store times as dhhmm
        self.week_sched = []
        for d, day in enumerate(self.days):
            for s in self.sched:
                if day in s[2]:
                    sched_time = d * 10000 + s[0]
                    if self.random != 0:
                        sched_time = self.randomize(sched_time)
                    self.week_sched.append([sched_time, s[1]])
        self.week_sched.sort(reverse=True)


    def randomize(self, t):
        """given the schedule time t expressed as dhhmm, return a
        randomly adjusted time by applying the random value for this remote.
        if this would push the time into the next day, then set it to 2359
        instead. if it would push it back into the previous day,
        then set it to 0000."""

        # save the day of the week, and convert the time to minutes
        d = t // 10000
        hhmm = t - d * 10000
        hour = hhmm // 100
        minute = hhmm - hour * 100
        minutes = 60 * hour + minute

        # apply the random factor
        minutes += random.randint(-self.random, self.random)
        # limit the randomized time to the current day
        if minutes < 0:
            minutes = 0
        elif minutes > 1439:
            minutes = 1439
        return d * 10000 + 100 * (minutes // 60) + minutes % 60


    def process(self):
        """process schedules for a given remote. if the current schedule
        is different from the last time we checked, then return the list
        for the current schedule, else return an empty list."""

        # calculate current time as an integer, dhhmm,
        # where d is the day of the week (mon=0)
        local = time.localtime()
        now = local.tm_wday * 10000 + local.tm_hour * 100 + local.tm_min

        # find the current schedule item in effect.
        # if the current time is less than the earliest schedule, or greater
        # than or equal to the latest schedule, then the latest schedule is in
        # effect. remember, the schedules are sorted in reverse order.
        if self.week_sched:     # it is possible that there are none
            if now < self.week_sched[-1][0] or now >= self.week_sched[0][0]:
                current_sched = self.week_sched[0]
            # else, step through the schedule items to find which is in effect
            else:
                for s in self.week_sched:
                    if now >= s[0]:
                        current_sched = s
                        break

            if current_sched != self.last_sched:
                self.last_sched = current_sched
                return self.last_sched
            else:
                return []


    def print(self, verbose):
        """print the schedule and related info for this remote.
        used when checking syntax."""
        print(f'\nRemote name: {self.name}')
        print(f'Enabled: {self.enabled}')
        print(f'Random factor: {self.random}')
        print('Schedule:')
        for s in sorted(self.sched):
            print(s)
        if verbose:
            print('Week schedule:')
            for w in self.week_sched:
                print(w)
