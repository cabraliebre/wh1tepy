import time                                   #https://docs.micropython.org/en/v1.5/pyboard/library/time.html
import sys                                    #https://docs.micropython.org/en/v1.5/pyboard/library/sys.html
#from lib.umqtt.simple2 import MQTTClient      #https://github.com/fizista/micropython-umqtt.simple2
from umqttsimple import MQTTClient
import ubinascii
import machine                                #https://docs.micropython.org/en/latest/library/machine.html
from machine import Pin, RTC, Timer, PWM
import ntptime                                #NTP-time (from pool.ntp.org)
import micropython
import network
import esp                                    #https://docs.micropython.org/en/latest/library/esp.html
esp.osdebug(None)
import esp32                                  #https://docs.micropython.org/en/latest/library/esp32.html
import gc
gc.collect()
import ujson
import os

############################ Global Variables ###################################

#MQTT Topics
# global client_id, station
# 
# prefix_topic = b'vick-dev/'
# main_topic = prefix_topic + b'wh1tepy/WH1TEPY-' + client_id
# discovery_topic = b'vick-dev/homeassistant'

#MQTT broker
mqtt_server = "mqtt.iotwired.link"
mqtt_port = 8803
mqtt_user = "mqtt"
mqtt_pass = "UPCmn2019"


################################## F(x) ########################################
#MQTT
    
# def mqtt_incoming(topic, msg):
#     global sch0
#     
#     try:
#         tmp = ujson.loads(msg)
#         print("json message incoming: %s" % tmp)
#     except:
#         print("simple message incoming: %s" % msg)
#         return
#     
#     if (topic == main_topic + b'/scheduler/0/set'):
#         if (("weekdays" in tmp) and (len(tmp["weekdays"]) == 7)):
#             f=open("scheduler/sch0.json","w") # opens a file for writing.
#             f.write(ujson.dumps(tmp))
#             f.close()
#             sch0 = tmp
#             print('Save json weekdays')
#             for day in range(0, 7): 
#                 print('\t[Day %d] -> %s' % (day,(sch0["weekdays"][day])))
#             #pub(b'/scheduler/0', ujson.dumps(tmp), True)
#     elif (topic == main_topic + b'/scheduler/0/get'):
#         if (("weekdays" in tmp) and (len(tmp["weekdays"]) == 7)):
#             print('Check weekdays json')
#             pub(b'/scheduler/0/sync', str(sch0 == tmp), True)
#     elif (topic == main_topic + b'/digital-outputs/set'):    
#         for i in range(0, 6):
#             output = ("dout%s" % str(i))
#             if (output in tmp):
#                 state = tmp[output]
#                 state_omap[i] = int(state)
#                 pub((b'/digital-outputs/%d' % i), str(state_omap[i]), False)
        
def mqtt_connect():
    start = time.ticks_ms()
    global mqtt, mqtt_server
    
    print('Connecting to broker %s:%d with SSL' % (mqtt_server, mqtt_port))
    
    mqtt=MQTTClient(client_id, mqtt_server, mqtt_port, mqtt_user, mqtt_pass, 5, True)
    mqtt.set_callback(mqtt_incoming)
    mqtt.set_last_will(main_topic + b'/status', "0", True, 0)
    mqtt.connect()
    mqtt.DEBUG = True
    pub(b'/status', "1", True)
    mqtt_subs()
    pub_info()
    delta = time.ticks_diff(time.ticks_ms(), start) # compute time difference
    print('Service MQTT run and connected with broker (%dms)' % (delta))
    pwm = PWM(Pin(2), freq=60, duty=5)
    return mqtt      

# def pub_sys():
#     global f_pub_sys
#     if (time.time() - f_pub_sys) > 300:
#         sys = {}
#         sys["freeMem"] = gc.mem_free()
#         sys["uptime"] = time.time()
#         sys["temp"] =  "{:.1f}".format((esp32.raw_temperature() - 32) * 5/9)
#         sys["rssi"] = station.status('rssi')
# 
#         pub(b'/sys', ujson.dumps(sys), True)
#         f_pub_sys = time.time()
# 
# def pub_info():
#     info = {}
#     info["board"] = sys.platform.upper()
#     info["version"] = "0.1"
#     info["upython_versio"] = sys.version
#     info["ip"] = station.ifconfig()[0]
# 
#     pub(b'/info', ujson.dumps(info), True)
# 
# def mqtt_subs():
#     mqtt.subscribe(main_topic + b'/digital-outputs/set')
#     for i in range(0, len(omap)):
#         mqtt.subscribe(main_topic + (b'/scheduler/%d/set') % i)
#         mqtt.subscribe(main_topic + (b'/scheduler/%d/get') % i)
#         
# def restart_and_reconnect():
#     print('Failed to connect to MQTT broker. Reconnecting...')
#     time.sleep(5)
#     machine.reset()         
# 
# def pub(addtopic, payload, retain):
#     global mqtt
#     topic = main_topic + addtopic
#     mqtt.publish(topic, payload, retain)
#     
# def pub_outputs(retain):
#     for i in range(0,6):
#         pub((b'/digital-outputs/%d' % i), str(state_omap[i]), retain)
# 
# def pub_inputs(retain):
#     for i in range(0,6):
#         pub((b'/digital-inputs/%d' % i), str(state_imap[i]), retain)