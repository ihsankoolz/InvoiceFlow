import json
import time
from datetime import datetime

import pika
import requests

# print("SCRIPT IS STARTING NOW !!!")

# CONFIGURATION
OUTSYSTEMS_URL = "https://personal-xowqm3b2.outsystemscloud.com/ActivityLog/rest/ActivityLogAPI/LogEvent"

def relay_to_outsystems(ch, method, properties, body):
    try:
        # parse the incoming RabbitMQ message
        payload_dict = json.loads(body)
        event_type = method.routing_key

        # PREPARE THE DATA FOR OUTSYSTEMS
        # map RabbitMQ data to OutSystems 'EventRequest' structure
        event_data = {
            "event_type": event_type,
            "payload": json.dumps(payload_dict), # store the whole JSON as a string
            "source_service": payload_dict.get("source", "RabbitMQ_Bridge"),
            "timestamp": datetime.now().isoformat(),
            "invoice_token": payload_dict.get("invoice_token", "N/A"),
            "user_id": payload_dict.get("user_id", 0),
            "severity": "INFO"
        }

        # SEND TO OUTSYSTEMS
        response = requests.post(OUTSYSTEMS_URL, json=event_data)

        if response.status_code == 200:
            print(f" [OK] Relayed {event_type} to OutSystems")
            ch.basic_ack(delivery_tag=method.delivery_tag)
        else:
            print(f" [ERROR] OutSystems returned {response.status_code}: {response.text}")
            # Negative-ack without requeue — message goes to DLQ
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    except Exception as e:
        print(f" [FAILED] Could not process message: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

# CONNECT TO RABBITMQ — retry until ready (RabbitMQ can be slow to start)
# 'localhost' works for local testing, 'rabbitmq' works for docker
_MAX_RETRIES = 15
_RETRY_DELAY = 5  # seconds
for _attempt in range(1, _MAX_RETRIES + 1):
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
        print(f" [*] Connected to RabbitMQ on attempt {_attempt}")
        break
    except pika.exceptions.AMQPConnectionError as _e:
        print(f" [!] RabbitMQ not ready (attempt {_attempt}/{_MAX_RETRIES}): {_e}")
        if _attempt == _MAX_RETRIES:
            raise
        time.sleep(_RETRY_DELAY)
channel = connection.channel()

# declare the exchange
channel.exchange_declare(exchange='invoiceflow_events', exchange_type='topic', durable=True)

# declare the DLQ first so it exists before the main queue references it
channel.queue_declare(queue='outsystems_audit_queue.dlq', durable=True)

# create the main bridge queue with dead-letter routing to the DLQ
result = channel.queue_declare(
    queue='outsystems_audit_queue',
    durable=True,
    arguments={
        'x-dead-letter-exchange': '',           # default exchange (direct)
        'x-dead-letter-routing-key': 'outsystems_audit_queue.dlq',
    }
)
queue_name = result.method.queue

# bind the queue to everything
channel.queue_bind(exchange='invoiceflow_events', queue=queue_name, routing_key='#')

print(' [*] Bridge is active. Listening for RabbitMQ events. To exit press CTRL+C')

channel.basic_consume(queue=queue_name, on_message_callback=relay_to_outsystems, auto_ack=False)
channel.start_consuming()
