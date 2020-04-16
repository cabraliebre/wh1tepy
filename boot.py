import time                                   #https://docs.micropython.org/en/v1.5/pyboard/library/time.html
import utime
from time import localtime
import sys                                    #https://docs.micropython.org/en/v1.5/pyboard/library/sys.html
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
#import ujson
import os

client_id = str(ubinascii.hexlify(machine.unique_id()))[-7:-1].upper()
(year, month, mday, weekday, hour, minute, second, milisecond) = 0,0,0,0,0,0,0,0

omap = ["dout0","dout1","dout2","dout3","dout4","dout5"]
omap_pin = [4,5,18,19,21,22]
state_omap = [0,0,0,0,0,0]
last_state_omap = [0,0,0,0,0,0]

imap = ["din0","din1","din2","din3","din4","din5"]
imap_pin = [13,12,14,27,26,25]
state_imap = [0,0,0,0,0,0]
last_state_imap = [0,0,0,0,0,0]

#Setup
def info():
    print('Startup boot.py\nPython version ' + sys.version + ' in board ' + sys.platform.upper())
    print('ID Board: %s' % client_id)
    print('uC Temp: %.1f ºC - HALL sensor: %s' % ((esp32.raw_temperature() - 32) * 5/9 , esp32.hall_sensor()))

#WiFi
def connect_wifi():
    global station
    
    start = time.ticks_ms()
    ssid = 'dev'
    password = 'hasshass'
    print('Connecting WiFi to SSID %s' % ssid)    
    station = network.WLAN(network.STA_IF)

    station.active(True)
    station.connect(ssid, password)

    while station.isconnected() == False:
      pass

    pwm2 = PWM(Pin(2), freq=4, duty=10)
    delta = time.ticks_diff(time.ticks_ms(), start) # compute time difference
    print('Connection successful. Your IP is %s (%dms)' % (station.ifconfig()[0], delta))  

#NTP
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

#GPIO
def setup_gpio():
    for i in range(0,6):
        omap[i] = Pin(omap_pin[i], Pin.OUT)
        
        imap[i] = Pin(imap_pin[i], Pin.IN, Pin.PULL_UP)  
        state_imap[i] = imap[i].value()
        last_state_imap = state_imap
        
    print('Inputs state: %s' % str(state_imap))


start = time.ticks_ms() # get millisecond counter

pwm = PWM(Pin(2), freq=2, duty=5)
time.sleep(1)

info()
setup_gpio()
connect_wifi()

delta = time.ticks_diff(time.ticks_ms(), start) # compute time difference
print('End setup.py (%dms)' % delta)

#timer = machine.Timer(0)
#timer.init(period=30, mode=machine.Timer.PERIODIC, callback=test)
#timer.deinit()
