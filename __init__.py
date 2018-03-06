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
#import vlc
import libsonic
import time
import requests
import os
from pprint import pprint
from hashlib import md5
from urllib import urlencode
from os.path import dirname, abspath, basename
from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill, intent_handler
from mycroft.util.log import LOG
from collections import defaultdict
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
        self.qdict = {'f': 'json',
           'v': '1.16.0',
           'c': 'mycroft-subsonic',
           'u': self.subsonic_username,
           's': self.salt[:12],
           't': self.token
           }
        self.base_url = self.subsonic_server + ':' + str(self.subsonic_port) + '/' + self.subsonic_path + '/rest/'
        self.args = '?%s' % urlencode(self.qdict)

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
	cont = 1
	i = 0

	while (cont == 1):
	    self.results = self.subsonic_connection.getAlbumList2('newest', 500, i*500)
	    if self.results['albumList2'] == {}:
		cont = 0
	    else: 
		for album in self.results['albumList2']['album']:
		    self.albums[album['name']][album['artist']] = album
	    i = i+1

	self.results = self.subsonic_connection.getArtists()
	for artist in self.results['artists']['index']:
	    if type(artist) == type(list()):
		self.artists[artist['artist']['name']] = artist['artist']
	    elif type(artist) == type(dict()):
		for lartist in artist['artist']:
		    self.artists[lartist['name']] = lartist

	self.playlist = {}
	self.playlist.update(self.albums)
	self.playlist.update(self.artists)

	self.register_vocabulary(self.name, 'NameKeyword')
	self.register_vocabulary('some music', 'SomeMusicKeyword')
	self.register_vocabulary('a song', 'ASongKeyword')
        for p in self.playlist.keys():
            LOG.debug("Playlist: " + p)
	    self.register_vocabulary(p, 'PlaylistKeyword' + self.name)
	intent = IntentBuilder('PlayPlaylistIntent' + self.name)\
            .require('PlayKeyword')\
            .require('PlaylistKeyword' + self.name)\
            .build()
        self.register_intent(intent, self.handle_play_playlist)
        intent = IntentBuilder('PlayFromIntent' + self.name)\
            .require('PlayKeyword')\
            .require('PlaylistKeyword')\
            .require('NameKeyword')\
            .build()
	self.register_intent(intent, self.handle_play_playlist)
        intent = IntentBuilder('PlayRandomIntent' + self.name)\
            .require('PlayKeyword')\
            .one_of('SomeMusicKeywork', 'ASongKeyword')\
            .build()
        self.register_intent(intent, self.handle_play_random)


    def initialize(self):
        LOG.info('initializing Subsonic Media skill')
        super(SubsonicMediaSkill, self).initialize()
        self.load_data_files(dirname(__file__))

        self.emitter.on(self.name + '.connect', self._connect)
	self._connect('connecting...');	

        if AudioService:
	    self.audioservice = AudioService(self.emitter)

        #self.add_event('mycroft.audio.service.next', self.next_track)
        #self.add_event('mycroft.audio.service.prev', self.prev_track)
        #self.add_event('mycroft.audio.service.pause', self.pause)
	#self.add_event('mycroft.audio.service.resume', self.resume)

        #self.vlc_instance = vlc.Instance()
        #self.vlc_player = self.vlc_instance.media_player_new()

    def handle_play(self, message):
        LOG.info("I'd play")
        #self.vlc_player.play()

    def handle_play_playlist(self, message):
        LOG.info("I'd play playlist")
        #self.media = self.vlc_instance.media_new(self.base_url, '--loop', '--http-caching=500')
        #self.vlc_player.set_media(self.media)

    def handle_play_random(self, message):
        self.speak("Playing a random song")


def create_skill():
    return SubsonicMediaSkill()
