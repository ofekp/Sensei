#!/bin/python

# sudo apt-get install python-espeak
# sudo pip pyttsx

import os
import sys
import time
from subprocess import Popen, PIPE, check_output
import threading
import pyttsx


def speakCurrentTime():
    global stream_play_pipe
    
    engine = pyttsx.init()
    engine.setProperty('rate', 150)  # by default the rate is 200

    time.sleep(2)
    for i in range(20):
        stream_play_pipe.stdin.write('/')
        time.sleep(0.02)
    engine.say('The current time is ')
    engine.say(str(int(time.strftime("%H"))))
    minutes = int(time.strftime("%M"))
    if (minutes != 0):
        engine.say('and')
        engine.say(str(int(minutes)))
        engine.say('minutes')
    engine.runAndWait()
    time.sleep(2)    

    for i in range(20):
        stream_play_pipe.stdin.write('*')
        time.sleep(0.02)
    # schedual for next time read
    threading.Timer(30, speakCurrentTime).start()


chour = int(sys.argv[1])
cminute = int(sys.argv[2])
print("current time [" + str(int(time.strftime("%H"))) + ":" + str(int(time.strftime("%M"))) + "] ctime [" + str(chour) + ":" + str(cminute) + "]")

while int(time.strftime("%H")) < chour:
    time.sleep(60)  # sleep 60 seconds

while int(time.strftime("%M")) < cminute:
    time.sleep(30)  # sleep 30 seconds

# start alarm
#os.system("omxplayer -o local 'http://broadcast.infomaniak.net/onefm-high.mp3'")
#os.system("mplayer -ao pulse 'http://broadcast.infomaniak.net/onefm-high.mp3'")
stream_url = "http://broadcast.infomaniak.net/onefm-high.mp3"
stream_play_pipe = Popen(['mplayer', '-quiet', '-ao', 'pulse', '{0}'.format(stream_url)], stdin=PIPE, stdout=PIPE)
time.sleep(10)
speakCurrentTime()

