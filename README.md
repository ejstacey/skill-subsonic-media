# Subsonic Media Skill

This skill plays music from a Subsonic Media Server (https://www.subsonic.org/)

Note that depending the size of your library, it can take 1-5 minutes to load this skill. 

## installing
Install this skill, then go to https://home.mycroft.ai and enter your subsonic details under 


## Current state

Working features:
  - play \<content\>
  - play \<content\> on \<backend\>
  - stop
  - pause
  - next
  - prev


\<content\> can be:
  - \<song\>
  - \<song\> by \<artist\>


\<backend\> can be the valid name of how to play. You generally only need:
  - vlc [default if not given]
  - \<name of chromecast\>

Known issues:
  - As mentioned in the summary at the top, if you have a large library it can take minutes to initialise, and then another chunk of time (tens of seconds) to determine what you specified as \<content\>.

TODO:
  - \<content\>
    - \<artist\>
    - \<album\> by \<artist\>
    - some music
  - determine how to specify to play it on random w/o conflicting with the backends
  - video for chromecast output?
  - podcasts?
