#!/usr/bin/python2.7

import os
import sys
import time
import urllib2
import json
# sudo pip install python-gcm
#from gcm import *
#gcm = GCM(app_key);
#data = {'the_message': 'Sensor was triggered', 'sensor_id': 'door'}
#reg_id = 'f5dK1q7RYcQ:APA91bEhYHD-eGLfRbsDuEpj93HFgeEYklSWIICahBCpl6-G89w77hjm3mefuPB2auwsoaaIbPA0ai6cDS7GUQz6AKQG19dkSY99X4AM9kZxjKHKy0mWv6g7oHMcvn6OxgeUutFvJ35q'
#gcm.plaintext_request(registration_id=reg_id, data=data)

def sendNotification(message):
    url = "https://android.googleapis.com/gcm/send"
    app_key = "AIzaSyD5uehR9NXaiuGKIEmbJWkMUY3Y23d0XNE"

    json_data = {"data": {"message": message}, "to": "/topics/global"}

    headers = {'Content-Type': 'application/json', 'Authorization': 'key=' + app_key}
    data =  json.dumps(json_data)

    req = urllib2.Request(url, data, headers)
    f = urllib2.urlopen(req)
    response = json.loads(f.read())

    print("Rsponse: " + str(response))

    reply = {}
    if 'message_id' in response:
        reply['error'] = '0'
        print('Message sent!')
    elif 'error' in response:
        reply['error'] = '1'
        print('Counld not send the message')

    f.close()

import subprocess

def addUpnpRuleTCP(port):
    subprocess.Popen("upnpc -u http://192.168.1.1:1900/gatedesc.xml -a $(ifconfig wlan0 | grep 'inet addr' | cut -d : -f 2 | cut -d ' ' -f 1) " + str(port) + " " + str(port) + " TCP", shell=True, stdout=subprocess.PIPE)
    p = subprocess.Popen("upnpc -u http://192.168.1.1:1900/gatedesc.xml -l | grep " + str(port), shell=True, stdout=subprocess.PIPE)
    res_str = p.communicate()[0]
    res = False
    if str(port) in res_str:
        res = True
    return res
    
print("Initializing...")
# Start Motion
while not addUpnpRuleTCP(8080):
    time.sleep(5)
print("Done upnpc 8080 TCP")
time.sleep(5)
while not addUpnpRuleTCP(8081):
    time.sleep(5)
print("Done upnpc 8081 TCP")
subprocess.Popen("sudo motion", shell=True)
print("Started Motion")


# PIR
import RPi.GPIO as GPIO
import time

calibration_time_in_sec = 30
pause_time_in_sec = 5

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)

# First calibrate the sensor
GPIO.setup(11, GPIO.OUT)
GPIO.output(11, 0)
print("Calibrating the sensor...")
for i in range(0, calibration_time_in_sec):
    sys.stdout.write('.') # print without \n
    time.sleep(1)
print("Sensor calibrated.")
GPIO.setup(11, GPIO.IN)

# Main loop
lock_low = True
take_low_time = True
low_in = 0
while True:
    val = GPIO.input(11)
    if val == 1:
        if (lock_low):
            lock_low = False
            motion_start_msg = "Motion Detected! [" + str(int(time.time())) + "]" 
            print(motion_start_msg)
            sendNotification(motion_start_msg)
            time.sleep(0.05)
        take_low_time = True

    if val == 0:
        if take_low_time:
            low_in = int(time.time())
            take_low_time = False
        if not lock_low and (int(time.time()) - low_in) > pause_time_in_sec:
            lock_low = True
            print("Motion ended at [" + str(int(time.time())) + "]")
            time.sleep(0.05)

# To have UPnP capabilities use:
# http://miniupnp.tuxfamily.org/
# go to the download page
# download the latest miniupnp client
# make -j4
# sudo make install
# upnpc -a $(ifconfig wlan0 | grep "inet addr" | cut -d : -f 2 | cut -d " " -f 1) 8090 8090 TCP
# Better to directly send the request to the gateway router, first find the path using upnpc -l
# then pass the path of the required router in the next command using '-u'
# upnpc -u http://192.168.1.1:1900/gatedesc.xml -a $(ifconfig wlan0 | grep "inet addr" | cut -d : -f 2 | cut -d " " -f 1) 8080 8080 TCP
# upnpc -u http://192.168.1.1:1900/gatedesc.xml -a $(ifconfig wlan0 | grep "inet addr" | cut -d : -f 2 | cut -d " " -f 1) 8081 8081 TCP
# To remove a rule:
# upnpc -d 80 TCP

# install motion
# for more installation info refer to http://www.techrapid.co.uk/raspberry-pi/turn-raspberry-pi-nvr-motion/
# sudo apt-gte update
# sudo apt-get install motion
# copy the motion_backup.conf file from Sensei.git to /etc/motion/motion.conf
# sudo motion (will not work without sudo)



# ============================================
# Tried but not worked with IPCAM Android apps
# ********************************************

# HTTP Stream
# http://www.r3uk.com/index.php/38-tech-tips/software/100-webcam-capture-using-fswebcam
# fswebcam -c /home/pi/ofek/Sensei/fswebcam.conf

# MJPG-STREAMER
# To install refer to http://petrkout.com/electronics/low-latency-0-4-s-video-streaming-from-raspberry-pi-mjpeg-streamer-opencv/



