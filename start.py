import MqttActor, TrackQueueActor

track_queue = TrackQueueActor.TrackQueueActor.start()

mqtt_ref = MqttActor.MqttActor.start(track_queue)
mqtt_ref.tell({'command': 'init'})
