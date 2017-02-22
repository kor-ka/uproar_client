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

        cmd = "mpg123 %s" % track
        p = subprocess.Popen(cmd, shell=True)

        self.queue_actor.tell({'command': 'playing_process', "p": p})

        p.wait()

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
            if to_play.get('action') == 'skip' or to_play.get('action') == 'promote':
                self.check_queue()
            else:
                self.play_and_report(to_play)

    def on_receive(self, message):
        if message.get('command') == 'check':
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
            self.queue_actor.tell({'command': 'downloaded', 'track': track, 'file': mp3_track})
        except Exception as ex:
            print ex
        finally:
            self.check_queue()

    def check_queue(self):
        to_download = self.queue_actor.ask({'command': 'pop_download'})
        if to_download is not None:
            if to_download.get('action') == 'skip' or to_download.get('action') == 'promote':
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

        self.download_queue_promoted = Queue()
        self.player_queue_promoted = Queue()

        self.count = 0
        self.player = Player.start(mqtt_actor, self.actor_ref)
        self.downloader = Downloader.start(mqtt_actor, self.actor_ref)

        self.downloading = None
        self.playing = None

        self.skip_current_download = False
        self.promote_current_download = False
        self.p = None

    # def check_download(self):
    #     if self.downloadQueue.qsize() > 0:
    #         self.count += 1
    #
    #         track = self.downloadQueue.get()
    #         track['count'] = self.count
    #         self.downloader.tell({'command':'download', 'track': track})

    def on_move_action(self, orig, action):
        track = None
        if self.downloading is not None and self.downloading.get('orig') == orig:
            if action == 'skip':
                self.skip_current_download = True
                self.promote_current_download = False
            else:
                self.skip_current_download = False
                self.promote_current_download = True
            track = self.downloading
        elif self.playing is not None and self.playing.get('track').get('orig') == orig:
            track = self.playing.get('track')
            if action == 'skip' and self.p is not None:
                self.p.terminate()
        else:
            for qp in self.player_queue.queue:
                if qp.get('track').get('orig') == orig and qp.get("action") is None:
                    if action == "promote":
                        self.player_queue_promoted.put(qp.copy())
                    qp['action'] = action
                    track = qp.get('track')
            for qd in self.download_queue.queue:
                if qd.get('orig') == orig and qd.get("action") is None:
                    if action == "promote":
                        self.download_queue_promoted.put(qd.copy())
                    qd['action'] = action
                    track = qd
        if track is not None:
            track['message'] = action
            self.mqtt_actor.tell({'command': 'update_track_status', 'status': action, 'track': track})

    def on_receive(self, message):
        if message.get('command') == 'track':
            print ('add track ' + message.get('track').get('track_url') + ' to download queue')
            self.download_queue.put(message.get('track'))
            self.downloader.tell({'command': 'check'})
        elif message.get('command') == 'pop_download':
            self.downloading = None if self.download_queue_promoted.empty() else self.download_queue_promoted.get(
                block=False)
            if self.downloading is None:
                self.downloading = None if self.download_queue.empty() else self.download_queue.get(block=False)
            if self.downloading is not None:
                self.count += 1
                self.downloading['count'] = self.count
            return self.downloading
        elif message.get('command') == 'pop_play':
            self.playing = None if self.player_queue_promoted.empty() else self.player_queue_promoted.get(block=False)
            if self.playing is None:
                self.playing = None if self.player_queue.empty() else self.player_queue.get(block=False)
            if self.playing is None and self.downloading is None and self.download_queue.empty() and self.download_queue_promoted.empty():
                self.mqtt_actor.tell({"command":"boring"})
            return self.playing
        # elif message.get('command') == 'check_download':
        #     self.check_download()
        elif message.get('command') == 'startup':
            self.player.tell(message)
        elif message.get('command') == 'skip':
            self.on_move_action(message.get('orig'), 'skip')
        elif message.get('command') == 'promote':
            self.on_move_action(message.get('orig'), 'promote')
        # elif message.get('command') == 'check_player':
        #     self.check_player()
        elif message.get('command') == 'downloaded':
            if self.skip_current_download:
                self.skip_current_download = False
            else:
                if self.promote_current_download or message.get("track").get("action") == "promote":
                    if self.promote_current_download: 
                        self.promote_current_download = False
                    self.player_queue_promoted.put(message)
                else:
                    self.player_queue.put(message)

                track = message.get('track')
                track['message'] = 'queue'
                self.mqtt_actor.tell({'command': 'update_track_status', 'status': 'queue', 'track': track})
                self.player.tell({'command': 'check'})

                print ('add track ' + message.get('file') + ' to play queue')

        elif message.get('command') == 'playing_process':
            self.p = message.get('p')
