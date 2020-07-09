#!/usr/bin/env python

import pika
import json
import time
import threading
from socket import error as socket_error
from retry import retry

#import mqtt_conn
import amqp_conn

amqp_bus = amqp_conn.AMQPConn()
#mqtt_bus = MQTTConn()

client = mqtt.Client("sensors-service")

nodeMap = {}

class Node(object):
    def __init__(self, node_id, task_id = -1, counter = 0):
        self.node_id = node_id
        self.task_id = task_id    # -1 if node is currently without any task, otw -> id of given task
        self.counter = counter

    def switch_task(self, task_id):
        self.task_id = task_id
        self.counter = 0

    def to_json(self):
        return json.dumps(self.__dict__)


def start_task_callback(ch, method, properties, body):
    msg_dict = json.loads(body)["message"]
    node_obj = node_map.get(msg_dict["nodeID"])

    print(" [x] Received start task request - message: %r" % msg_dict)
   
    if node_obj is None:
        return 

    node_obj.switch_task(msg_dict["taskID"])
    client.publish(payload="", topic="/tasks/start/{}".format(msg_dict['nodeID']))


def end_task_callback(ch, method, properties, body):
    msg_dict = json.loads(body)["message"]
    node_obj = node_map.get(msg_dict[nodeID])

    print(" [x] Received end task request - message: %r" % msgDict)
   
    if node_obj is None:
        return 

    node_obj.switch_task(-1)
    client.publish(payload="",topic="/tasks/end/{}".format(msg_dict['nodeID']))
    

def tasks_status_callback(ch, method, properties, body):
    print(" [x] Received nodes status request")
    print("hello - i will provide array with all nodes status")


def mqtt_on_connect(client, userdata, flags, rc):    
    client.subscribe("nodes/discover/response")
    client.publish("nodes/discover", payload="")


def mqtt_on_message(client, userdata, msg):
    if msg.topic == '/nodes/discover/response':
        if node_map.get(msg.payload) is not None:
            node_map[msg.payload] = Node(msg.payload)

    elif msg.topic == '/nodes/status':
        task_data = json.loads(msg.payload)
        node_obj = node_map.get(task_data['nodeID'])
        
        if node_obj is not None:
            node_obj.counter = task_data.counter
            amqp_bus.publish(message=node_obj.to_json(), )


@retry(socket_error, delay=5, jitter=(1, 3))
def mqtt_connect():
    print("connecting to mqtt broker")
    global client

    client.username_pw_set("user", "user")
    client.connect("localhost")
     
    client.on_connect = mqtt_on_connect
    client.on_message = mqtt_on_message

    client.loop_start()        # separate thread looping through receive and send buffers, handling reconnects


endpoints = [('startTask', startTaskCallback),
            ('endTask', endTaskCallback),
            ('taskStatus', tasksStatusCallback)]


amqp_thread = threading.Thread(target=conf.start_consumer, args=(endpoints,))
amqp_thread.start() 

mqtt_connect()
amqp_thread.join()