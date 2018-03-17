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


import sys
import libsonic
import time
import requests
import os
import pprint 
from hashlib import md5
from urllib import urlencode
from os.path import dirname, abspath, basename
from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill, intent_file_handler
from mycroft.util.log import LOG
from collections import defaultdict
from fuzzywuzzy.process import extractOne

pp = pprint.PrettyPrinter(indent=4)

try:
    from mycroft.skills.audioservice import AudioService
except:
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
        self.qdict = {'f': 'mp3',
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
        except Exception,e:
           LOG.info('Could not connect to server ' + self.base_url + ': ' + str(e) + ' - ' + repr(e) + '. retrying in 10 sec')
           LOG.info(self.args)
           time.sleep(10)
           self._connect("Attempting reconnect...");

           return

        LOG.info('Loading content')
	self.albums = defaultdict(dict)
	self.artists = defaultdict(dict)
	self.songs = defaultdict(dict)
	cont = 1
	i = 0

	while (cont == 1):
	    self.results = self.subsonic_connection.getAlbumList2('newest', 500, i*500)
	    if self.results['albumList2'] == {}:
		cont = 0
	    else: 
		for album in self.results['albumList2']['album']:
		    self.albums[album['name']] = album;
                    self.albums[album['name'] + ' by ' + album['artist']] = album;
                    self.song_results = self.subsonic_connection.getAlbum(album['id'])
                    #LOG.info(pp.pformat(self.song_results))
                    for song in self.song_results['album']['song']:
                        #LOG.info(pp.pformat(song))
                        self.songs[song['title']] = song
                        self.songs[song['title'] + ' by ' + song['artist']] = song

	    i = i+1

	self.results = self.subsonic_connection.getArtists()
	for artist in self.results['artists']['index']:
	    if type(artist) == type(list()):
		self.artists[artist['artist']['name']] = artist['artist']
	    elif type(artist) == type(dict()):
		for lartist in artist['artist']:
		    self.artists[lartist['name']] = lartist

	self.playlist = {}
        self.playlist.update(self.albums);
        self.playlist.update(self.artists);
        self.playlist.update(self.songs);
        #LOG.info('subsonic :' + pp.pformat(self.playlist));
        self.albums_keys = self.albums.keys();
        self.artists_keys = self.artists.keys();
        self.songs_keys = self.songs.keys();
        self.playlist_keys = self.albums_keys + self.artists_keys + self.songs_keys;
        #LOG.info('subsonic :' + pp.pformat(self.playlist_keys));

        self.register_vocabulary(self.name, 'NameKeyword')

    def initialize(self):
        LOG.info('initializing Subsonic Media skill')
        super(SubsonicMediaSkill, self).initialize()
        self.load_data_files(dirname(__file__))

        self.emitter.on(self.name + '.connect', self._connect)
	self._connect('connecting...');	

        if AudioService:
	    self.audioservice = AudioService(self.emitter)

#        self.add_event('mycroft.audio.service.next', self.handle_next)
#        self.add_event('mycroft.audio.service.prev', self.handle_prev)
#        self.add_event('mycroft.audio.service.pause', self.handle_pause)
#	self.add_event('mycroft.audio.service.resume', self.handle_resume)
#	self.add_event('mycroft.audio.service.stop', self.handle_stop)

    @intent_file_handler('Play.intent')
    def handle_play(self, message):
        LOG.info('Handling play request')
        key, confidence = extractOne(message.data.get('music'), self.playlist_keys)
        if confidence > 50:
            p = key
        else:
            self.speak('couldn\'t find anything matching ' + key)
            return

        backend = message.data.get('backend')
        if backend is None:
            backend = 'vlc'
        else:
            LOG.info(type(backend))

        if p in self.playlist:
            LOG.info('subsonic :' + pp.pformat(self.playlist[p]));
        else:
            self.speak('can\'t find ' + p)
            return

        self.song_url = self.base_url + '/stream?id=' + self.playlist[p]['id'] + '&' + self.args
        LOG.info("URL: " + self.song_url)

        # if audio service module is available use it
        if self.audioservice:
            LOG.info("Playing via audioservice on " + backend)
            self.audioservice.play(self.song_url, backend)
        else: # othervice use normal mp3 playback
            LOG.info("Playing via mp3 playback")
            self.process = play_mp3(self.song_url)

        #self.vlc_player.play()

    def handle_play_random(self, message):
        self.speak("Playing a random song")

    def handle_next(self, message):
        LOG.info("I'd play next");

    def handle_prev(self, message):
        LOG.info("I'd play prev");

    def handle_pause(self, message):
        LOG.info("I'd play pause");

    def handle_resume(self, message):
        LOG.info("I'd play resume");


def create_skill():
    return SubsonicMediaSkill()
