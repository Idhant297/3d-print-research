import paho.mqtt.client as mqtt
import json
import ssl
import os
from dotenv import load_dotenv

def update_json(new_data, filename="latest_message.json"):
    try:
        # Read existing data if file exists
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                existing_data = json.load(f)
        else:
            existing_data = {}
        
        # Deep merge the new data with existing data
        def deep_update(source, updates):
            for key, value in updates.items():
                if key in source and isinstance(source[key], dict) and isinstance(value, dict):
                    deep_update(source[key], value)
                else:
                    source[key] = value
            return source
        
        # Update existing data with new values
        updated_data = deep_update(existing_data, new_data)
        
        # Write back to file
        with open(filename, 'w') as f:
            json.dump(updated_data, f, indent=4)
            
        return updated_data
    except Exception as e:
        print(f"Error updating JSON: {e}")
        return None

def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    client.subscribe("device/01S00C3A2500071/report")
    print("Subscribed to device/01S00C3A2500071/report")

def on_message(client, userdata, message):
    try:
        # Parse incoming message
        new_data = json.loads(message.payload.decode())
        
        # Update only changed values
        updated_data = update_json(new_data)
        print(f"Updated values for topic: {message.topic}")

    except Exception as e:
        print(f"Error processing message: {e}")

# Create client
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

# Set up TLS
client.tls_set(cert_reqs=ssl.CERT_NONE)
client.tls_insecure_set(True)

# Load environment variables
load_dotenv()

# Set credentials from .env file
client.username_pw_set(os.getenv("USER"), os.getenv("PWD"))

# Broker details from .env file
broker_address = os.getenv("IP_ADDRESS")
port = int(os.getenv("PORT"))

try:
    client.connect(broker_address, port, 60)
    print(f"Connected to broker at {broker_address}:{port}")
    client.loop_forever()
except Exception as e:
    print(f"Failed to connect: {e}")