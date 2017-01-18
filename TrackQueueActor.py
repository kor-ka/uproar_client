import urllib, time, os, pyglet
from Queue import Queue

import pykka


class Player(pykka.ThreadingActor):
    prev = None

    def play(self, track):

        sound = pyglet.media.load(track, streaming=False)
        sound.play()
        pyglet.app.run()

        if self.prev is not None:
            os.remove(self.prev)
        self.prev = track

    def on_receive(self, message):
        if message.get('command') == 'play':
            self.play(message.get('track'))


class TrackQueueActor(pykka.ThreadingActor):
    queue = Queue()
    count = 0
    player = Player.start()

    def check(self):
        if self.queue.qsize() > 0:
            self.count += 1
            track_url = self.queue.get()
            track = urllib.urlretrieve(track_url,
                                       str(self.count) + ".mp3")
            self.player.tell({'command': 'play', 'track': track[0]})

    def on_receive(self, message):
        if message.get('command') == 'track':
            self.queue.put(message.get('track'))
            self.actor_ref.tell({'command': 'check'})
        elif message.get('command') == 'check':
            self.check()
