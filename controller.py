import argparse
import logging
import logging.handlers
import paho.mqtt.client as mqtt
import os
import random
import socket
import sys
import time
import yaml

import remote

logger = logging.getLogger('timer_main')

class Controller:
    """A class to manage and communicate with one or more remotes."""

    def __init__(self, mainfile):
        """set up logging, process command line arguments"""

        # a list containing all the Remote objects
        self.remotes = []

        # a dictionary containing schedules that have been sent to a remote
        # but not acknowledged.
        self.retry = {}

        # a list of remote hostnames that are considered offline
        # because they have not responded to a message.
        self.offline = []

        # the mqtt client and associated parameters
        self.mqClient = None
        self.mqtt_connected = False
        self.mq_broker = ''
        self.mq_port = 0
        self.mq_topic = ''

        # various informational stuff
        self.progpath = os.path.dirname(os.path.realpath(mainfile))
        self.prognamepy = os.path.basename(sys.argv[0])  # name.py
        self.progname = self.prognamepy.split(sep='.')[0]     # name only
        # get the git hash for the current commit
        cmd = os.popen(f'git -C {self.progpath} log -1 --format="%h %ai %an"')
        self.git_hash = cmd.read().replace('\n', '')
        cmd.close()
        version_info = f'{self.prognamepy} PID {str(os.getpid())} {self.git_hash}'
        log_filename = f'{self.progpath}{os.sep}.{self.progname}.log'

        # set up logging
        global logger
        logger = logging.getLogger(self.progname)
        logger.setLevel(logging.DEBUG)
        handler = logging.handlers.TimedRotatingFileHandler(
                log_filename, when='midnight', backupCount=7)
        logger.addHandler(handler)
        f = logging.Formatter(
                fmt='%(asctime)s.%(msecs)03d\t%(levelname)s\t%(module)s\t%(message)s',
                datefmt='%Y-%m-%d %H:%M:%S')
        handler.setFormatter(f)
        logger.info(f'Start {version_info}')

        # process command line arguments
        parser = argparse.ArgumentParser(
            description='Timer main: Control program for remote timers.',
            epilog='Manages schedules and communicates with one or more remote timers.')
        parser.add_argument('-s', '--syntax', action='store_true',
            help='Check config file for syntax errors and exit.')
        parser.add_argument('-c', '--config', default='config.yaml',
            help='Optional config file name, defaults to config.yaml.')
        self.args = parser.parse_args()
        self.write_pidfile()


    def init_controller(self):
        """reads the configuration file and creates Remote objects.
        exits if it's just a syntax check, else initializes mqtt and
        processes the remotes."""

        # in case we were called to reload the config file, start with
        # a fresh list of remotes, clear the retry dict and offline list.
        for r in self.remotes:
            del r
        self.remotes = []
        self.retry = {}
        self.offline = []

        # read the config file and convert to a dictionary object (d).
        # if not just checking syntax, and parsing the config file fails,
        # then the program will continue running but will do nothing
        # as the dictionary will be empty.
        try:
            filename = self.args.config
            d = {}
            with open(filename, 'r') as yamlfile:
                d = yaml.safe_load(yamlfile)
                logger.debug(f'Config file parsed successfully: {filename}')
        except Exception as e:
            logger.error(f'Error parsing config file: {filename}')
            if self.args.syntax:
                print(f'\nParse failed!\n{str(e)}')
                sys.exit(1)

        # get the mqtt and remotes blocks from the config file.
        # if they do not exist, then generate an error.
        try:
            mqtt_d = d['mqtt']
            remotes_d = d['remotes']
            self.mq_broker = mqtt_d['broker']
            self.mq_port = mqtt_d.get('port', 1883)
            self.mq_topic = mqtt_d.get('topic', self.progname)
        except Exception as e:
            logger.error(f'Config file error: {str(e)}')
            if self.args.syntax:
                print(f'Config file error: {str(e)}')
                sys.exit(1)
            else:
                # this return will cause the program to keep running but doing nothing.
                return

        # instantiate Remote objects and add them to the list
        for k, v in remotes_d.items():
            r = remote.Remote(k, v)
            if r.name == 'error':
                if self.args.syntax:
                    print('\nParse failed!')
                    print(f'Unexpected structure in config file: {r.error_msg}')
                    sys.exit(1)
            else:
                self.remotes.append(r)

        # if syntax check, print the config information.
        if self.args.syntax:
            print(f'\nConfiguration file parsed successfully: {filename}')
            for r in self.remotes:
                r.print()
            logger.info('Exiting: Syntax check only.')
            sys.exit(0)

        if not self.args.syntax:
            if not self.mqtt_connected:
                self.init_mqtt()
                time.sleep(1)
            self.process()


    def init_mqtt(self):
        """set up callback functions and start mqtt."""

        self.mqClient = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, \
            client_id=f'{self.prognamepy}@{socket.gethostname()}', clean_session=True)
        self.mqClient.on_connect = self.on_connect
        self.mqClient.on_message = self.on_message
        self.mqClient.on_disconnect = self.on_disconnect
        self.mqClient.loop_start()

        # connect to broker
        logger.info(f'MQTT broker {self.mq_broker}:{self.mq_port} topic {self.mq_topic}')
        retryInterval = 10
        nTry = 0
        while (not self.mqtt_connected):
            try:
                nTry += 1
                self.mqClient.connect(self.mq_broker, self.mq_port)
                time.sleep(1)
            except Exception as e:
                logMsg = f'Connect to broker failed: {str(e)}, Retry in {str(retryInterval)} seconds.'
                logger.error(logMsg)
                time.sleep(retryInterval)
                if (nTry == 12):
                    retryInterval = 60


    def on_connect(self, mqClient, userdata, flags, reason_code, properties):
        """The callback for when the client receives a CONNACK response from the broker."""
        global logger
        logger.info(f'Connect to broker: {str(reason_code)}')
        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        self.mqClient.subscribe(self.mq_topic)
        self.mqtt_connected = True


    def on_disconnect(self, mqClient, userdata, flags, reason_code, properties):
        """The callback for when the broker disconnects."""
        global logger
        self.mqtt_connected = False
        logger.warning(f'Broker disconnect!')


    def on_message(self, mqClient, userdata, msg):
        """The callback for when a PUBLISH message is received from the broker.
        Process ack, reset, and pong (response to ping) messages here."""
        global logger
        try:
            msgText = msg.payload.decode('utf-8')
            ellipsis = '…' if len(msgText) > 32 else ''
            logger.debug(f'Received {msgText}')
            # take the message apart, space-delimited
            # three possible messages:
            #   hostname ack serial hh:mm:ss
            #   hostname reset hh:mm:ss
            #   hostname pong hh:mm:ss (response to ping)
            msg = msgText.split()
            if msg[1] == 'ack':
                if msg[2] in self.retry:
                    del self.retry[msg[2]]
            elif msg[1] == 'pong' or msg[1] == 'reset':
                hostname = msg[0]
                # remove this remote from the offline list
                while hostname in self.offline:
                    self.offline.remove(hostname)
                # also remove any items in the retry dictionary for this remote
                remove = []
                for serial, v in self.retry.items():
                    if v[1] ==  hostname:
                        remove.append(serial)
                for s in remove:
                    del self.retry[s]
                logger.info(f'{msg[0]} is online.')
                # now process the remotes, make sure we send state to the
                # one that just came back online by clearing last_sched.
                for r in self.remotes:
                    if r.name == hostname:
                        r.last_sched = []
                self.process()
            else:
                logger.warning(f'Unknown message, ignored: {msgText}')
        except Exception as e:
            logger.error(f'Message receive fail: {str(e)}')
            return


    def process(self):
        """process all the remotes by checking their schedules and sending
        new state if a new schedule is in effect.
        each time we send a message to a remote, we place it in the retry
        dictionary, including a retry count. it will be removed from
        the retry dictionary upon receipt of an ack."""
        retry = 2
        for r in self.remotes:
            if r.enabled:
                if r.name in self.offline:
                    # just send a ping
                    hex_serial = f'{random.randrange(pow(2,32)):08x}'
                    self.mqClient.publish(r.name, f'Ping {hex_serial}')
                    logger.debug(f'Ping {r.name} {hex_serial}')
                else:
                    sched = r.process()
                    if sched:
                        # tag each publish with a random serial number of 8 hex digits
                        # add the publish information to the retry dict as:
                        #   hex_serial: [retries_left, hostname, sched_list]
                        hex_serial = f'{random.randrange(pow(2,32)):08x}'
                        self.retry[hex_serial] = [retry, r.name, sched]
                        self.mqClient.publish(r.name, f'{sched[1]} {hex_serial}')
                        logger.debug(f'Publish {r.name} {sched} {hex_serial}')


    def process_retries(self):
        """process the retry dictionary. resend any items that have
        remaining retries. items that are out of retries are removed
        from the retry dictionary and added to the offline list."""

        # as we process the retry dictionary items, we build this list of
        # dictionary items to be removed, i.e. those that are out of retries.
        remove = []

        for serial, v in self.retry.items():
            hostname = v[1]
            sched = v[2]
            if v[0] > 0:
                logger.debug(f'Retry {hostname} {sched} {serial}')
                self.mqClient.publish(hostname, f'{sched[1]} {serial}')
                v[0] -= 1
            else:
                logger.warning(f'Retries exhausted for {serial} {v}')
                remove.append(serial)

        # now we can remove the exhausted dictionary items and put them
        # in the offline list.
        # (python does not allow a dictionary to change size during iteration)
        for k in remove:
            hostname = self.retry[k][1]
            del self.retry[k]
            if hostname not in self.offline:
                self.offline.append(hostname)
            logger.warning(f'{hostname} is not responding.')


    def sleep_minute(self):
        """Sleep until the minute rolls over."""
        now = time.time()
        l = time.localtime(now)
        sleep_sec = 60 - l.tm_sec - (now -int(now))
        time.sleep(sleep_sec)
        #print(time.strftime("%F %T"))


    def write_pidfile(self):
        """write our pid to a file."""
        if not self.args.syntax:
            with open (f'{self.progname}.pid', 'w') as p:
                p.write(f'{str(os.getpid())}\n')


    def remove_pidfile(self):
        """remove the pid file. call when the program is terminating."""
        if not self.args.syntax:
            os.remove(f'{self.progname}.pid')
