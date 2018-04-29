## subsonic media player
A player for media from the subsonic media server

## Description 
This module plays streaming content from a Subsonic Media Server (https://www.subsonic.org/).

## Examples 
* "play something i can never have by nine inch nails"
* "play pretty hate machine"
* "play nine inch nails"
* "play pretty hate machine on random on my chromecast"

## Credits 
Eric Stacey <ejstacey@joyrex.net>

## Configuring
Install this skill, then go to https://home.mycroft.ai and enter your subsonic details under Skills-\>Subsonic Media Skill

## Current state
Working features:
  - play \<content\>
  - play \<content\> on \<backend\>
  - play \<content\> on random
  - play \<content\> on random on \<backend\>
  - sub play \<content\>
  - sub play \<content\> on \<backend\>
  - sub play \<content\> on random
  - sub play \<content\> on random on \<backend\>
  - stop
  - pause
  - unpause / resume
  - next track
  - previous track

Note: Mycroft has an issue where various modules that use the 'play' functionality can conflict.  In this case, you can use 'sub play' instead of 'play' to make sure the subsonic skill is used for playing content.

\<content\> can be:
  - \<song\>
  - \<song\> by \<artist\>
  - \<album\>
  - \<album\> by \<artist\>
  - \<artist\>

\<backend\> can be the valid name of how to play. You generally only need:
  - vlc [default if not given]
  - \<name of chromecast\>

## Known issues:
  - If you have a large library it can take minutes to initialise, and then another chunk of time (tens of seconds) to determine what you specified as \<content\>.
  - Next / Previous don't always work.  I'm using the standard AudioService Playback Control stuff, so not sure why this is yet.

## TODO
  - \<content\>
    - \<genre\>
    - some music
  - video for chromecast output?
  - podcasts?
  - random / chromecast combinations work, but just through a fluke... need to make it properly capture/separate the values

## Action / Logic
When \<content\> computation matches:
  - song: a single song is played
  - artist: all of the music by the artist is put on randomly
  - album: the album is played in order (unless random mode is specified)
  - genre: all of the music tagged with that genre is put on randomly

