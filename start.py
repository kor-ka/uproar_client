import MqttActor, TrackQueueActor, pyglet

sound = pyglet.media.load('1.mp3', streaming=False)
sound.play()
pyglet.app.run()

track_queue = TrackQueueActor.TrackQueueActor.start()

mqtt_ref = MqttActor.MqttActor.start(track_queue)
mqtt_ref.tell({'command': 'init'})
