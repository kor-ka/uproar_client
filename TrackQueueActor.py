import urllib, time, os
import subprocess
from Queue import Queue

import pykka


class Player(pykka.ThreadingActor):
    def __init__(self, mqtt_actor):
        super(Player, self).__init__()
        self.mqtt_actor = mqtt_actor
    prev = None

    def play(self, track):

        print ('play ' + track)

        # sound = pyglet.media.load(track, streaming=False)
        # player = sound.play()
        # while sound.duration != player.time:
        #     time.sleep(1)
        #
        # player.pause()

        cmd = "mpg123 %s" % track
        subprocess.Popen(cmd, shell=True).wait()

        if self.prev is not None:
            os.remove(self.prev)
            print ('remove ' + self.prev)

        self.prev = track

    def on_receive(self, message):
        if message.get('command') == 'play':
            self.play(message.get('file'))
            self.mqtt_actor.tell({'command': 'update_track_status', 'status':'download', 'track':message.get('track')})



class TrackQueueActor(pykka.ThreadingActor):
    def __init__(self, mqtt_actor):
        super(TrackQueueActor, self).__init__()
        self.mqtt_actor = mqtt_actor

        self.queue = Queue()
        self.count = 0
        self.player = Player.start(mqtt_actor)

    def check(self):
        if self.queue.qsize() > 0:
            self.count += 1
            track = self.queue.get()
            track_url = track.get('track_url')
            print ('download track: ' + track_url)
            self.mqtt_actor.tell({'command': 'update_track_status', 'status':'download', 'track':track})
            # it's download a alot of stuff can happen! (omg, what a shitty shit)
            try:
                resp = urllib.urlretrieve(track_url,
                                           str(self.count) + '.mp3')
                mp3_track = resp[0]
                # print ('convert track to wav')
                # song = AudioSegment.from_mp3(mp3_track)
                # wav_track = str(self.count) + '.wav'
                # song.export(wav_track, format='wav')
                # os.remove(mp3_track)
                print ('add track ' + mp3_track + ' to play queue')
                self.mqtt_actor.tell({'command': 'update_track_status', 'status': 'queue', 'track': track})
                self.player.tell({'command': 'play', 'track': track, 'file':mp3_track})
            except Exception as ex:
                print ex

    def on_receive(self, message):
        if message.get('command') == 'track':
            print ('add track ' + message.get('track').get('track_url') + ' to download queue')
            self.queue.put(message.get('track'))
            self.actor_ref.tell({'command': 'check'})
        elif message.get('command') == 'check':
            self.check()
