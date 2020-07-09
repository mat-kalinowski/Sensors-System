import paho.mqtt.client as mqtt 
from config import config

mqtt_conf = config.opts["mqtt"]

class MQTTConn(object):

    def __init__(self):
        print("init function")

    def __enter__(self):
        print("entering")

    def __exit__(self):
        print("exiting")