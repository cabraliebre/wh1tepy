import time                                   #https://docs.micropython.org/en/v1.5/pyboard/library/time.html
import utime
import sys                                    #https://docs.micropython.org/en/v1.5/pyboard/library/sys.html
import ubinascii
import machine                                #https://docs.micropython.org/en/latest/library/machine.html
from machine import Pin, RTC, Timer, PWM                              #NTP-time (from pool.ntp.org)
import micropython
import network
import esp                                    #https://docs.micropython.org/en/latest/library/esp.html
esp.osdebug(None)
import esp32                                  #https://docs.micropython.org/en/latest/library/esp32.html
import gc
gc.collect()
import os

client_id = str(ubinascii.hexlify(machine.unique_id()))[-7:-1].upper()

OMAP = ["dout0","dout1","dout2","dout3","dout4","dout5"]
OMAP_PIN = [4,5,18,19,21,22]
state_omap = [0,0,0,0,0,0]
last_state_omap = [0,0,0,0,0,0]

IMAP = ["din0","din1","din2","din3","din4","din5"]
IMAP_PIN = [13,12,14,27,26,25]
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

#GPIO
def setup_gpio():
    for i in range(0,6):
        OMAP[i] = Pin(OMAP_PIN[i], Pin.OUT)
        
        IMAP[i] = Pin(IMAP_PIN[i], Pin.IN, Pin.PULL_UP)  
        state_imap[i] = IMAP[i].value()
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
