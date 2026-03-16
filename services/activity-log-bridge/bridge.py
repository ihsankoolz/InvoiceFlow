import pika
import requests
import json
from datetime import datetime

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
        else:
            print(f" [ERROR] OutSystems returned {response.status_code}: {response.text}")

    except Exception as e:
        print(f" [FAILED] Could not process message: {e}")

# CONNECT TO RABBITMQ 
# 'localhost' works for local testing, 'rabbitmq' works for Docker.
connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
channel = connection.channel()

# declare the exchange 
channel.exchange_declare(exchange='invoiceflow_events', exchange_type='topic')

# create a temporary queue for bridge
result = channel.queue_declare(queue='outsystems_audit_queue', durable=True)
queue_name = result.method.queue

# bind the queue to everything
channel.queue_bind(exchange='invoiceflow_events', queue=queue_name, routing_key='#')

print(' [*] Bridge is active. Listening for RabbitMQ events. To exit press CTRL+C')

channel.basic_consume(queue=queue_name, on_message_callback=relay_to_outsystems, auto_ack=True)
channel.start_consuming()