#!/usr/bin/env python

import pika
from retry import retry

def nodesStatusCallback(ch, method, properties, body):
    print(" [x] Received node status callback: %r" % body)


def startTaskCallback(ch, method, properties, body):
    print(" [x] Received start task request: %r" % body)


def endTaskCallback(ch, method, properties, body):
    print(" [x] Received end task request: %r" % body)


credentials = pika.PlainCredentials('user', 'user')

@retry(pika.exceptions.AMQPConnectionError, delay=5, jitter=(1, 3))
def consume():
    print("receiver: attempting to connect")

    connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='rabbitmq', credentials=credentials))

    channel = connection.channel()

    channel.queue_declare(queue='nodesStatus')
    channel.queue_declare(queue='startTask', durable=True)
    channel.queue_declare(queue='endTask')

    channel.basic_consume(
        queue='nodesStatus', on_message_callback=nodesStatusCallback, auto_ack=True)
    
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

