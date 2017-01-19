import MqttActor, TrackQueueActor

mqtt_ref = MqttActor.MqttActor.start(track_queue)
mqtt_ref.tell({'command': 'init'})
