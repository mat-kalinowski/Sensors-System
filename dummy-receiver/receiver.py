#!/usr/bin/env python
import pika
from retry import retry

def callback(ch, method, properties, body):
    print(" [x] Received %r" % body)

credentials = pika.PlainCredentials('user', 'user')

print("receiver: started ")

@retry(pika.exceptions.AMQPConnectionError, delay=5, jitter=(1, 3))
def consume():
    print("receiver: attempting to connect")

    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host='rabbitmq-broker', credentials=credentials))

    channel = connection.channel()
    channel.queue_declare(queue='hello')
    channel.basic_consume(
        queue='hello', on_message_callback=callback, auto_ack=True)

    #print(' [*] Waiting for messages. To exit press CTRL+C')
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()
        connection.close()

consume()

