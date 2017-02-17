import urllib, time, os
import subprocess
from Queue import Queue

import pykka


class PingActor(pykka.ThreadingActor):
    def __init__(self, mqtt_actor):
        super(PingActor, self).__init__()
        self.mqtt_actor = mqtt_actor

    def on_start(self):
        self.actor_ref.tell({"command":"ping"}) 

    def ping(self):
        self.mqtt_actor.tell({"command":"ping"})
        print "--ping--"
        time.sleep(10)
        self.actor_ref.tell({"command":"message", "message":"ping"})

    def on_receive(self, message):
        if message.get('command') == 'ping':
            self.ping()



