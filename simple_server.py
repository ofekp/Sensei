#!/usr/bin/python2.7
# usage: "sudo python2.7 simple_server.py"

import time
import json
import httplib2
import requests
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
from bluetoothctl import Bluetoothctl

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
debug = True
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
upnp_update_interval_sec = 600.0
ddns_update_interval_sec = 600.0
certificate_renewal_interval = 259200  # 3 days
# mplayer
mplayer_control_file = "/tmp/mplayercontrol"
# stream
radio_stations_file = "radiostations.json"
# devices
devices_file = "devices.json"
# BT
bt_speaker_name = "Bose Revolve SoundLink"


if ddns_hostname == "":
    print("You clearly have not set the configuration file [" + config_file_name + "]")
    exit(1)

# make a temp file from which mplayer can receive commands
os.system("if [ -e " + mplayer_control_file + " ]; then rm " + mplayer_control_file + "; fi")
#os.system("su - pi \"mkfifo " + mplayer_control_file + "\"")
os.system("mkfifo " + mplayer_control_file)
os.system("chmod 777 " + mplayer_control_file)

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
    debug_print("Risco server resp: " + str(content))
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


def close_process(process_name):
    try:
        pids_str = check_output(['pgrep', '-f', process_name])
        pids = pids_str.strip().split('\n')
        for pid in pids:
            os.system("sudo kill -9 " + pid)
        return True
    except Exception as e:
        return False


def check_process_running(process_name):
    try:
        pids_str = check_output(['pgrep', '-f', process_name])
        pids = pids_str.strip().split('\n')
        return len(pids) > 0
    except Exception as e:
        return False


def handle_pi_command(pi_command, pi_command_params):
    if "disarm risco" in pi_command:
        command_name = "disarm risco"
        riscoArmThread = Thread(target=riscoAction, args=[RiscoAction.DISARMED])
        riscoArmThread.start()
    elif "arm all risco" in pi_command:
        command_name = "arm risco"
        riscoArmThread = Thread(target=riscoAction, args=[RiscoAction.ARMED])
        riscoArmThread.start()
    elif "arm risco" in pi_command:
        command_name = "arm risco partially"
        riscoArmThread = Thread(target=riscoAction, args=[RiscoAction.PARTIALLY_ARMED])
        riscoArmThread.start()
    print "Executing command [" + command_name + "]"
    return command_name


@app.route('/webhook', methods=['POST'])
def process_command():
    debug_print("request: " + request.data)
    data_obj = json.loads(request.data)
    debug_print(json.dumps(data_obj, indent=4))
    user_action = data_obj['action']
    user_action = user_action.lower()
    user_action = user_action.replace("the", "").replace("  ", " ")
    try:
        user_action_params = json.loads(data_obj['params'])
    except:
        user_action_params = [{}]
    debug_print("user_action [" + user_action + "]")
    debug_print("user_action " + str(user_action_params))
    
    # combo commands
    if "combo" in user_action:
        if "sleep" in user_action:
            pi_commands = ["arm risco", "Boss alarm to 6:00"]
            pi_commands_params[1]['date-time'] = "6:00"  # setting parameter for the second command
        else:
            return "I do not recognize the combo command: " + pi_commands
    else:
        pi_commands = [user_action]
        pi_commands_params = [user_action_params]

    debug_print("pi_commands " + str(pi_commands))
    
    response = ""
    for idx, pi_command in enumerate(pi_commands):
        response += handle_pi_command(pi_command, pi_commands_params[idx]) + ". "
    return response


def start_webserver():
    global app
    #context = (cert_file, key_file)
    #app.run(host='0.0.0.0', port=port, debug=debug, ssl_context=context)
    app.run(host='0.0.0.0', port=port, debug=debug)


def ddns_update():
    h = httplib2.Http()
    resp, external_ip = h.request("http://ipecho.net/plain")
    #resp, external_ip = h.request("http://myexternalip.com/raw");  # IPv6
    print("My IP address is [" + external_ip.strip() + "]")
    #h.add_credentials(ddns_username, ddns_password)
    update_dynu_ddns_url = "https://api.dynu.com/nic/update?hostname=" + ddns_hostname + "&username=" + ddns_username + "&myip=" + external_ip.strip() + "&password=" + ddns_password
    #update_noip_dns_url = "http://dynupdate.no-ip.com/nic/update?hostname=" + ddns_hostname + "&myip=" + external_ip.strip() + ""
    print("Update DYNU url [" + update_dynu_ddns_url + "]")
    resp = requests.get(update_dynu_ddns_url)
    print("DDNS response [" + resp.content + "]")
    ddns_timer = Timer(ddns_update_interval_sec, ddns_update)
    ddns_timer.setDaemon(True)
    ddns_timer.start()


def upnp_update():
    # first let's find the gateway router
    adjusted_update_interval = upnp_update_interval_sec
    gateway_split = check_output(["ip", "route"]).split(" ")
    if len(gateway_split) >= 2:
        gateway = gateway_split[2]
        upnpc_cmd = "upnpc -e 'Sensei' -r " + str(port) + " TCP -G " + str(gateway)
        debug_print("upnp command [" + upnpc_cmd + "]")
        os.system(upnpc_cmd)
    else:
        adjusted_update_interval = upnp_update_interval_sec / 10
    upnp_timer = Timer(adjusted_update_interval, upnp_update)
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
    # start pulseaudio and then connect to bluetooth speaker
    os.system("su - pi \"pulseaudio -D\"")
    bt = Bluetoothctl()
    bt.start_scan()
    if bt.is_connected():
        print("BT is already connected")
    else:
        devices = bt.get_connectable_devices()
        devMap = {}
        devList = []
        for dev in devices:
            devMap[dev['name']] = dev['mac_address'];
            devList.append(dev['name'])
        if bt_speaker_name in devList:
            bt_mac = devMap[bt_speaker_name]
            logging.debug('trying to connect to [' + bt_device_name + ']')
            bt.start_agent()
            bt.default_agent()
            bt.trust(bt_mac)
            bt.pair(bt_mac)
            result = bt.connect(bt_mac)
            logging.debug("Connection result [" + str(result) + "]")
            if result:
                print('successful connection to [' + bt_device_name + ']')
            else:
                print("Could not connect to BR speaker [" + bt_speaker_name + "]")
                exit(1) 
        else:
            print("could not find BT speaker [" + bt_speaker_name + "]")
            exit(1)
          
    upnp_update()
    ddns_update()
    #certificate_renewal()
    debug_print("Strting flask server")
    #webserver_thread = Thread(target=start_webserver)
    #webserver_thread.start()
    start_webserver()



