import pykka, paho.mqtt.client as mqtt, os, urlparse, socket, json, time, config
from subprocess import call
import TrackQueueActor


class MqttActor(pykka.ThreadingActor):
    uid = config.uproar.get('token')
    track_queue = None
    client = None
    once = True

    # The callback for when a PUBLISH message is received from the server.
    def on_message(self, client, userdata, msg):

        self.check_q_a()

        if msg.topic == ("track_" + self.uid):
            data = json.loads(str(msg.payload))
            self.track_queue.tell({'command': 'track', 'track': data})

        elif msg.topic == ('volume_' + self.uid):
            if str(msg.payload) == '1':
                call(["amixer", "-q", "sset", "\'Power Amplifier\'", "5%+"])
            elif str(msg.payload) == '0':
                call(["amixer", "-q", "sset", "\'Power Amplifier\'", "5%-"])

        elif msg.topic == ("promote_" + self.uid):
            self.track_queue.tell({'command':'promote', 'orig':int(msg.payload)})
        elif msg.topic == ("skip_" + self.uid):
            self.track_queue.tell({'command':'skip', 'orig':int(msg.payload)})

    def check_q_a(self):
        if self.track_queue is None or not self.track_queue.is_alive():
            self.track_queue = TrackQueueActor.TrackQueueActor.start(self.actor_ref)

    # The callback for when the client receives a CONNACK response from the server.
    def on_connect(self, client, userdata, flags, rc):
        print("Connected with result code " + str(rc))

        client.subscribe("track_" + self.uid, 0)
        client.subscribe("volume_" + self.uid, 0)
        client.subscribe("skip_" + self.uid, 0)
        client.subscribe("promote_" + self.uid, 0)

        if self.once:
            self.once = False
            client.publish('server_test', self.uid)
            self.check_q_a()
            self.track_queue.tell({'command': 'startup'})


    def initMqtt(self):
        print('init mqtt')
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        url_str = os.environ.get('UPROARMQTT', 'mqtt://eksepjal:UyPdNESZw5yo@m21.cloudmqtt.com:18552')
        url = urlparse.urlparse(url_str)
        self.client.username_pw_set(url.username, url.password)
        self.client.connect(url.hostname, url.port)
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
            self.client.publish("update_" + self.uid, str(json.dumps(track)))
        elif message.get('command') == "boring":
            self.client.publish("message_" + self.uid, "boring")
            
