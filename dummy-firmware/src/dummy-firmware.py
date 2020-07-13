#!/usr/bin/env python

import paho.mqtt.client as mqtt
import threading
from socket import error as socket_error
from retry import retry
import time
import json


def mqtt_connection_handler(client, userdata, flags, rc):
    node_obj = userdata["node"]

    client.subscribe("nodes/discover")
    client.subscribe("tasks/start/{}".format(node_obj.node_id))
    client.subscribe("tasks/end/{}".format(node_obj.node_id))

    print('Node{}: connected to mqtt broker'.format(node_obj.node_id))


def mqtt_message_handler(client, userdata, msg):
    node_obj = userdata["node"]

    if msg.topic == 'tasks/start/{}'.format(node_obj.node_id):
        node_obj.counter = 0
        node_obj.do_run = True

        thread = threading.Thread(target=node_obj.fw_loop)
        thread.start()

    elif msg.topic == 'tasks/end/{}'.format(node_obj.node_id):
        node_obj.do_run = False

    if msg.topic == 'nodes/discover':
        client.publish(payload=node_obj.node_id, topic="nodes/discover/response")


class Node(object):
    def __init__(self, node_id):
        self.node_id = node_id
        self.counter = 0

    @retry(socket_error, delay=5, jitter=(1, 3))
    def connect(self):
        client = mqtt.Client(self.node_id, userdata={'node': self})

        client.username_pw_set("user", "user")
        client.connect("rabbitmq-broker", 1883, 60)

        client.on_message = mqtt_message_handler
        client.on_connect = mqtt_connection_handler

        self.client_handle = client
        client.loop_forever()

    def fw_loop(self):
        while getattr(self, "do_run", True):
            self.counter += 1

            json_msg = json.dumps({'nodeID': self.node_id,'counter': self.counter})
            self.client_handle.publish("nodes/status", json_msg)

            time.sleep(2.0)


node1 = Node("123")
thread1 = threading.Thread(target = node1.connect)
thread1.start()

node2 = Node("124")
thread2 = threading.Thread(target = node2.connect)
thread2.start()

thread1.join()
thread2.join()


