import urllib, time, os
import subprocess
import os.path
from Queue import Queue

import logging

import pykka
import signal

import sys
from pytube import YouTube


class Player(pykka.ThreadingActor):
    def __init__(self, mqtt_actor, queue_actor):
        super(Player, self).__init__()
        self.mqtt_actor = mqtt_actor
        self.queue_actor = queue_actor

    prev = None
    startup_sound = '/usr/uproar/startup.mp3'
    log_count = 0
    def play(self, track, with_command, args, delete):
        args = [] if args is None else args
        args.insert(0, with_command)
        args.insert(1, track)
        p = subprocess.Popen(args)
        self.queue_actor.tell({'command': 'playing_process', "p": p})

        # TODO schedule kill
        p.wait()

        if self.prev is not None:
            os.remove(self.prev)
            print ('remove ' + self.prev)
        if track != self.startup_sound and os.path.isfile(track) and delete:
            self.prev = track

    def play_and_report(self, message):
        track = message.get('track')
        track['message'] = 'playing'
        self.mqtt_actor.tell({'command': 'update_track_status', 'track': track})

        if message.get("file"):
            self.play(message.get("file"), track.get("play_with"), track.get("args"), True)
        elif message.get("track").get("url"):
            if message.get("track").get("type") == "ytb":
                self.play(message.get("file"), track.get("play_with"), track.get("args"), True)

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
        try:
            if message.get('command') == 'check':
                self.check_queue()
            elif message.get('command') == 'startup':
                if os.path.isfile(self.startup_sound):
                    self.play(self.startup_sound, "mpg123", [], False)
        except Exception as ex:
            logging.exception(ex)


class Downloader(pykka.ThreadingActor):
    def __init__(self, mqtt_actor, queue_actor):
        super(Downloader, self).__init__()
        self.mqtt_actor = mqtt_actor
        self.queue_actor = queue_actor

    def download(self, track):

        print ('download track: ' + track.get("title"))
        track['message'] = 'download'
        self.mqtt_actor.tell({'command': 'update_track_status', 'track': track})

        type = track.get("type")
        if type == "track":

            track_url = track.get('track_url')

            # it's download a alot of stuff can happen! (omg, what a shitty shit)
            try:
                resp = urllib.urlretrieve(track_url,
                                          str(track.get('count')) + '.mp3')
                file = resp[0]
                # print ('convert track to wav')
                # song = AudioSegment.from_mp3(mp3_track)
                # wav_track = str(self.count) + '.wav'
                # song.export(wav_track, format='wav')

                # os.remove(mp3_track)
                track["play_with"] = "mpg123"
                self.queue_actor.tell({'command': 'downloaded', 'track': track, 'file': file})
            except Exception as ex:
                print logging.exception(ex)

        elif type == "ytb":
            try:
                print ('extracting ytb video link')
                yt = YouTube(track.get("url"))
                video = yt.filter('mp4')[-1]
                if video:
                    track["url"] = video.url

                    resp = urllib.urlretrieve(video.url,
                                              str(track.get('count')) + '.mp4')
                    file = resp[0]
                    track["play_with"] = "mplayer"
                    track["args"] =["-framedrop"]
                    if 'darwin' in sys.platform:
                        track["args"].insert(0, "-fs")
                    else:
                        track["args"].insert(0, "-vo")
                        track["args"].insert(1, "null")
                    # track["kill"] = "killall -9 VLC"
                    self.queue_actor.tell({'command': 'downloaded', 'track': track, 'file': file})
            except Exception as ex:
                print logging.exception(ex)
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
        self.boring = False

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
                if track.get("kill"):
                    os.system(track.get("kill"))
                else:
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
            self.mqtt_actor.tell({'command': 'update_track_status', 'track': track})

    def on_receive(self, message):
        try:

            if message.get('command') == 'add_content':

                track = message.get("content").get("audio")
                ytb = message.get("content").get("youtube_link")
                if track or ytb:
                    if track:
                        content = track
                        content["type"] = "track"
                    elif ytb:
                        content = ytb
                        content["type"] = "ytb"
                    content['title'] = content.get('title').encode('ascii', 'ignore').decode(
                        'ascii')
                    print ('add content ' + content.get('title') + ' to download queue')
                    self.download_queue.put(content)
                    self.boring = True
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
                self.playing = None if self.player_queue_promoted.empty() else self.player_queue_promoted.get(
                    block=False)
                if self.playing is None:
                    self.playing = None if self.player_queue.empty() else self.player_queue.get(block=False)
                if self.playing is None and self.downloading is None and self.download_queue.empty() and self.download_queue_promoted.empty() and self.boring:
                    self.boring = False
                    self.mqtt_actor.tell({"command": "update", "update": "boring"})
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
                    self.mqtt_actor.tell({'command': 'update_track_status', 'track': track})
                    print ('add track ' + message.get('track').get('title') + ' to play queue')
                    self.player.tell({'command': 'check'})


            elif message.get('command') == 'playing_process':
                self.p = message.get('p')
        except Exception as ex:
            logging.exception(ex)
