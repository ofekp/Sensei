#!/usr/bin/python2.7

from flask import Flask, render_template, request, Response, make_response
import time
from threading import Thread
import os


# Configuration
port = 80
debug = False


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


def start_webserver():
    global app
    app.run(host='0.0.0.0', port=port, debug=debug)


def upnp_update():
    upnpc_cmd = "upnpc -e 'Sensei' -r " + str(port) + " TCP"
    debug_print("upnp command [" + upnpc_cmd + "]")
    os.system(upnpc_cmd)


if __name__ == "__main__":
    upnp_update()
    time.sleep(20.0)
    start_webserver_thread = Thread(target=start_webserver)
    start_webserver_thread.setDaemon(True)
    start_webserver_thread.start()
    time.sleep(20)
    os.system("sudo ./certbot-auto renew --dry-run")

