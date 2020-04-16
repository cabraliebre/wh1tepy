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
global client_id, station

prefix_topic = b'vick-dev/'
main_topic = prefix_topic + b'wh1tepy/WH1TEPY-' + client_id
discovery_topic = b'vick-dev/homeassistant'

#MQTT broker
mqtt_server = "mqtt.iotwired.link"
mqtt_port = 8803
mqtt_user = "mqtt"
mqtt_pass = "UPCmn2019"

#Timmer loop
last_message = 0
message_interval = 5
counter = 0
f_pub_sys = 0

#GPIO
global omap, omap_pin, state_omap, last_state_omap
global imap, imap_pin, state_imap, last_state_imap

global year, month, mday, weekday, hour, minute, second, milisecond

#scheduler
sch0 = {}

################################## F(x) ########################################
#NTPTime
def ntp(tprint, value):
    try:
        ntptime.settime()                       #https://github.com/micropython/micropython/blob/master/ports/esp8266/modules/ntptime.py
    except:
        print("Error to try sync with NTP server")
        time.sleep(1)
        ntp(1,0)
    (year, month, mday, weekday, hour, minute, second, milisecond)=RTC().datetime()
    RTC().init((year, month, mday, weekday, hour+2, minute, second, milisecond))         # GMT correction. GMT+2
    weekday = RTC().datetime()[3]
    if (tprint == 1):
        print ("NTP Sync - {:02d}/{:02d}/{}  {:02d}:{:02d}:{:02d}".format(RTC().datetime()[2],RTC().datetime()[1],RTC().datetime()[0],RTC().datetime()[4],RTC().datetime()[5],RTC().datetime()[6]))
    
    if value == 0: #all date/time
        return("{:02d}/{:02d}/{}  {:02d}:{:02d}:{:02d}".format(RTC().datetime()[2],RTC().datetime()[1],RTC().datetime()[0],RTC().datetime()[4],RTC().datetime()[5],RTC().datetime()[6]))
    elif value == 1: #time
        return("{:02d}:{:02d}:{:02d}".format(RTC().datetime()[4],RTC().datetime()[5],RTC().datetime()[6]))
    elif value == 2: #date
        return("{:02d}/{:02d}/{}".format(RTC().datetime()[2],RTC().datetime()[1],RTC().datetime()[0]))
   
#PINS
def spin():
    state = p2.value()
    p2.value(not state)

def test(timer):
    state = p2.value()
    p2.value(not state)

def write_outputs():
    if (state_omap != last_state_omap):
        for i in range(0,len(omap)):
            if (state_omap[i] != last_state_omap[i]):
                last_state_omap[i] = state_omap[i]
                omap[i].value(state_omap[i])
                
                print('output %d : %d' % (i, state_omap[i]))
                pub((b'/digital-outputs/%d' % i), str(state_omap[i]), True)

def read_inputs(first):
    for i in range(0,len(imap)):
        state_imap[i] = imap[i].value()
        if (state_imap[i] != last_state_imap[i]):
            last_state_imap[i] = state_imap[i]
            if (not first):
                print('input %d : %d' % (i, state_imap[i]))
                pub((b'/digital-inputs/%d' % i), str(state_imap[i]), False)

#MQTT
    
def mqtt_incoming(topic, msg):
    global sch0
    
    try:
        tmp = ujson.loads(msg)
        print("json message incoming: %s" % tmp)
    except:
        print("simple message incoming: %s" % msg)
        return
    
    if (topic == main_topic + b'/scheduler/0/set'):
        if (("weekdays" in tmp) and (len(tmp["weekdays"]) == 7)):
            f=open("scheduler/sch0.json","w") # opens a file for writing.
            f.write(ujson.dumps(tmp))
            f.close()
            sch0 = tmp
            print('Save json weekdays')
            for day in range(0, 7): 
                print('\t[Day %d] -> %s' % (day,(sch0["weekdays"][day])))
            #pub(b'/scheduler/0', ujson.dumps(tmp), True)
    elif (topic == main_topic + b'/scheduler/0/get'):
        if (("weekdays" in tmp) and (len(tmp["weekdays"]) == 7)):
            print('Check weekdays json')
            pub(b'/scheduler/0/sync', str(sch0 == tmp), True)
    elif (topic == main_topic + b'/digital-outputs/set'):    
        for i in range(0, 6):
            output = ("dout%s" % str(i))
            if (output in tmp):
                state = tmp[output]
                state_omap[i] = int(state)
                pub((b'/digital-outputs/%d' % i), str(state_omap[i]), False)
        
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

def pub_sys():
    global f_pub_sys
    if (time.time() - f_pub_sys) > 300:
        sys = {}
        sys["freeMem"] = gc.mem_free()
        sys["uptime"] = time.time()
        sys["temp"] =  "{:.1f}".format((esp32.raw_temperature() - 32) * 5/9)
        sys["rssi"] = station.status('rssi')

        pub(b'/sys', ujson.dumps(sys), True)
        f_pub_sys = time.time()

def pub_info():
    info = {}
    info["board"] = sys.platform.upper()
    info["version"] = "0.1"
    info["upython_versio"] = sys.version
    info["ip"] = station.ifconfig()[0]

    pub(b'/info', ujson.dumps(info), True)

def mqtt_subs():
    mqtt.subscribe(main_topic + b'/digital-outputs/set')
    for i in range(0, len(omap)):
        mqtt.subscribe(main_topic + (b'/scheduler/%d/set') % i)
        mqtt.subscribe(main_topic + (b'/scheduler/%d/get') % i)
        
def restart_and_reconnect():
    print('Failed to connect to MQTT broker. Reconnecting...')
    time.sleep(5)
    machine.reset()         

def pub(addtopic, payload, retain):
    global mqtt
    topic = main_topic + addtopic
    mqtt.publish(topic, payload, retain)
    
def pub_outputs(retain):
    for i in range(0,6):
        pub((b'/digital-outputs/%d' % i), str(state_omap[i]), retain)

def pub_inputs(retain):
    for i in range(0,6):
        pub((b'/digital-inputs/%d' % i), str(state_imap[i]), retain)  

#HomeAssistant
def switch_discovery(num):
    
    main_topic_str = str(main_topic)[2:-1]
    
    sensor = {}
    sensor["avty_t"] = main_topic_str + "/status"
    sensor["stat_t"] = main_topic_str + "/digital-outputs/" + num
    sensor["name"] = "WH1TEPY-" + client_id + "_DO" + num
    sensor["uniq_id"] = sensor["name"]    
    sensor["pl_on"] = '{"dout' + num + '":1}'
    sensor["pl_off"] =  '{"dout' + num + '":0}'
    sensor["ret"] = True
    sensor["stat_off"] = "0"   
    sensor["stat_on"] = "1" 
    sensor["pl_avail"] = "1"
    sensor["pl_not_avail"] = "0"
    sensor["cmd_t"] = main_topic_str + "/digital-outputs/set"
    
    device = {}
    device["name"] = "WH1TEPY-" + client_id
    device["mf"] = "IoT Wired Link"
    device["sw"] = "0.1"
    device["mdl"] = sys.platform.upper()
    device["ids"] = "[ WH1TEPY-" + client_id + " ]"
    
    sensor["dev"] = device
    
    topic = discovery_topic + b'/switch/WH1TEPY-' + client_id + b'_' + num + b'/config'
    encoded = ujson.dumps(sensor)
    mqtt.publish(topic, encoded, True)
    
def bsensor_discovery(num):
    
    main_topic_str = str(main_topic)[2:-1]
    
    sensor = {}
    sensor["avty_t"] = main_topic_str + "/status"
    sensor["stat_t"] = main_topic_str + "/digital-inputs/" + num
    sensor["name"] = "WH1TEPY-" + client_id + "_DI" + num
    sensor["uniq_id"] = sensor["name"]    
    sensor["pl_on"] = "1"
    sensor["pl_off"] = "0"

    sensor["pl_avail"] = "1"
    sensor["pl_not_avail"] = "0"
    
    device = {}
    device["name"] = "WH1TEPY-" + client_id
    device["mf"] = "IoT Wired Link"
    device["sw"] = "0.1"
    device["mdl"] = sys.platform.upper()
    device["ids"] = "[ WH1TEPY-" + client_id + " ]"
    
    sensor["dev"] = device
    
    topic = discovery_topic + b'/binary_sensor/WH1TEPY-' + client_id + b'_' + num + b'/config'
    encoded = ujson.dumps(sensor)
    mqtt.publish(topic, encoded, True)  

def sensor_discovery(num):
    
    main_topic_str = str(main_topic)[2:-1]
    
    sensor = {}
    sensor["avty_t"] = main_topic_str + "/status"
    sensor["state_topic"] = main_topic_str + "/scheduler/" + num
    sensor["name"] = "WH1TEPY-" + client_id + "_SCH" + num
    sensor["uniq_id"] = sensor["name"]    

    sensor["pl_avail"] = "1"
    sensor["pl_not_avail"] = "0"
    
    device = {}
    device["name"] = "WH1TEPY-" + client_id
    device["mf"] = "IoT Wired Link"
    device["sw"] = "0.1"
    device["mdl"] = sys.platform.upper()
    device["ids"] = "[WH1TEPY-" + client_id + " ]"
    
    sensor["dev"] = device
    
    topic = discovery_topic + b'/sensor/WH1TEPY-' + client_id + b'_SCH' + num + b'/config'
    encoded = ujson.dumps(sensor)
    mqtt.publish(topic, encoded, True)  

def cover_discovery(up, down):
    
    main_topic_str = str(main_topic)[2:-1]

    sensor = {}
    sensor["avty_t"] = main_topic_str + "/status"
    sensor["name"] = "WH1TEPY-" + client_id + "_C" + up + "-" + down
    sensor["uniq_id"] = sensor["name"]    
    sensor["pl_open"] = '{"dout' + down + '":0, "dout' + up + '":1}'
    sensor["pl_cls"] =  '{"dout' + up + '":0, "dout' + down + '":1}'
    sensor["pl_stop"] = '{"dout' + up + '":0, "dout' + down + '":0}'  
    sensor["pl_avail"] = "1"
    sensor["pl_not_avail"] = "0"
    sensor["cmd_t"] = main_topic_str + "/digital-outputs/set"
    
    device = {}
    device["name"] = "WH1TEPY-" + client_id
    device["mf"] = "IoT Wired Link"
    device["sw"] = "0.1"
    device["mdl"] = sys.platform.upper()
    device["ids"] = "[ WH1TEPY-" + client_id + " ]"
    
    sensor["dev"] = device
    
    topic = discovery_topic + b'/cover/WH1TEPY-' + client_id + b'_C' + up + "-" + down + b'/config'
    encoded = ujson.dumps(sensor)
    mqtt.publish(topic, encoded, True)

def pub_switchs():
    for i in range(0, 1):
        switch_discovery(str(i))
        
def pub_bsensor():
    for i in range(0, len(imap)):
        bsensor_discovery(str(i))        
        
#SCHEDULER        
def load_sch():
    for i in range(0, len(omap)):
        sch = "sch" + str(i)
        if (sch + ".json" in os.listdir("scheduler/")):
            path = "scheduler/" + sch + ".json"
            f=open(path,"r")
            sch = ujson.loads(f.read())
            f.close()
            print('load sch%d'% i)
            pub((b'/scheduler/%d/storage' % i), "INIT", True)
        else:
            print('not exist ',sch)
            pub((b'/scheduler/%d/storage' % i), "NOT_INIT", True)

def sync_sch():
    time = ("{:02d}:{:02d}:{:02d}".format(RTC().datetime()[4],RTC().datetime()[5],RTC().datetime()[6]))
    wday = int(RTC().datetime()[3])
    
    global sch0
    
    if (("weekdays" in sch0) and (len(sch0["weekdays"]) == 7)):
        #print('[Day %d] v2 -> %s' % (wday, len(sch0["weekdays"][wday])))
        for j in range(0, len(sch0["weekdays"][wday])):
            if (("when" in sch0["weekdays"][wday][j]) and ("what" in sch0["weekdays"][wday][j]) and (sch0["weekdays"][wday][j]["when"] >= time)):
                #print('\t [Time: %s] -> %d' % (sch["weekdays"][wday][j]["when"], sch["weekdays"][wday][j]["what"])) 
                if ((sch0["weekdays"][wday][j]["when"] == time) and (state_omap[0] != int(sch0["weekdays"][wday][j]["what"]) )):
                    state_omap[0] = int(sch0["weekdays"][wday][j]["what"])
                    
################################ START #########################################
ntp(1,0)

try:
    mqtt = mqtt_connect()
except OSError as e:
    restart_and_reconnect()

load_sch()
read_inputs(True)
pub_switchs()
pub_bsensor()
cover_discovery("2","3")
cover_discovery("4","5")
pub_inputs(False)
pub_outputs(False)

while 1:
    pub_sys()
    read_inputs(False)
    sync_sch()
    try:
        mqtt.check_msg()
        if (time.time() - last_message) > message_interval:
            #print("{:02d}:{:02d}:{:02d}".format(RTC().datetime()[4],RTC().datetime()[5],RTC().datetime()[6]))
            msg = b'%.1f' % ((esp32.raw_temperature() - 32) * 5/9)
            mqtt.publish(main_topic + b'/temp', msg)
            last_message = time.time()
            counter += 1
        write_outputs()
    except OSError as e:
        restart_and_reconnect()

