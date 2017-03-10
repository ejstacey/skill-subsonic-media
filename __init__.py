import sys
import vlc
import libsonic
import time
import requests
import os
from pprint import pprint
from hashlib import md5
from urllib import urlencode
from os.path import dirname, abspath, basename
from mycroft.skills.media import MediaSkill
from adapt.intent import IntentBuilder
from mycroft.messagebus.message import Message
from mycroft.util.log import getLogger
from mycroft.configuration import ConfigurationManager
from collections import defaultdict
logger = getLogger(abspath(__file__).split('/')[-2])
__author__ = 'ejstacey'

class SubsonicMediaSkill(MediaSkill):
    def __init__(self):
        super(SubsonicMediaSkill, self).__init__('Subsonic Media Skill')
        self.volume_is_low = False

    def _connect(self, message):
        self.config = ConfigurationManager.get()
        self.subsonic_server = self.config['SubsonicMediaSkill']['subsonic_server']
        self.subsonic_port = self.config['SubsonicMediaSkill']['subsonic_port']
        self.subsonic_path = self.config['SubsonicMediaSkill']['subsonic_path']
        self.subsonic_username = self.config['SubsonicMediaSkill']['subsonic_username']
        self.subsonic_password = self.config['SubsonicMediaSkill']['subsonic_password']
        self.salt = md5(os.urandom(100)).hexdigest()
        self.token = md5(self.subsonic_password + self.salt[:12]).hexdigest()
        self.qdict = {'f': 'json',
           'v': '1.14.0',
           'c': 'mycroft-subsonic',
           'u': self.subsonic_username,
           's': self.salt[:12],
           't': self.token
           }
        self.base_url = self.subsonic_server + ':' + str(self.subsonic_port) + '/' + self.subsonic_path + '/rest/'
        self.args = '?%s' % urlencode(self.qdict)
        logger.debug(self)

	try:
	    self.subsonic_connection = libsonic.Connection(
		self.subsonic_server,
		self.subsonic_username,
		self.subsonic_password,
		self.subsonic_port,
		self.subsonic_path + '/rest/'
	    )
	except:
           logger.info('Could not connect to server, retrying in 10 sec')
           time.sleep(10)
           self.emitter.emit(Message(self.name + '.connect'))

           return

        logger.info('Loading content')
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
            logger.debug("Playlist: " + p)
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
        logger.info('initializing Subsonic Media skill')
        super(SubsonicMediaSkill, self).initialize()
        self.load_data_files(dirname(__file__))

        self.emitter.on(self.name + '.connect', self._connect)
	self.emitter.emit(Message(self.name + '.connect'))

        self.vlc_instance = vlc.Instance()
        self.vlc_player = self.vlc_instance.media_player_new()

    def handle_play(self, message):
        logger.info("I'd play")
        #self.vlc_player.play()

    def handle_play_playlist(self, message):
        logger.info("I'd play playlist")
        #self.media = self.vlc_instance.media_new(self.base_url, '--loop', '--http-caching=500')
        #self.vlc_player.set_media(self.media)

    def handle_play_random(self, message):
        self.speak("Playing a random song")


def create_skill():
    return SubsonicMediaSkill()
