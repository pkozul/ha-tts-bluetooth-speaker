"""
Support for TTS on a Bluetooth Speaker

"""
import voluptuous as vol

from homeassistant.components.media_player import (
    SUPPORT_PLAY_MEDIA,
    SUPPORT_VOLUME_SET,
    PLATFORM_SCHEMA,
    MediaPlayerDevice)
from homeassistant.const import (
    CONF_NAME, STATE_OFF, STATE_PLAYING)
import homeassistant.helpers.config_validation as cv

try:
   from ..device_tracker import bluetooth_tracker
except ImportError:
   pass
import subprocess

import logging

import os
import re
import sys

DEFAULT_NAME = 'TTS Bluetooth Speaker'
DEFAULT_VOLUME = 0.5
DEFAULT_CACHE_DIR = "tts"
DEFAULT_SILENCE_DURATION = 0.0

SUPPORT_BLU_SPEAKER = SUPPORT_PLAY_MEDIA | SUPPORT_VOLUME_SET

CONF_ADDRESS = 'address'
CONF_VOLUME = 'volume'
CONF_CACHE_DIR = 'cache_dir'
CONF_PRE_SILENCE_DURATION = 'pre_silence_duration'
CONF_POST_SILENCE_DURATION = 'post_silence_duration'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_VOLUME, default=DEFAULT_VOLUME):
        vol.All(vol.Coerce(float), vol.Range(min=0, max=1)),
    vol.Optional(CONF_PRE_SILENCE_DURATION, default=DEFAULT_SILENCE_DURATION):
        vol.All(vol.Coerce(float), vol.Range(min=0, max=60)),
    vol.Optional(CONF_POST_SILENCE_DURATION, default=DEFAULT_SILENCE_DURATION):
        vol.All(vol.Coerce(float), vol.Range(min=0, max=60)),
    vol.Optional(CONF_CACHE_DIR, default=DEFAULT_CACHE_DIR): cv.string,
})

_LOGGER = logging.getLogger(__name__)

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the Bluetooth Speaker platform."""
    name = config.get(CONF_NAME)
    address = config.get(CONF_ADDRESS)
    volume = float(config.get(CONF_VOLUME))
    pre_silence_duration = float(config.get(CONF_PRE_SILENCE_DURATION))
    post_silence_duration = float(config.get(CONF_POST_SILENCE_DURATION))
    cache_dir = get_tts_cache_dir(hass, config.get(CONF_CACHE_DIR))

    add_devices([BluetoothSpeakerDevice(hass, name, address, volume, pre_silence_duration, post_silence_duration, cache_dir)])
    return True

def get_tts_cache_dir(hass, cache_dir):
    """Get cache folder."""
    if not os.path.isabs(cache_dir):
        cache_dir = hass.config.path(cache_dir)
    return cache_dir

class BluetoothSpeakerDevice(MediaPlayerDevice):
    """Representation of a Bluetooth Speaker on the network."""

    def __init__(self, hass, name, address, volume, pre_silence_duration, post_silence_duration, cache_dir):
        """Initialize the device."""
        self._hass = hass
        self._name = name
        self._is_standby = True
        self._current = None
        self._address = address
        self._volume = volume
        self._pre_silence_duration = pre_silence_duration
        self._post_silence_duration = post_silence_duration
        self._cache_dir = self.get_tts_cache_dir(cache_dir)
        self._tracker = 'custom_components.device_tracker.bluetooth_tracker' in sys.modules
        _LOGGER.debug('Bluetooth tracker integration:  {}'.format(str(self._tracker)))

    def get_tts_cache_dir(self, cache_dir):
        """Get cache folder."""
        if not os.path.isabs(cache_dir):
            cache_dir = hass.config.path(cache_dir)
        return cache_dir

    def update(self):
        """Retrieve latest state."""
        if self._is_standby:
            self._current = None
        else:
            self._current = True

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    # MediaPlayerDevice properties and methods
    @property
    def state(self):
        """Return the state of the device."""
        if self._is_standby:
            return STATE_OFF
        else:
            return STATE_PLAYING

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        return SUPPORT_BLU_SPEAKER

    @property
    def volume_level(self):
        """Volume level of the media player (0..1)."""
        return self._volume

    def set_volume_level(self, volume):
        """Set volume level, range 0..1."""
        # self._vlc.audio_set_volume(int(volume * 100))
        self._volume = volume

    def play_media(self, media_type, media_id, **kwargs):
        """Send play commmand."""
        _LOGGER.info('play_media: %s', media_id)
        self._is_standby = False

        media_file = self._cache_dir + '/' + media_id[media_id.rfind('/') + 1:];
        sink = 'pulse::bluez_sink.' + re.sub(':', '_', self._address)
        volume = str(self._volume * 100)

        pre_silence_file = "/tmp/pre_silence.mp3"
        post_silence_file = "/tmp/post_silence.mp3"
        media_file_to_play = media_file

        if (self._pre_silence_duration > 0) or (self._post_silence_duration > 0):
            media_file_to_play = "/tmp/tts_{}".format(os.path.basename(media_file))

            command = "sox -c 1 -r 24000 -n {} synth {} brownnoise gain -50".format(pre_silence_file, self._pre_silence_duration)
            _LOGGER.debug('Executing command: %s', command)
            subprocess.call(command, shell=True)

            command = "sox -c 1 -r 24000 -n {} synth {} brownnoise gain -50".format(post_silence_file, self._post_silence_duration)
            _LOGGER.debug('Executing command: %s', command)
            subprocess.call(command, shell=True)

            command = "sox {} {} {} {}".format(pre_silence_file, media_file, post_silence_file, media_file_to_play)
            _LOGGER.debug('Executing command: %s', command)
            subprocess.call(command, shell=True)

        if self._tracker:
            self._hass.services.call(bluetooth_tracker.DOMAIN, bluetooth_tracker.BLUETOOTH_TRACKER_SERVICE_TURN_OFF, None)

        command = "mplayer -ao {} -quiet -channels 2 -volume {} {}".format(sink, volume, media_file_to_play);
        _LOGGER.debug('Executing command: %s', command)
        subprocess.call(command, shell=True)

        if (self._pre_silence_duration > 0) or (self._post_silence_duration > 0):
            command = "rm {} {} {}".format(pre_silence_file, media_file_to_play, post_silence_file);
            _LOGGER.debug('Executing command: %s', command)
            subprocess.call(command, shell=True)

        if self._tracker:
            self._hass.services.call(bluetooth_tracker.DOMAIN, bluetooth_tracker.BLUETOOTH_TRACKER_SERVICE_TURN_ON, None)

        self._is_standby = True
