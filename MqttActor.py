import pykka, paho.mqtt.client as mqtt, os, urlparse, socket
from subprocess import call

class MqttActor(pykka.ThreadingActor):
    client = mqtt.Client()
    uid = os.environ.get('UPROARUID', 'test')

    def __init__(self, track_queue):
        super(MqttActor, self).__init__()
        self.track_queue = track_queue

    # The callback for when a PUBLISH message is received from the server.
    def on_message(self, client, userdata, msg):
        if msg.topic == ("track_" + self.uid):
            self.track_queue.tell({'command':'track', 'track':str(msg.payload)})
        elif msg.topic == ('volume_' + self.uid):
            if str(msg.payload) == '1':
                call(["amixer", "-q", "sset", "\'Power Amplifier\'", "5%+"])
            elif str(msg.payload) == '0':
                call(["amixer", "-q", "sset", "\'Power Amplifier\'", "5%-"])

    # The callback for when the client receives a CONNACK response from the server.
    def on_connect(self, client, userdata, flags, rc):
        print("Connected with result code " + str(rc))
	client.publish('server_test', socket.gethostbyname(socket.gethostname()))        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        client.subscribe("track_"+self.uid, 0)
        client.subscribe("volume_"+self.uid, 0)

    def initMqtt(self):
	print('init mqtt')
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        url_str = os.environ.get('UPROARMQTT', 'mqtt://eksepjal:UyPdNESZw5yo@m21.cloudmqtt.com:18552')
        url = urlparse.urlparse(url_str)
        self.client.username_pw_set(url.username, url.password)
        self.client.connect(url.hostname, url.port)
        self.client.loop_start()
        self.actor_ref.tell({'command': 'loop'})


    def on_receive(self, message):
        if message.get('command') == 'init':
            self.initMqtt()
        elif message.get('command') == 'loop':
            self.actor_ref.tell({'command': 'loop'})


