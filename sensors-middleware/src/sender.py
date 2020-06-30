#!/usr/bin/env python

import pika
from retry import retry
import json

credentials = pika.PlainCredentials('user', 'user')

@retry(pika.exceptions.AMQPConnectionError, delay=5, jitter=(1, 3))
def consume():
    print("sender: attempting to connect")

    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host='rabbitmq', credentials=credentials))

    channel = connection.channel()

    channel.queue_declare(queue='nodesStatus')
    channel.queue_declare(queue='startTask', durable=False)
    channel.queue_declare(queue='endTask')

    channel.basic_publish(exchange='', routing_key='startTask', body=json.dumps({'nodeId': 123}))
    channel.basic_publish(exchange='', routing_key='endTask', body=json.dumps({'nodeId': 123}))
    channel.basic_publish(exchange='', routing_key='nodesStatus', body=json.dumps({'nodeId': 123}))

    connection.close()

consume()
