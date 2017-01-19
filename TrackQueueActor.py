import urllib, time, os
import subprocess
from Queue import Queue

import pykka


class Player(pykka.ThreadingActor):
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
            self.play(message.get('track'))


class TrackQueueActor(pykka.ThreadingActor):
    queue = Queue()
    count = 0
    player = Player.start()

    def check(self):
        if self.queue.qsize() > 0:
            self.count += 1
            track_url = self.queue.get()
            print ('download track: ' + track_url)
	    #it's download a alot of stuff can happen! (omg, what a shitty shit)
	    try:
            	track = urllib.urlretrieve(track_url,
              	                         str(self.count) + '.mp3')
            	mp3_track = track[0]
            	# print ('convert track to wav')
            	# song = AudioSegment.from_mp3(mp3_track)
            	# wav_track = str(self.count) + '.wav'
            	# song.export(wav_track, format='wav')
            	# os.remove(mp3_track)
            	print ('add track ' + mp3_track + ' to play queue')
            	self.player.tell({'command': 'play', 'track': mp3_track})
	    except Exception as ex:
		print inst

    def on_receive(self, message):
        if message.get('command') == 'track':
            print ('add track ' + message.get('track') + ' to download queue')
            self.queue.put(message.get('track'))
            self.actor_ref.tell({'command': 'check'})
        elif message.get('command') == 'check':
            self.check()
