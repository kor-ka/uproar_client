import logging
import pykka, paho.mqtt.client as mqtt, os, urlparse, socket, json, time, config
from subprocess import call
import TrackQueueActor
import PingActor

class MqttActor(pykka.ThreadingActor):
    def __init__(self):
        super(MqttActor, self).__init__()
        self.uid = config.uproar.get('token')
        self.track_queue = None
        self.client = None
        self.once = True

    def on_message(self, client, userdata, msg):

        self.check_q_a()

        if msg.topic == ("device_in_" + self.uid):
            update = json.loads(str(msg.payload))
            update_type = update['update']
            if update_type == "add_content":
                self.track_queue.tell({'command': 'add_content', 'content': update["data"]})
            elif update_type == "skip":
                self.track_queue.tell({'command': 'skip', 'orig': update["data"]})
            elif update_type == "promote":
                self.track_queue.tell({'command': 'promote', 'orig': update["data"]})
            elif update_type == "volume":
                vol_action = "+" if update["data"] == "1" else "-"
                try:
                    call(["amixer", "-q", "sset", "\'Power Amplifier\'", "5%" + vol_action])
                except OSError:
                    pass

    def check_q_a(self):
        if self.track_queue is None or not self.track_queue.is_alive():
            self.track_queue = TrackQueueActor.TrackQueueActor.start(self.actor_ref)

    # The callback for when the client receives a CONNACK response from the server.
    def on_connect(self, client, userdata, flags, rc):
        print("Connected with result code " + str(rc))

        client.subscribe("device_in_" + self.uid, 2)

        if self.once:
            self.once = False
            client.publish('registry', self.uid)
            self.check_q_a()
            self.track_queue.tell({'command': 'startup'})


    def initMqtt(self):
        print('init mqtt')
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        url_str = 'mqtt://%s:%s@m21.cloudmqtt.com:18552' % (self.uid.split("-")[1], self.uid)
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
                logging.exception(ex)
                time.sleep(1)
                self.actor_ref.tell({'command': 'init'})
        elif message.get('command') == "update_track_status":
            track = message.get('track')
            update = {"update":"update_track_status", "data":track}
            self.client.publish("device_out_" + self.uid, str(json.dumps(update)))
        elif message.get('command') == "update":
            self.client.publish("device_out_" + self.uid, str(json.dumps({"update":message.get("update"), "data":message.get("data")})))
            
