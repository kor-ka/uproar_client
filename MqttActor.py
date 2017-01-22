import pykka, paho.mqtt.client as mqtt, os, urlparse, socket, json, time, config
from subprocess import call
import TrackQueueActor


class MqttActor(pykka.ThreadingActor):
    uid = config.uproar.get('token')
    track_queue = None
    client = None

    # The callback for when a PUBLISH message is received from the server.
    def on_message(self, client, userdata, msg):
        if msg.topic == ("track_" + self.uid):
            if self.track_queue is None or not self.track_queue.is_alive():
                self.track_queue = TrackQueueActor.TrackQueueActor.start(self.actor_ref)
            data = json.loads(str(msg.payload))
            self.track_queue.tell({'command': 'track', 'track': data})

        elif msg.topic == ('volume_' + self.uid):
            if str(msg.payload) == '1':
                call(["amixer", "-q", "sset", "\'Power Amplifier\'", "5%+"])
            elif str(msg.payload) == '0':
                call(["amixer", "-q", "sset", "\'Power Amplifier\'", "5%-"])

    # The callback for when the client receives a CONNACK response from the server.
    def on_connect(self, client, userdata, flags, rc):
        print("Connected with result code " + str(rc))
        if self.track_queue is None or not self.track_queue.is_alive():
            self.track_queue = TrackQueueActor.TrackQueueActor.start(self.actor_ref)
        self.track_queue.tell({'command': 'startup'})
        client.publish('server_test',
                       'hi there')  # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        client.subscribe("track_" + self.uid, 0)
        client.subscribe("volume_" + self.uid, 0)

    def initMqtt(self):
        print('init mqtt')
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self.client.username_pw_set(config.mqtt.get('username'), config.mqtt.get('pass'))
        self.client.connect(config.mqtt.get('hostname', config.mqtt.get('port')))
        self.client.loop_start()

    def on_receive(self, message):
        if message.get('command') == 'init':
            try:
                self.client = mqtt.Client()
                self.initMqtt()
            except Exception as ex:
                print (ex)
                time.sleep(1)
                self.actor_ref.tell({'command': 'init'})
        elif message.get('command') == "update_track_status":
            track = message.get('track')
            data = json.dumps({'message_id': track.get('message_id'), 'chat_id': track.get('chat_id'),
                               'message': message.get('status')})
            self.client.publish("update_test", str(data))
