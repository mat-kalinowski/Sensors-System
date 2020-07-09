#!/usr/bin/env python

import paho.mqtt.client as mqtt
import threading
from socket import error as socket_error
from retry import retry
import time


def mqtt_connection_handler(client, userdata, flags, rc):
    client.subscribe("nodes/discover")
    client.subscribe("tasks/start/{}".format(self.node_id))
    client.subscirbe("tasks/stop/{}".format(self.node_id))


def mqtt_message_handler(client, userdata, msg):
    if msg.topic == 'task/start/':
        print("starting task")
        self.counter = 0
        self.fwLoop()
    
    elif msg.topic == 'task/end/':
        print("ending task")
        self.do_run = False

    elif msg.topic == 'nodes/discover':
        client.publish(payload=userdata, topic="nodes/discover/response")


class Node(object):
    def __init__(self, nodeID):
        self.node_id = node_id
        self.counter = 0

    @retry(socket_error, delay=5, jitter=(1, 3))
    def connect(self):
        client = mqtt.Client(self.node_id, userdata=self.node_id)

        client.username_pw_set("user", "user")
        client.connect("localhost", 1883, 60)

        client.on_message = mqtt_message_handler
        client.on_connect = mqtt_connection_handler

        self.client_handle = client
        client.loop_forever()

    def fwLoop(self):
        while getattr(self, "do_run", True):
            self.counter += 1
            self.client_handle.publish("/nodes/status/{}".format(self.node_id))

            time.sleep(2.0)


node1 = Node("123")
thread1 = threading.Thread(target = node1.connect)
thread1.start()

node2 = Node("124")
thread2 = threading.Thread(target = node2.connect)
thread2.start()

thread1.join()
thread2.join()



