# Subsonic Media Skill for Mycroft
# Copyright (C) 2018  Eric Stacey <ejstacey@joyrex.net>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.


# Below is the list of outside modules you'll be using in your skill.
# They might be built-in to Python, from mycroft-core or from external
# libraries.  If you use an external library, be sure to include it
# in the requirements.txt file so the library is installed properly
# when the skill gets installed later by a user.


import libsonic
import time
import os
import pprint
import random
from hashlib import md5
from urllib import urlencode
from mycroft.skills.core import MycroftSkill, intent_file_handler
from mycroft.util.log import LOG
from collections import defaultdict
from fuzzywuzzy.process import extractOne

pp = pprint.PrettyPrinter(indent=4)

try:
    from mycroft.skills.audioservice import AudioService
except Exception, e:
    from mycroft.util import play_mp3
    AudioService = None

__author__ = 'ejstacey'

# Each skill is contained within its own class, which inherits base methods
# from the MycroftSkill class.  You extend this class as shown below.


class SubsonicMediaSkill(MycroftSkill):
    def __init__(self):
        super(SubsonicMediaSkill, self).__init__('Subsonic Media Skill')
        self.volume_is_low = False

    def _connect(self, message):
        self.subsonic_server = self.settings['server']
        self.subsonic_port = self.settings['port']
        self.subsonic_path = self.settings['path']
        self.subsonic_username = self.settings['username']
        self.subsonic_password = self.settings['password']
        self.salt = md5(os.urandom(100)).hexdigest()
        self.token = md5(self.subsonic_password + self.salt[:12]).hexdigest()
        self.qdict = {
           'f': 'mp3',
           'v': '1.16.0',
           'c': 'mycroft-subsonic',
           'u': self.subsonic_username,
           's': self.salt[:12],
           't': self.token
        }
        self.base_url = self.subsonic_server + ':' + str(self.subsonic_port) + self.subsonic_path + '/rest'
        self.args = '%s' % urlencode(self.qdict)

        try:
            self.subsonic_connection = libsonic.Connection(
                self.subsonic_server,
                self.subsonic_username,
                self.subsonic_password,
                self.subsonic_port,
                self.subsonic_path + '/rest'
            )
        except Exception, e:
            LOG.info('Could not connect to server ' + self.base_url + ': ' + str(e) + ' - ' + repr(e) + '. retrying in 10 sec')
            time.sleep(10)
            self._connect("Attempting reconnect...")

        LOG.info('Loading content')
        self.albums = defaultdict(dict)
        self.artists = defaultdict(dict)
        self.songs = defaultdict(dict)
        self.sources = defaultdict(dict)
        self.sources['album'] = defaultdict(dict)
        self.sources['artist'] = defaultdict(dict)
        self.sources['song'] = defaultdict(dict)
        self.sources['genre'] = defaultdict(dict)

        self.results = self.subsonic_connection.getArtists()
        for artist in self.results['artists']['index']:
            if isinstance(artist, list()):
                self.artists[artist['artist']['name']] = artist['artist']['id']
                artist['artist']['album'] = []
                self.sources['artist'][artist['artist']['id']] = artist['artist']
            elif isinstance(artist, dict()):
                for lartist in artist['artist']:
                    self.artists[lartist['name']] = lartist['id']
                    lartist['album'] = []
                    self.sources['artist'][lartist['id']] = lartist

        cont = 1
        i = 0
        while (cont == 1):
            self.results = self.subsonic_connection.getAlbumList2('newest', 500, i*500)
            if self.results['albumList2'] == {}:
                cont = 0
            else:
                for album in self.results['albumList2']['album']:
                    self.albums[album['name']] = album['id']
                    self.albums[album['name'] + ' by ' + album['artist']] = album['id']
                    self.song_results = self.subsonic_connection.getAlbum(album['id'])
                    self.sources['album'][self.song_results['album']['id']] = self.song_results['album']
                    self.sources['artist'][self.song_results['album']['artistId']]['album'].append(self.song_results['album']['id'])
                    for song in self.song_results['album']['song']:
                        self.sources['song'][song['title']] = song
                        artist_title = song['title'] + ' by ' + song['artist']
                        self.sources['song'][artist_title] = song
                        self.songs[song['title']] = song
                        self.songs[artist_title] = song

            i = i+1

        self.albums_keys = self.albums.keys()
        self.artists_keys = self.artists.keys()
        self.songs_keys = self.songs.keys()

        self.register_vocabulary(self.name, 'NameKeyword')

    def initialize(self):
        LOG.info('initializing Subsonic Media skill')
        super(SubsonicMediaSkill, self).initialize()

        self.emitter.on(self.name + '.connect', self._connect)
        self._connect('connecting...')

        if AudioService:
            self.audioservice = AudioService(self.emitter)

    @intent_file_handler('Play.intent')
    def handle_play(self, message):
        LOG.info('Handling play request')
        music = message.data.get('music')
        song_key, song_confidence = extractOne(music, self.songs_keys)
        album_key, album_confidence = extractOne(music, self.albums_keys)
        artist_key, artist_confidence = extractOne(music, self.artists_keys)

        if (
            (song_confidence > 50)
            and (song_confidence >= album_confidence)
            and (song_confidence >= artist_confidence)
        ):
            p = song_key
            source = 'song'
        elif (
            (album_confidence > 50)
            and (album_confidence >= song_confidence)
            and (album_confidence >= artist_confidence)
        ):
            p = album_key
            source = 'album'
        elif (
            (artist_confidence > 50)
            and (artist_confidence >= song_confidence)
            and (artist_confidence >= album_confidence)
        ):
            p = artist_key
            source = 'artist'
        else:
            log = "couldn't find anything matching " \
              + music
            self.speak(log)
            return

        backend = message.data.get('backend')
        if backend is None:
            backend = 'vlc'

        randomise = False
        if backend == 'random':
            backend = 'vlc'
            randomise = True

        self.tracklist = []

        if source == 'song':
            url = self.base_url + '/stream?id=' \
              + self.sources['song'][p]['id'] + '&' + self.args
            self.tracklist.append(url)

        if source == 'album':
            for song in self.sources['album'][self.albums[p]]['song']:
                url = self.base_url + '/stream?id=' + song['id'] + '&' \
                  + self.args
                self.tracklist.append(url)

        if source == 'artist':
            for album in self.sources['artist'][self.artists[p]]['album']:
                for song in self.sources['album'][album]['song']:
                    url = self.base_url + '/stream?id=' + song['id'] + '&' \
                      + self.args
                    self.tracklist.append(url)
                    random.shuffle(self.tracklist)

        utterance = message.data.get('utterance')
        if "on random" in utterance or randomise:
            randomise = True
            random.shuffle(self.tracklist)

        # if audio service module is available use it
        if self.audioservice:
            log = "Playing " + p + " (" + source + ") via audioservice on " \
              + backend
            LOG.info(log)
            self.audioservice.play(self.tracklist, backend)
        else:
            # othervice use normal mp3 playback
            LOG.info("Playing via mp3 playback")
            self.process = play_mp3(self.tracklist)


def create_skill():
    return SubsonicMediaSkill()
