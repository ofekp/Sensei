#!/usr/bin/python2.7

import os
import time
import urllib2
import json
# sudo pip install python-gcm
#from gcm import *
#gcm = GCM(app_key);
#data = {'the_message': 'Sensor was triggered', 'sensor_id': 'door'}
#reg_id = 'f5dK1q7RYcQ:APA91bEhYHD-eGLfRbsDuEpj93HFgeEYklSWIICahBCpl6-G89w77hjm3mefuPB2auwsoaaIbPA0ai6cDS7GUQz6AKQG19dkSY99X4AM9kZxjKHKy0mWv6g7oHMcvn6OxgeUutFvJ35q'
#gcm.plaintext_request(registration_id=reg_id, data=data)


url = "https://android.googleapis.com/gcm/send"
app_key = "AIzaSyD5uehR9NXaiuGKIEmbJWkMUY3Y23d0XNE"

json_data = {"data": {"message": "hello!"}, "to": "/topics/global"}

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
