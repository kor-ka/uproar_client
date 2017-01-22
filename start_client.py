#!/usr/bin/env python
import MqttActor, time

mqtt_ref = MqttActor.MqttActor.start()
mqtt_ref.tell({'command': 'init'})

# do not exit
while True:
    time.sleep(100)
