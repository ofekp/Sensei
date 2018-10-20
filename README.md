# Sensei

Set Risco home security on/off by protocol with no involvement of Risco app.

To install, simply clone this repo and add the follwing line to `/etc/rc.local` just before the `exit 0` line:

`sudo su - pi -c "cd /home/pi/ofek/Sensei/; sudo python2.7 simple_server.py > /home/pi/ofek/Sensei/output 2>&1 &"`
