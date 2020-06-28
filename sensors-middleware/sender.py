#!/usr/bin/env python
import pika
from retry import retry

credentials = pika.PlainCredentials('user', 'user')

@retry(pika.exceptions.AMQPConnectionError, delay=5, jitter=(1, 3))
def consume():
    print("sender: attempting to connect")
    
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host='rabbitmq-broker', credentials=credentials))

    channel = connection.channel()
    channel.queue_declare(queue='hello')
    channel.basic_publish(exchange='', routing_key='hello', body='Hello World!')
    
    print(" [x] Sent 'Hello World!'")
    connection.close()

consume()
