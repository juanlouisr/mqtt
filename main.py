from umqttsimple import MQTTClient
from machine import Pin
import time as tm

print('ESP STARTED')

led_pin = Pin(2, Pin.OUT)
ac_pin = Pin(3, Pin.OUT)

start_ms = tm.ticks_ms()
led_start_ms = None
ac_start_ms = None
timer_ms = None
input_start_ms = None
input_duration_ms = None
timer_device = None

client_name = 'MyESP'
broker_address = '192.168.88.117'
mqtt_client = MQTTClient(client_name, broker_address, port=1883, keepalive=1000)
mqtt_client.connect()

def mqtt_receive_callback(topic, message):
    global led_start_ms, ac_start_ms, timer_ms, input_start_ms, input_duration_ms, timer_device
    command = message.decode('utf-8')
    command = command.split('|')
    print(command)
    
    if command[1] == '1':
        if command[0] == '1':
            led_pin.on()
            led_start_ms = tm.ticks_ms()
            timer_ms = None
        else:
            ac_pin.on()
            ac_start_ms = tm.ticks_ms()
            timer_ms = None
            
    elif command[1] == '2':
        if command[0] == '1':
            led_pin.off()
            led_start_ms = None
            timer_ms = None
        else:
            ac_pin.off()
            ac_start_ms = None
            timer_ms = None
            
    elif command[1] == '3':
        input_start_ms, input_duration_ms = command[2], command[3]
        timer_ms = tm.ticks_ms()
        timer_device = command[0]
        
    else:
        message = ''
        current_ms = tm.ticks_ms()
        
        if command[0] == '1':
            led_time_ms = led_start_ms if led_start_ms else current_ms
            message = f'{led_pin.value()}|{current_ms - led_time_ms}|{current_ms - start_ms}'
        else:
            ac_time_ms = ac_start_ms if ac_start_ms else current_ms
            message = f'{ac_pin.value()}|{current_ms - ac_time_ms}|{current_ms - start_ms}'
            
        mqtt_client.publish('status/receive', message)

mqtt_client.set_callback(mqtt_receive_callback)
mqtt_client.subscribe('status/send')

while True:
    mqtt_client.check_msg()
    
    current_ms = tm.ticks_ms()
    
    if timer_ms is not None:
        if tm.ticks_diff(current_ms, timer_ms) > input_start_ms and (tm.ticks_diff(current_ms, timer_ms)) < (input_start_ms+input_duration_ms):
            # Turn on device
            if timer_device == '0':
                led_pin.on()
                led_start_ms = tm.ticks_ms()
            else:
                ac_pin.on()
                ac_start_ms = tm.ticks_ms()
                
        elif (tm.ticks_diff(current_ms, timer_ms)) > (input_start_ms+input_duration_ms):
                # Turn off device
            if timer_device == '0':
                led_pin.off()
                led_start_ms = None
            else:
                ac_pin.off()
                ac_start_ms = None
                    
            timer_ms = None
            input_start_ms = None
            input_duration_ms = None
            timer_device = None

mqtt_client.disconnect()

