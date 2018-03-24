#!/usr/bin/python2.7

from flask import Flask, render_template, request, Response, make_response
import time
from threading import Thread
import os
import httplib2
import ConfigParser
import requests


# Configuration
port = 80
debug = True

# config parser
config_file_name = "home_sensei.cfg"
config = ConfigParser.RawConfigParser()
if not os.path.isfile(config_file_name) or os.stat(config_file_name).st_size == 0 or config.read(config_file_name) == []:
    print "Config file nt found. aborting."
    exit(1)
# DDNS
ddns_hostname = config.get('ddns', 'hostname')
ddns_username = config.get('ddns', 'username')
ddns_password = config.get('ddns', 'password')

app = Flask(__name__)


def debug_print(msg):
    if debug:
        print(msg)


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
    return Response("No File Exists")


# when creating a new certificate use this
# http://ofekp.dynu.net/.well-known/acme-challenge/_vEulN92p8eRLj-HBsgtUsiiLoxcBESRYRGpfup34nY
# Must change port to 80 when using certbot
#@app.route('/.well-known/acme-challenge/<challenge>', methods=['GET', 'POST'])
def certbot_answer(challenge):
    return Response(challenge)


def start_webserver():
    global app
    app.run(host='0.0.0.0', port=port, debug=debug, use_reloader=False)


def upnp_update():
    upnpc_cmd = "upnpc -e 'Sensei' -r " + str(port) + " TCP"
    debug_print("upnp command [" + upnpc_cmd + "]")
    os.system(upnpc_cmd)


def ddns_update():
    h = httplib2.Http()
    resp, external_ip = h.request("http://ipecho.net/plain")
    #resp, external_ip = h.request("http://myexternalip.com/raw");  # IPv6
    print("My IP address is [" + external_ip.strip() + "]")
    #h.add_credentials(ddns_username, ddns_password)
    update_dynu_ddns_url = "https://api.dynu.com/nic/update?hostname=" + ddns_hostname + "&username=" + ddns_username + "&myip=" + external_ip.strip() + "&password=" + ddns_password
    #update_noip_dns_url = "http://dynupdate.no-ip.com/nic/update?hostname=" + ddns_hostname + "&myip=" + external_ip.strip() + ""
    print("Update DYNU url [" + update_dynu_ddns_url + "]")
    #resp, content = h.request(update_dynu_ddns_url)
    resp = requests.get(update_dynu_ddns_url)
    print("DDNS response [" + resp.content + "]")


if __name__ == "__main__":
    ddns_update()
    upnp_update()
    time.sleep(5.0)
    start_webserver_thread = Thread(target=start_webserver)
    start_webserver_thread.setDaemon(True)
    start_webserver_thread.start()
    time.sleep(5.0)
    # when cheking the renewal process
    #os.system("sudo ./certbot-auto renew --dry-run")
    # when renewing use this
    #os.system("sudo ./certbot-auto renew")
    # when changing a dns, need a completely different certificate from scratch
    os.system("sudo ./certbot-auto certonly --webroot --preferred-challenges http -d ofekp.dynu.net")
    # webroot: /home/pi/ofek/Sensei/
    # make sure the folder /home/pi/ofek/Sensei/.well-known has 777 permissions recursively!
    # when done change the certificates paths in the sensei config file
    # make sure to disable ipv6 in the ddns service (was needed for dynu)
    raw_input("Press any key to exit")
