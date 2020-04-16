from time import sleep
from umqtt.simple import MQTTClient
from machine import Pin
from dht import DHT22

SERVER = 'mqtt.iotwired.link'  # MQTT Server Address (Change to the IP address of your Pi)
CLIENT_ID = 'ESP32_DHT22_Sensor'
TOPIC = b'temp_humidity'

client = MQTTClient(CLIENT_ID, SERVER, 8803, "mqtt", "UPCmn2019", 10, True)
client.connect()   # Connect to MQTT broker

sensor = DHT22(Pin(15, Pin.IN, Pin.PULL_UP))   # DHT-22 on GPIO 15 (input with internal pull-up resistor)

def sub_cb(topic, msg):
    if msg == b"1":
        print('ok')
    else:
        print((topic, msg))

client.DEBUG = True
client.set_last_will("uPy/status", b"offline", True)
client.set_callback(sub_cb)

if not client.connect(clean_session=False):
    print("New session being set up")
    client.subscribe(b"uPy/set")

while 1:
    client.wait_msg()

client.disconnect()


#while True:
#    try:
#        #sensor.measure()   # Poll sensor
#        t = 25.65 #sensor.temperature()
#        h = 45.9 #humidity()
#        if isinstance(t, float) and isinstance(h, float):  # Confirm sensor results are numeric
#            msg = (b'{0:3.1f},{1:3.1f}'.format(t, h))
#            client.publish(TOPIC, msg)  # Publish sensor data to MQTT topic
#            print(msg)
#        else:
#            print('Invalid sensor readings.')
#    except OSError:
#        print('Failed to read sensor.')
#    sleep(4)
