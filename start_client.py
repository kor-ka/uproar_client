#!/usr/bin/env python
import sys

import subprocess

import MqttActor, time

mqtt_ref = MqttActor.MqttActor.start()
mqtt_ref.tell({'command': 'init'})

# prevent mac from sleep
if 'darwin' in sys.platform:
    print('Running \'caffeinate\' on MacOSX to prevent the system from sleeping')
    subprocess.Popen('caffeinate')

# do not exit
while True:
    time.sleep(100)
