import paho.mqtt.client as mqtt 
from socket import error as socket_error
from retry import retry
from config import config

mqtt_conf = config.mqtt

class MQTTConn(object):

    @retry(socket_error, delay=5, jitter=(1, 3))
    def __init__(self, on_connect, on_message):
        client = mqtt.Client("sensors-service")
        client.username_pw_set(mqtt_conf["username"], mqtt_conf["password"])
        client.connect(mqtt_conf["hostname"])
     
        client.on_connect = on_connect
        client.on_message = on_message

        client.loop_start()        # separate thread looping through receive and send buffers, handling reconnects
        self.client = client

    def publish(self, message, topic):
        self.client.publish(topic=topic, payload=message)

