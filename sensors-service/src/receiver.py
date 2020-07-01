#!/usr/bin/env python

import pika
import json
import time
import threading
from retry import retry

credentials = pika.PlainCredentials('user', 'user')
tasksMap = {}

class MassTransitMessage(object):
    def __init__(self, destAddr, msgType, msg, headers = {}):
        self.destinationAddress = destAddr
        self.headers = headers
        self.messageType = [msgType]
        self.message = msg

    def toJson(self):
        return json.dumps(self.__dict__)


class Task(object):
    def __init__(self, nodeID, taskID, counter = 0):
        self.nodeID = nodeID
        self.taskID = taskID
        self.counter = counter
        self.threadHandle = threading.Thread(target = self.notifyLoop)

    # each thread needs separate connection and channel
    def connect(self):
        params = pika.ConnectionParameters(host="rabbitmq-broker", credentials=credentials)

        self.connection = pika.BlockingConnection(params)
        self.channel = self.connection.channel()

    def disconnect(self):
        if self.connection is not None:
            self.connection.close()

    def notifyLoop(self):
        while getattr(self, "do_run", True):
            payload = {'nodeID': self.nodeID,'taskID': self.taskID, 'counter': self.counter}
            msg = MassTransitMessage(
                destAddr = "rabbitmq://rabbitmq-broker/updateTask", msgType = 'urn:message:dotnetapp:UpdateTaskCounter', msg = payload)
            
            if self.channel is None:
                return

            self.channel.basic_publish(
                exchange='updateTask', routing_key='', body=msg.toJson())

            self.counter += 1
            time.sleep(2.0)


def startTaskCallback(ch, method, properties, body):
    msgDict = json.loads(body)["message"]
    reqObject = Task(msgDict["nodeID"], msgDict["taskID"])

    print(" [x] Received start task request - message: %r" % msgDict)
   
    if tasksMap.get(reqObject.taskID) is not None:
        return 

    tasksMap[reqObject.taskID] = reqObject
    reqObject.connect() 
    reqObject.threadHandle.start()


def endTaskCallback(ch, method, properties, body):
    msgDict = json.loads(body)["message"]
    taskObject = tasksMap.get(msgDict["taskID"])

    print(" [x] Received end task request - message: %r" % msgDict)

    if taskObject is None:
        return

    taskObject.do_run = False
    taskObject.disconnect()
    tasksMap.pop(msgDict["taskID"])


@retry(pika.exceptions.AMQPConnectionError, delay=5, jitter=(1, 3))
def consume():
    print("attempting to connect...")

    params = pika.ConnectionParameters(host="rabbitmq-broker", credentials=credentials)
    connection = pika.BlockingConnection(params)

    channel = connection.channel()

    channel.queue_declare(queue='startTask', durable=True)
    channel.queue_declare(queue='endTask', durable=True)

    channel.basic_consume(
        queue='startTask', on_message_callback=startTaskCallback, auto_ack=True)
    
    channel.basic_consume(
        queue='endTask', on_message_callback=endTaskCallback, auto_ack=True)

    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()
        connection.close()


consume()

