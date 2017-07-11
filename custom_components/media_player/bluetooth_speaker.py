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

import subprocess

import logging

import os
import re

DEFAULT_NAME = 'Bluetooth Speaker'
DEFAULT_VOLUME = 0.5
DEFAULT_CACHE_DIR = "tts"

# This is the path where the script is located
SCRIPT_DIR = '/home/pi/.homeassistant/scripts/'

# This is the name of the script
SCRIPT_NAME = SCRIPT_DIR + 'play_url_bluetooth.sh'

SUPPORT_BLU_SPEAKER = SUPPORT_PLAY_MEDIA | SUPPORT_VOLUME_SET

CONF_ADDRESS = 'address'
CONF_VOLUME = 'volume'
CONF_CACHE_DIR = 'cache_dir'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_VOLUME, default=DEFAULT_VOLUME):
        vol.All(vol.Coerce(float), vol.Range(min=0, max=1)),
    vol.Optional(CONF_CACHE_DIR, default=DEFAULT_CACHE_DIR): cv.string,
})

_LOGGER = logging.getLogger(__name__)

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the Bluetooth Speaker platform."""
    name = config.get(CONF_NAME)
    address = config.get(CONF_ADDRESS)
    volume = float(config.get(CONF_VOLUME))
    cache_dir = get_tts_cache_dir(hass, config.get(CONF_CACHE_DIR))

    add_devices([BluetoothSpeakerDevice(name, address, volume, cache_dir)])
    return True

def get_tts_cache_dir(hass, cache_dir):
    """Get cache folder."""
    if not os.path.isabs(cache_dir):
        cache_dir = hass.config.path(cache_dir)
    return cache_dir

class BluetoothSpeakerDevice(MediaPlayerDevice):
    """Representation of a Bluetooth Speaker on the network."""

    def __init__(self, name, address, volume, cache_dir):
        """Initialize the device."""
        self._name = name
        self._is_standby = True
        self._current = None
        self._address = address
        self._volume = volume
        self._cache_dir = self.get_tts_cache_dir(cache_dir)

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

        sink = 'pulse::bluez_sink.' + re.sub(':', '_', self._address)
        volume = str(self._volume * 100)
        media_file = self._cache_dir + '/' + media_id[media_id.rfind('/') + 1:];

        subprocess.call('mplayer' \
            ' -ao ' + sink + '' \
            ' -really-quiet' \
            ' -noconsolecontrols' \
            ' -srate 44100' \
            ' -channels 2' \
            ' -volume ' + volume + '' \
            ' ' + media_file, shell=True)

        self._is_standby = True
