#!/usr/bin/python2.7
# usage: "sudo python2.7 server.py"

# dependencies:
# sudo pip install enum


import time
import json
import httplib2
import urllib2
from threading import Thread
from flask import Flask, render_template, request, Response, make_response
import pyttsx
from OpenSSL import SSL
import os
import base64
from enum import Enum
import ConfigParser


# config parser
config_file_name = "home_sensei.cfg"
config = ConfigParser.RawConfigParser()


if not os.path.isfile(config_file_name) or os.stat(config_file_name).st_size == 0 or config.read(config_file_name) == []:
    debug_print("Writing empty config file")
    config.add_section('ddns')
    config.set('ddns', 'hostname', '')
    config.set('ddns', 'username', '')
    config.set('ddns', 'password', '')
    config.add_section('risco')
    config.set('risco', 'username', 'a@b.c')
    config.set('risco', 'password', '123456')
    config.set('risco', 'code', '1234')
    config.add_section('ssl')
    config.set('ssl', 'key_file', '<path to private key pem file>')
    config.set('ssl', 'cert_file', '<path to fullchain certificate pem file>')
    save_global_config(config)
    print("Please fill configuration file [" + config_file_name + "]")
    exit(1)


# BT Speaker
speak_volume = 0.8
# Flask
debug = False
port = 80
key_file = config.get('ssl', 'key_file')
cert_file = config.get('ssl', 'cert_file')
# DDNS
ddns_hostname = config.get('ddns', 'hostname')
ddns_username = config.get('ddns', 'username')
ddns_password = config.get('ddns', 'password')
# Risco
risco_username = config.get('risco', 'username')
risco_password = config.get('risco', 'password')
risco_code = config.get('risco', 'code')


if ddns_hostname == "":
    print(str(config.read(config_file_name)))
    print("You clearly have not set the configuration file [" + config_file_name + "]")
    exit(1)


app = Flask(__name__)
context = (cert_file, key_file)


def debug_print(msg):
    if debug:
        print(msg)


def say_something(something):
    engine = pyttsx.init()
    engine.setProperty('rate', 150)  # by default the rate is 200
    engine.setProperty('volume', speak_volume)
    engine.say(something)
    engine.runAndWait()
    del engine


def save_global_config(config_obj):
    with open(config_file_name, 'wb') as config_file:
        config_obj.write(config_file)


# Send message to phone using GCM - for debug purposes
def sendNotification(message):
    url = "https://android.googleapis.com/gcm/send"
    app_key = "AIzaSyD5uehR9NXaiuGKIEmbJWkMUY3Y23d0XNE"

    json_data = {"data": {"message": message}, "to": "/topics/global"}

    headers = {'Content-Type': 'application/json', 'Authorization': 'key=' + app_key}
    data =  json.dumps(json_data)

    req = urllib2.Request(url, data, headers)
    f = urllib2.urlopen(req)
    response = json.loads(f.read())

    reply = {}
    if 'message_id' in response:
        reply['error'] = '0'
    elif 'error' in response:
        reply['error'] = '1'

    f.close()
    

def get_response(command):
    resp = Response(json.dumps({ "speech": command, "displayText": command, "source": "sensei-webhook" }, indent=4))
    resp.headers['Content-Type'] = 'application/json'
    return resp


def riscoLogin():
    h = httplib2.Http(".cache")
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    headers['Content-Length'] = '0'
    login_url = "https://www.riscocloud.com/ELAS/WebUI/?username=" + risco_username + "&password=" + risco_password + "&code=" + risco_code + "&langId=en"
    if debug:
        debug_print("login_url " + login_url)
    resp, content = h.request(login_url, 'POST', headers=headers)
    debug_print("login resp: " + str(resp))
    # return headers with the set cookie
    RUCCookie = 'username=' + base64.b64encode(risco_username) + '&langId=en&isForcedLangId=False'
    asp_session_id = resp['set-cookie'][resp['set-cookie'].find("ASP.NET_SessionId") + 18 : resp['set-cookie'].find(';')]
    debug_print("RUCCookie [" + RUCCookie + "] ASP Session ID [" + asp_session_id + "]")
    return {'Cookie': 'RUCCookie=' + RUCCookie + '; ASP.NET_SessionId=' + asp_session_id}


class RiscoAction(Enum):
    ARMED = 1
    PARTIALLY_ARMED = 2
    DISARMED = 3


def riscoAction(riscoAction):
    headers = riscoLogin()
    headers['Referer'] = 'https://www.riscocloud.com/'
    headers['Content-Type'] = 'text/html'
    headers['Accept'] = '*/*'
    headers['Content-Length'] = '0'
    debug_print("request risco headers " + str(headers))
    debug_print("RiscoAction enum [" + str(riscoAction) + "]")
    if riscoAction == RiscoAction.ARMED:
        riscoAction = "armed"
    elif riscoAction == RiscoAction.PARTIALLY_ARMED:
        riscoAction = "partially"
    elif riscoAction == RiscoAction.DISARMED:
        riscoAction = "disarmed"
    else:
        return False
    debug_print("riscoAction [" + riscoAction + "]")
    resp, content = h.request("https://www.riscocloud.com/ELAS/WebUI/Security/ArmDisarm?type=0%3A" + riscoAction + "&passcode=" + risco_password + "&bypassZoneId=-1", 'POST', headers=headers)
    debug_print("disarm resp: " + str(content))
    if "ico-partial.png" in str(content):
        sendNotification("RISCO is set to [ARMED_PARTIALLY]") 
    elif "ico-armed.png" in str(content):
        sendNotification("RISCO is set to [ARMED]")
    elif "ico-disarmed.png" in str(content):
        sendNotification("RISCO is set to [DISARMED]")
    else:
        sendNotification("RISCO state could not be determined")
    return True
 

def notifyRiscoState():
    headers = riscoLogin()
    headers['Referer'] = 'https://www.riscocloud.com/'
    headers['Content-Type'] = 'application/x-www-form-urlencoded'
    headers['Accept'] = '*/*'
    headers['Content-Length'] = '0'
    debug_print("request risco headers " + str(headers))
    resp, content = h.request("https://www.riscocloud.com/ELAS/WebUI/Security/GetCPState?code=" + risco_code, 'POST', headers=headers)
    debug_print("risco status resp: " + str(content))
    #sendNotification()


# Must change port to 80 when using certbot
@app.route('/.well-known/acme-challenge/<path:path>', methods=['GET', 'POST'])
def certbot_answer(path):
    only_files = [f for f in os.listdir(".well-known/acme-challenge/") if os.path.isfile(os.path.join(".well-known/acme-challenge/", f))]
    debug_print(str(only_files))
    for file in only_files:
        with open(os.path.join(".well-known/acme-challenge/", file), 'r') as fin:
            debug_print(str(file))
            file_content = fin.read()
            debug_print(file_content)
            return Response(file_content)


@app.route('/webhook', methods=['GET', 'POST'])
def process_command():
    debug_print("request: " + request.data)
    data_obj = json.loads(request.data)
    debug_print(json.dumps(data_obj, indent=4))
    try:
        user_command = data_obj['originalRequest']['data']['inputs'][0]['rawInputs'][0]['query']
    except:
        user_command = data_obj['result']['resolvedQuery']
    user_command = user_command.lower()
    debug_print("user_command: " + user_command)
    command_name = ""
    if "arm risco partially" in user_command:
        command_name = "arm risco partially"
        riscoArmThread = Thread(target=riscoAction, args=[RiscoAction.PARTIALLY_ARMED])
        riscoArmThread.start()
    elif "disarm risco" in user_command:
        command_name = "disarm risco"
        riscoArmThread = Thread(target=riscoAction, args=[RiscoAction.DISARMED])
        riscoArmThread.start()
    elif "arm risco" in user_command:
        command_name = "arm risco"
        riscoArmThread = Thread(target=riscoAction, args=[RiscoAction.ARMED])
        riscoArmThread.start()
    elif "risco state" in user_command or "risco status" in user_command:
        command_name = "risco state"
        riscoArmThread = Thread(target=notifyRiscoState)
        riscoArmThread.start()
    elif "home sensei" in user_command:
        return get_response("Welcome to Home Sensei, how may I assist")
    else:
        return get_response("I do not recognize the command: " + user_command)
    return get_response("Command " + command_name + " is being processed")


def start_webserver():
    global context
    app.run(host='0.0.0.0', port=port, debug=debug, ssl_context=context)
    #app.run(host='0.0.0.0', port=port, debug=debug)

if __name__ == "__main__":
    h = httplib2.Http(".cache")
    resp, external_ip = h.request("http://ipecho.net/plain")
    h.add_credentials(ddns_username, ddns_password)
    update_noip_dns_url = "http://dynupdate.no-ip.com/nic/update?hostname=" + ddns_hostname + "&myip=" + external_ip
    debug_print("Update no-ip url [" + update_noip_dns_url + "]")
    resp, content = h.request(update_noip_dns_url)
    debug_print(resp)
    debug_print(content)
    debug_print("Strting flask server")
    upnpc_cmd = "upnpc -e 'Sensei' -r " + str(port) + " TCP"
    debug_print("upnp command [" + upnpc_cmd + "]")
    os.system(upnpc_cmd)
    #webserver_thread = Thread(target=start_webserver)
    #webserver_thread.start()
    start_webserver()

while True:
    time.sleep(10)
