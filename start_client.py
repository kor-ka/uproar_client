#!/usr/bin/env python
import MqttActor, TrackQueueActor

mqtt_ref = MqttActor.MqttActor.start()
mqtt_ref.tell({'command': 'init'})
