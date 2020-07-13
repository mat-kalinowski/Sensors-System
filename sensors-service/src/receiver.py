#!/usr/bin/env python

import pika
import json
import threading
import paho.mqtt.client as mqtt 
import time
import socket

import mqtt_conn
import amqp_conn

node_map = {}
tasks_map = {}

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
        mqtt_bus.publish(message="", topic="nodes/discover")
        return

    node_obj.switch_task(msg_dict["taskID"])
    tasks_map[node_obj.task_id] = node_obj

    mqtt_bus.publish(message="", topic="tasks/start/{}".format(node_obj.node_id))


def end_task_callback(ch, method, properties, body):
    msg_dict = json.loads(body)["message"]
    node_obj = tasks_map.get(msg_dict["taskID"])

    print(" [x] Received end task request - message: %r" % msg_dict)
   
    if node_obj is None:
        return 

    tasks_map.pop(node_obj.task_id)
    node_obj.switch_task(-1)

    mqtt_bus.publish(message="", topic="tasks/end/{}".format(node_obj.node_id))
    
# sending back to updateStatus exchange

def nodes_status_callback(ch, method, properties, body):
    res_arr = []

    print(" [x] Received nodes status request")

    for node_tuple in node_map.items():
        node = node_tuple[1]
        
        active = True if node.task_id >= 0 else False
        res_arr.append({"nodeID": node.node_id, "isActive": active})

    amqp_pub.publish(message=res_arr, exchange='updateStatus')


def mqtt_on_connect(client, userdata, flags, rc):  
    client.subscribe("nodes/discover/response")
    client.subscribe("nodes/status")
    client.publish("nodes/discover", payload="")


def mqtt_on_message(client, userdata, msg):
    str_payload = msg.payload.decode("utf-8") 

    if msg.topic == 'nodes/discover/response':
        if node_map.get(str_payload) is None:
            node_map[str_payload] = Node(str_payload)

    elif msg.topic == 'nodes/status':
        task_data = json.loads(msg.payload)
        node_obj = node_map.get(task_data['nodeID'])
        
        if node_obj is not None and node_obj.counter != task_data['counter']:
            node_obj.counter = task_data['counter']
            ser_node = node_obj.__dict__.copy()

            ser_node["nodeID"] = ser_node.pop("node_id")
            ser_node["taskID"] = ser_node.pop("task_id")

            amqp_pub.publish(message=ser_node, exchange='updateTask')


endpoints = [('startTask', start_task_callback),
            ('endTask', end_task_callback),
            ('nodesStatus', nodes_status_callback)]

time.sleep(20.0)

hostname = socket.gethostname()
ip_address = socket.gethostbyname(hostname)

print("up and running - ip address: {}".format(ip_address))

amqp_bus = amqp_conn.AMQPConsumer()
amqp_pub = amqp_conn.AMQPPublisher()
mqtt_bus = mqtt_conn.MQTTConn(on_connect=mqtt_on_connect, on_message=mqtt_on_message)

amqp_thread = threading.Thread(target=amqp_bus.consume, args=(endpoints,))
amqp_thread.start() 

amqp_thread.join()