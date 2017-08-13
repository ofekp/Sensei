#!/bin/python

# sudo apt-get install python-espeak
# sudo pip pyttsx

import os
import sys
import time
from subprocess import Popen, PIPE, check_output
import thread
import pyttsx


user_cmd = ""
speak_volume = 1.0

def speakTime(engine, hour, minute):
    ampm = ""
    if hour == 0:
        hour = 12
        ampm = "am"
    elif hour > 12:
        hour = hour - 12
        ampm = "pm"
    else:
        ampm = "am"
    sayString = str(hour) + " " + ampm
    if (minute != 0):
        sayString += " and " + str(minute)
        if minute == 1:
            sayString += " minute"
        else:
            sayString += " minutes"
    engine.say(sayString)


def speakCurrentTime():
    global stream_play_pipe
    global user_cmd

    while True:
        try:
            engine = pyttsx.init()
            engine.setProperty('rate', 150)  # by default the rate is 200
            engine.setProperty('volume', speak_volume)
    
            time.sleep(2)
            for i in range(20):
                stream_play_pipe.stdin.write('/')
                time.sleep(0.02)
        
            engine.say('The current time is ')
            speakTime(engine, int(time.strftime("%H")), int(time.strftime("%M")))
            engine.runAndWait()
            time.sleep(2)    

            for i in range(25):
                stream_play_pipe.stdin.write('*')
                time.sleep(0.02)
    
            del engine

            # schedual for next time read
            for i in range(30):
                if user_cmd == "q":
                    quit()
                time.sleep(1)
        except Exception as e:
            print "pyttsx exception({0}) occurred: {1}".format(e.errno, e.strerror) 
        except:
            print "Unexpected error: ", sys.exc_info()[0]
            pass


def get_user_input():
    global user_cmd

    while user_cmd != "q":
        user_cmd = raw_input("Enter cmd: ")
        print("User cmd received: " + user_cmd)
    

chour = int(sys.argv[1])
cminute = int(sys.argv[2])
engine = pyttsx.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', speak_volume)
engine.say('Alarm set to ')
speakTime(engine, chour, cminute)
engine.runAndWait()
time.sleep(2)
del engine
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
time.sleep(5)
thread.start_new_thread(speakCurrentTime, ())
thread.start_new_thread(get_user_input, ())

while user_cmd != "q":
    time.sleep(2)

print("Good Morning!!!")
