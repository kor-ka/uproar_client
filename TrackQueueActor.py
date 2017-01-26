import urllib, time, os
import subprocess
from Queue import Queue

import pykka


class Player(pykka.ThreadingActor):
    def __init__(self, mqtt_actor, queue_actor):
        super(Player, self).__init__()
        self.mqtt_actor = mqtt_actor
        self.queue_actor = queue_actor

    prev = None
    startup_sound = '/usr/uproar/startup.mp3'

    def play(self, track):

        print ('play ' + track)

        cmd = "pkill mpg123"
        subprocess.Popen(cmd, shell=True).wait()

        cmd = "mpg123 %s" % track
        subprocess.Popen(cmd, shell=True).wait()

        if self.prev is not None:
            os.remove(self.prev)
            print ('remove ' + self.prev)
        if track != self.startup_sound:
            self.prev = track

    def play_and_report(self, message):
        track = message.get('track')
        track['message'] = 'playing'
        self.mqtt_actor.tell({'command': 'update_track_status', 'track': track})
        self.play(message.get('file'))
        track['message'] = 'done'
        self.mqtt_actor.tell({'command': 'update_track_status', 'track': track})
        self.check_queue()

    def check_queue(self):
        to_play = self.queue_actor.ask({'command': 'pop_play'})
        if to_play is not None:
            if to_play.get('skip'):
                self.check_queue()
            else:
                self.play_and_report(to_play)


    def on_receive(self, message):
        if message.get('message') == 'check':
            self.check_queue()
        elif message.get('command') == 'startup':
            self.play(self.startup_sound)


class Downloader(pykka.ThreadingActor):
    def __init__(self, mqtt_actor, queue_actor):
        super(Downloader, self).__init__()
        self.mqtt_actor = mqtt_actor
        self.queue_actor = queue_actor

    def download(self, track):
        track_url = track.get('track_url')
        print ('download track: ' + track_url)
        track['message'] = 'download'
        self.mqtt_actor.tell({'command': 'update_track_status', 'track': track})
        # it's download a alot of stuff can happen! (omg, what a shitty shit)
        try:
            resp = urllib.urlretrieve(track_url,
                                      str(track.get('count')) + '.mp3')
            mp3_track = resp[0]
            # print ('convert track to wav')
            # song = AudioSegment.from_mp3(mp3_track)
            # wav_track = str(self.count) + '.wav'
            # song.export(wav_track, format='wav')
            # os.remove(mp3_track)
            print ('add track ' + mp3_track + ' to play queue')
            track['message'] = 'queue'
            self.mqtt_actor.tell({'command': 'update_track_status', 'status': 'queue', 'track': track})
            self.queue_actor.tell({'command': 'downloaded', 'track': track, 'file': mp3_track})
        except Exception as ex:
            print ex

    def check_queue(self):
        to_download = self.queue_actor.ask({'command': 'pop_download'})
        if to_download is not None:
            if to_download.get('skip'):
                self.check_queue()
            else:
                self.download(to_download)

    def on_receive(self, message):
        if message.get('command') == 'check':
            self.check_queue()


class TrackQueueActor(pykka.ThreadingActor):
    def __init__(self, mqtt_actor):
        super(TrackQueueActor, self).__init__()
        self.mqtt_actor = mqtt_actor

        self.download_queue = Queue()
        self.player_queue = Queue()
        self.count = 0
        self.player = Player.start(mqtt_actor, self.actor_ref)
        self.downloader = Downloader.start(mqtt_actor, self.actor_ref)

        self.downloading = None
        self.playing = None

        self.skip_current_download = False

    # def check_download(self):
    #     if self.downloadQueue.qsize() > 0:
    #         self.count += 1
    #
    #         track = self.downloadQueue.get()
    #         track['count'] = self.count
    #         self.downloader.tell({'command':'download', 'track': track})

    def on_skip(self, orig):
        if self.downloading.get('orig') == orig:
            self.skip_current_download = True
        elif self.playing.get('track').get('orig') == orig:
            cmd = "pkill mpg123"
            subprocess.Popen(cmd, shell=True).wait()
        else:
            for qp in self.player_queue.queue:
                if qp.get('track').get('orig') == orig:
                    qp['skip'] = True
                    return
            for qd in self.download_queue.queue:
                if qd.get('orig') == orig:
                    qd['skip'] = True
                    return

    def on_receive(self, message):
        if message.get('command') == 'track':
            print ('add track ' + message.get('track').get('track_url') + ' to download queue')
            self.download_queue.put(message.get('track'))
            self.downloader.tell({'command': 'check'})
        if message.get('command') == 'pop_download':
            self.downloading = self.download_queue.get()
            return self.downloading
        if message.get('command') == 'pop_play':
            self.playing = self.player_queue.get()
            return self.playing
        # elif message.get('command') == 'check_download':
        #     self.check_download()
        elif message.get('command') == 'startup':
            self.player.tell(message)
        elif message.get('command') == 'skip':
            self.on_skip(message.get('orig'))
        # elif message.get('command') == 'check_player':
        #     self.check_player()
        elif message.get('command') == 'downloaded':
            if self.skip_current_download:
                self.skip_current_download = False
            else:
                self.player_queue.put(self.player.tell(message))
                self.player.tell({'command': 'check'})
