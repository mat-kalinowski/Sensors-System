import pika
import json
from retry import retry
from config import config

amqp_conf = config.amqp

class MassTransitMessage(object):

    def __init__(self, endpoint, message, headers = {}):
        self.destinationAddress = "rabbitmq://{}/{}".format(amqp_conf["hostname"], endpoint)
        self.headers = {}
        self.messageType = ["urn:message:{}:{}".format(amqp_conf["dotnet-service"], amqp_conf["endpoints"][endpoint])]
        self.message = message

    def to_json(self):
        return json.dumps(self.__dict__)


# separate connection for each thread

class AMQPConsumer(object):

    credentials = pika.PlainCredentials(amqp_conf["username"], amqp_conf["password"])
    params = pika.ConnectionParameters(host=amqp_conf["hostname"], credentials=credentials)
    
    @retry(pika.exceptions.AMQPConnectionError, delay=5, jitter=(1, 3))
    def __init__(self, *args, **kwargs):
        self.conn = pika.BlockingConnection(self.params)
        self.channel = self.conn.channel()

    def consume(self, ep_callbacks):
        for ep in ep_callbacks:
            self.channel.queue_declare(ep[0], durable=True)

            self.channel.basic_consume(
                queue=ep[0], 
                on_message_callback=ep[1], 
                auto_ack=True)

        self.channel.start_consuming()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.conn.close()


class AMQPPublisher(object):

    credentials = pika.PlainCredentials(amqp_conf["username"], amqp_conf["password"])
    params = pika.ConnectionParameters(host=amqp_conf["hostname"], credentials=credentials)
    
    @retry(pika.exceptions.AMQPConnectionError, delay=5, jitter=(1, 3))
    def __init__(self, *args, **kwargs):
        self.conn = pika.BlockingConnection(self.params)
        self.channel = self.conn.channel()


    def publish(self, message, exchange):
        msg = MassTransitMessage(endpoint=exchange, message=message)

        if self.channel is None:
            return

        self.channel.basic_publish(
            exchange=exchange, routing_key='', body=msg.to_json())