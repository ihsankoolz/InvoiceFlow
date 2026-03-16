import pika
import requests
import json
from datetime import datetime

# print("!!! SCRIPT IS STARTING NOW !!!") 

# 1. YOUR CONFIGURATION
# Replace this with your actual OutSystems API URL from Postman
OUTSYSTEMS_URL = "https://personal-xowqm3b2.outsystemscloud.com/ActivityLog/rest/ActivityLogAPI/LogEvent"

def relay_to_outsystems(ch, method, properties, body):
    try:
        # Parse the incoming RabbitMQ message
        payload_dict = json.loads(body)
        event_type = method.routing_key
        
        # 2. PREPARE THE DATA FOR OUTSYSTEMS
        # We map RabbitMQ data to your OutSystems 'EventRequest' structure
        event_data = {
            "event_type": event_type,
            "payload": json.dumps(payload_dict), # Store the whole JSON as a string
            "source_service": payload_dict.get("source", "RabbitMQ_Bridge"),
            "timestamp": datetime.now().isoformat(),
            "invoice_token": payload_dict.get("invoice_token", "N/A"),
            "user_id": payload_dict.get("user_id", 0),
            "severity": "INFO"
        }

        # 3. SEND TO OUTSYSTEMS
        response = requests.post(OUTSYSTEMS_URL, json=event_data)
        
        if response.status_code == 200:
            print(f" [OK] Relayed {event_type} to OutSystems")
        else:
            print(f" [ERROR] OutSystems returned {response.status_code}: {response.text}")

    except Exception as e:
        print(f" [FAILED] Could not process message: {e}")

# 4. CONNECT TO RABBITMQ
# Since you're running this inside the InvoiceFlow docker network eventually, 
# 'localhost' works for local testing, 'rabbitmq' works for Docker.
connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
channel = connection.channel()

# Declare the exchange (must match your project config)
channel.exchange_declare(exchange='invoiceflow_events', exchange_type='topic')

# Create a temporary queue for this bridge
result = channel.queue_declare(queue='outsystems_audit_queue', durable=True)
queue_name = result.method.queue

# Bind the queue to EVERYTHING (the # wildcard)
channel.queue_bind(exchange='invoiceflow_events', queue=queue_name, routing_key='#')

print(' [*] Bridge is active. Listening for RabbitMQ events. To exit press CTRL+C')

channel.basic_consume(queue=queue_name, on_message_callback=relay_to_outsystems, auto_ack=True)
channel.start_consuming()