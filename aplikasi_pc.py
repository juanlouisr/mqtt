from paho.mqtt.client import Client
from typing import Optional
import paho.mqtt.publish as publish
import threading

broker_address = '192.168.88.117'

def publish_message_to_topic(topic, message, verbose=False):
    if verbose:
        print(f'Sending message `{message}` to topic `{topic}`')
    publish.single(topic, message, hostname=broker_address)

def subscribe_simple(
    topics: str | list[str],
    hostname: str,
    timeout: Optional[float] = None,
    **mqtt_kwargs,
):
    lock: Optional[threading.Lock]
    
    # Function called when connection to MQTT broker is established
    def on_connect(client, userdata, flags, rc):
        client.subscribe(userdata['topics']) # subscribe to topics specified in userdata
        return

    # Function called when a message is received
    def on_message(client, userdata, message):
        userdata['messages'] = message # store the received message in userdata
        client.disconnect() # disconnect from MQTT broker
        if userdata['lock']:
            userdata['lock'].release() # release the lock to indicate that a message has been received
        return

    # Create a lock if a timeout has been specified, otherwise set lock to None
    if timeout:
        lock = threading.Lock()
    else:
        lock = None

    # Convert topics to a list if it is a string
    topics = [topics] if isinstance(topics, str) else topics
    # Create a dictionary containing userdata to pass to the MQTT client
    userdata: dict[str, any] = {
        'topics': [(topic, mqtt_kwargs.pop('qos', 0)) for topic in topics], # list of topics to subscribe to with QoS level specified
        'messages': None, # placeholder for received message
        'lock': lock, # lock for synchronizing threads if timeout is specified
    }

    # Create MQTT client with userdata and set callback functions
    client = Client(userdata=userdata)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(hostname) # connect to MQTT broker

    # If no timeout specified, run MQTT client loop indefinitely
    if timeout is None:
        client.loop_forever()
    # Otherwise, wait for a message for a maximum of timeout seconds
    else:
        assert lock is not None
        lock.acquire()
        client.loop_start()
        lock.acquire(timeout=timeout)
        client.loop_stop()
        client.disconnect()

    # Return the received message
    return userdata['messages']

def run_device_manager(verbose=False):
    while True:
        # Prompt user for device and command
        device = input('\nWhich device?\n1. LED\n2. AC\n>> ')
        order = input('What would you like to do?\n1. Turn ON\n2. Turn OFF\n3. Set a timer\n4. Check status\n5. Go back\n>> ')
        command = f'{device}|{order}'

        # If command is to set a timer, prompt user for additional input
        if order == '3':
            input_time = input('On Time:\n>> ')
            input_duration = input('Duration:\n>> ')
            command = f'{command}|{input_time}|{input_duration}'

        # Publish command to MQTT broker
        publish_message_to_topic('status/send', command)
    
        # If command is to get status, wait for callback with 3 seconds timeout
        if order == '4':
            received_message = subscribe_simple('status/receive', hostname=broker_address, timeout=3)
            if received_message is not None:
                received_message = received_message.payload.decode()
                status = received_message.split('|')
                print('Device:', 'LED' if device == '1' else 'AC')
                print('Status:', 'ON' if status[0] == '1' else 'OFF')
                print('On Time:',  int(status[1]) // 1000, "seconds")
                print('Connection Time:',  int(status[2]) // 1000, "seconds")
            else:
                print('Timed out waiting for message')
            if verbose:
                print('Received message:', received_message)



if __name__ == '__main__':
    run_device_manager()