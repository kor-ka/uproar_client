import MqttActor, TrackQueueActor

mqtt_ref = MqttActor.MqttActor.start()
mqtt_ref.tell({'command': 'init'})
