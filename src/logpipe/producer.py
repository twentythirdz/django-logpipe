from .backend import get_producer_backend
from .constants import FORMAT_JSON
from .format import render
from . import settings
from kafka import KafkaProducer
from confluent_kafka import SerializingProducer
from confluent_kafka.serialization import StringSerializer
import logging
import json

logger = logging.getLogger(__name__)


class ConfluentProducer(object):

    def __init__(self, topic_name, serializer_class, json_serializer=None):
        self.json_serializer = json_serializer
        self.client = self.get_client_config()
        self.topic_name = topic_name
        self.serializer_class = serializer_class

    def send(self, instance, renderer=None):
        # Instantiate the serialize
        ser = self.serializer_class(instance=instance)

        # Get the message type and version
        message_type = self.serializer_class.MESSAGE_TYPE
        version = self.serializer_class.VERSION

        # Get the message's partition key
        key_field = getattr(self.serializer_class, 'KEY_FIELD', None)
        key = None
        if key_field:
            key = str(ser.data[key_field])
        # Render everything into a string
        renderer = settings.get('DEFAULT_FORMAT', FORMAT_JSON)
        body = {
            'version': version,
            'message': ser.data,
        }
        serialized_data = render(renderer, body)

        json_data = json.loads(serialized_data)['message']

        # Send the message data
        self.client.produce(self.topic_name, key=key,
                            value=json_data if self.json_serializer else json.dumps(json_data))
        self.client.flush()
        logger.debug('Sent message with type "%s", key "%s" to topic "%s"' % (message_type, key, self.topic_name))

    def get_client_config(self):
        kwargs = {
            'bootstrap.servers': settings.get('KAFKA_BOOTSTRAP_SERVERS'),
        }
        kwargs.update(settings.get('CONFLUENT_PRODUCER_KWARGS', {}))
        kwargs.update({'key.serializer': StringSerializer('utf_8')})
        kwargs.update({'value.serializer': self.json_serializer} if self.json_serializer else {})
        return SerializingProducer(kwargs)


class BasicProducer(object):

    def __init__(self, topic_name, serializer_class):
        self.client = self.get_client_config()
        self.topic_name = topic_name
        self.serializer_class = serializer_class

    def send(self, instance, renderer=None):
        # Instantiate the serialize
        ser = self.serializer_class(instance=instance)

        # Get the message type and version
        message_type = self.serializer_class.MESSAGE_TYPE
        version = self.serializer_class.VERSION

        # Get the message's partition key
        key_field = getattr(self.serializer_class, 'KEY_FIELD', None)
        key = None
        if key_field:
            key = str(ser.data[key_field])
        # Render everything into a string
        renderer = settings.get('DEFAULT_FORMAT', FORMAT_JSON)
        body = {
            'version': version,
            'message': ser.data,
        }
        serialized_data = render(renderer, body)

        json_data = json.loads(serialized_data)['message']

        # Send the message data
        self.client.send(self.topic_name, key=key.encode('utf-8'), value=json.dumps(json_data).encode('utf-8'))
        self.client.flush()
        logger.debug('Sent message with type "%s", key "%s" to topic "%s"' % (message_type, key, self.topic_name))

    def get_client_config(self):
        kwargs = {
            'bootstrap_servers': settings.get('KAFKA_BOOTSTRAP_SERVERS'),
            'retries': settings.get('KAFKA_MAX_SEND_RETRIES', 0)
        }
        kwargs.update(settings.get('BASIC_KAFKA_PRODUCER_KWARGS', {}))

        return KafkaProducer(**kwargs)



