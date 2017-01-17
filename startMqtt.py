import paho.mqtt.client as mqtt, os, urlparse

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    uid = os.environ.get('UPROARUID', 'test')
    client.subscribe(uid, 0)
    client.publish(uid, "hi there")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(msg.topic+" "+str(msg.payload))

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

url_str = os.environ.get('UPROARMQTT', 'mqtt://localhost:1883')
url = urlparse.urlparse(url_str)

client.username_pw_set(url.username, password=url.password)
client.connect(url.hostname, url.port)

# Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.
client.loop_forever()
