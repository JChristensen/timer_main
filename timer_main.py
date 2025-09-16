#!/home/jack/.venv/bin/python3
#import random
#import string
#''.join(random.choices(string.hexdigits, k=16))

import logging
import paho.mqtt.client as mqtt
import signal
import socket
import sys
import time
import yaml

import timer_classes as timer

def main():
    global controller
    global logger
    controller = timer.Controller(__file__)
    logger = logging.getLogger('timer_main.py')

    # register signal handlers
    signal.signal(signal.SIGINT,  sigint_handler)
    signal.signal(signal.SIGTERM, sigterm_handler)
    signal.signal(signal.SIGHUP,  sighup_handler)

    controller.init_controller()

    # initialize mqtt
    mqClient = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, \
        client_id=f'{controller.prognamepy}@{socket.gethostname()}', clean_session=True)
    mqClient.on_connect = on_connect
    mqClient.on_message = on_message

    # try to connect to the broker
    retryInterval = 10
    nTry = 0
    connected = False
    while (not connected):
        try:
            nTry += 1
            mqClient.connect('z21')
            connected = True
        except Exception as e:
            logMsg = f'Connect to broker failed: {str(e)}, Retry in {str(retryInterval)} seconds.'
            logger.error(logMsg)
            time.sleep(retryInterval)
            if (nTry == 36):
                retryInterval = 3600
            elif (nTry == 24):
                retryInterval = 300
            elif (nTry == 12):
                retryInterval = 60

    mqClient.loop_start()

    while True:
        controller.sleep_minute()
        controller.process()


# The callback for when the client receives a CONNACK response from the server.
def on_connect(mqClient, userdata, flags, reason_code, properties):
    global logger
    logger.info(f'Connect to broker: {str(reason_code)}')
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    mqClient.subscribe('timer_main')


# The callback for when a PUBLISH message is received from the server.
def on_message(mqClient, userdata, msg):
    global logger
    try:
        msgText = msg.payload.decode('utf-8')
        ellipsis = '…' if len(msgText) > 32 else ''
        logger.debug(f'Received [{msg.topic}] {msgText[:32]}{ellipsis}')
    except Exception as e:
        logger.error(f'Message receive fail: {str(e)}')
        return


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
