#!/usr/bin/python2.7
# usage: "sudo python2.7 server.py"

# dependencies:
# sudo pip install enum


import time
import json
import httplib2
import urllib2
from threading import Thread, Timer
from flask import Flask, render_template, request, Response, make_response
import pyttsx
from OpenSSL import SSL
import os
import base64
from enum import Enum
import ConfigParser
from subprocess import Popen, PIPE, check_output
import pwd


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

# system
pi_username = "pi"
pi_uid = 1000
pi_gid = 1000
# BT Speaker
speak_volume = 0.8
# Flask
debug = False
port = 28080
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
# update_interval
upnp_update_interval = 3600.0
ddns_update_interval = 4000.0
certificate_renewal_interval = 259200  # 3 days
# mplayer
mplayer_control_file = "/tmp/mplayercontrol"

if ddns_hostname == "":
    print("You clearly have not set the configuration file [" + config_file_name + "]")
    exit(1)

# make a temp file from which mplayer can receive commands
os.system("su - pi \"mkfifo " + mplayer_control_file + "\"")

app = Flask(__name__)

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
    h = httplib2.Http()
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
    h = httplib2.Http()
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
    h = httplib2.Http()
    headers = riscoLogin()
    headers['Referer'] = 'https://www.riscocloud.com/'
    headers['Content-Type'] = 'application/x-www-form-urlencoded'
    headers['Accept'] = '*/*'
    headers['Content-Length'] = '0'
    debug_print("request risco headers " + str(headers))
    resp, content = h.request("https://www.riscocloud.com/ELAS/WebUI/Security/GetCPState?code=" + risco_code, 'POST', headers=headers)
    debug_print("risco status resp: " + str(content))
    #sendNotification()


@app.route('/webhook', methods=['GET', 'POST'])
def process_command():
    global alarm_process
    global env

    debug_print("request: " + request.data)
    data_obj = json.loads(request.data)
    debug_print(json.dumps(data_obj, indent=4))
    try:
        user_command = data_obj['originalRequest']['data']['inputs'][0]['rawInputs'][0]['query']
    except:
        user_command = data_obj['result']['resolvedQuery']
    user_command = user_command.lower()
    user_command = user_command.replace("the", "").replace("  ", " ")
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
    elif "set alarm" in user_command or "set an alarm" in user_command:
        # currently only supporting "07:30:00" format (7:30 am)
        command_name = "set alarm"
        date_time = data_obj['result']['parameters']['date-time']
        mhs = date_time.split(":")
        os.system("su - pi -c \"python2.7 /home/pi/ofek/Sensei/alarmclock.py " + mhs[0] + " " + mhs[1] + " &\"")
    elif "cancel alarm" in user_command or "stop alarm" in user_command:
        command_name = "cancel alarm"
        pids_str = check_output(['pgrep', '-f', 'alarmclock.py'])
        pids = pids_str.strip().split('\n')
        for pid in pids:
            os.system("sudo kill -9 " + pid)
    elif "snooze" in user_command:
        command_name = "snooze"
        date_time = data_obj['result']['parameters']['date-time']
        print(date_time)
    elif "stop streaming" in user_command or "stop stream" in user_command:
        command_name = "stop streaming"
        pids_str = check_output(['pgrep', '-f', 'mplayer'])
        pids = pids_str.strip().split('\n')
        for pid in pids:
            os.system("sudo kill -9 " + pid)
    elif "stream" in user_command:
        command_name = "stream"
        # load radio stations map
        found_station = False
        with open('radiostations.json', 'r') as rsf:
            rso = json.load(rsf)
            for rs in rso:
                if rs in user_command:
                    user_command += " " + rs + " station"
                    found_station = True
                    os.system("su - pi -c \"mplayer -ao pulse -slave -input file=" + mplayer_control_file + " '" + rso[rs] + "' &\"")
                    break
        if not found_station:
            return get_response("I am not familiarized with the requested radio station")
    elif "set volume" in user_command:
        percentage = data_obj['result']['parameters']['number']
        os.system("echo \"volume " + percentage + " 1\" > " + mplayer_control_file)     
    elif "home sensei" in user_command:
        return get_response("Home Sensei here")
    else:
        return get_response("I do not recognize the command: " + user_command)
    return get_response("Command " + command_name + " is being processed")


def start_webserver():
    global app
    context = (cert_file, key_file)
    app.run(host='0.0.0.0', port=port, debug=debug, ssl_context=context)


def ddns_update():
    h = httplib2.Http()
    resp, external_ip = h.request("http://ipecho.net/plain")
    h.add_credentials(ddns_username, ddns_password)
    update_noip_dns_url = "http://dynupdate.no-ip.com/nic/update?hostname=" + ddns_hostname + "&myip=" + external_ip
    debug_print("Update no-ip url [" + update_noip_dns_url + "]")
    resp, content = h.request(update_noip_dns_url)
    debug_print(resp)
    debug_print(content)
    ddns_timer = Timer(ddns_update_interval, ddns_update)
    ddns_timer.setDaemon(True)
    ddns_timer.start()


def upnp_update():
    upnpc_cmd = "upnpc -e 'Sensei' -r " + str(port) + " TCP"
    debug_print("upnp command [" + upnpc_cmd + "]")
    os.system(upnpc_cmd) 
    upnp_timer = Timer(upnp_update_interval, upnp_update)
    upnp_timer.setDaemon(True)
    upnp_timer.start()


def certificate_renewal():
    # get next renewal time from config file
    # if the renewal time has come, renew the certificate
    os.system("sudo python2.7 certificate_renewal.py")
    certificate_renewal_timer = Timer(certificate_renewal_interval, certificate_renewal)
    certificate_renewal_timer.setDaemon(True)
    certificate_renewal_timer.start()


if __name__ == "__main__":
    upnp_update()
    ddns_update()
    #certificate_renewal()
    debug_print("Strting flask server")
    #webserver_thread = Thread(target=start_webserver)
    #webserver_thread.start()
    start_webserver()

