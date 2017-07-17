"""
Tracking for bluetooth devices.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/device_tracker.bluetooth_tracker/
"""
import logging
import os
import subprocess

import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.core import callback
from homeassistant.helpers.event import track_point_in_utc_time
from homeassistant.const import STATE_OFF, STATE_STANDBY, STATE_ON
from homeassistant.components.device_tracker import (
    YAML_DEVICES, CONF_TRACK_NEW, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL,
    load_config, PLATFORM_SCHEMA, DEFAULT_TRACK_NEW)
from homeassistant.const import (
    ATTR_ENTITY_ID)
import homeassistant.util.dt as dt_util

_LOGGER = logging.getLogger(__name__)

REQUIREMENTS = ['pybluez==0.22']

BT_PREFIX = 'BT_'

DOMAIN = 'device_tracker'
ENTITY_ID = 'bluetooth_tracker'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_TRACK_NEW): cv.boolean
})

BLUETOOTH_TRACKER_SERVICE_SCHEMA = vol.Schema({
    vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
})

BLUETOOTH_TRACKER_SERVICE_TURN_ON = 'bluetooth_tracker_turn_on'
BLUETOOTH_TRACKER_SERVICE_TURN_OFF = 'bluetooth_tracker_turn_off'

def setup_scanner(hass, config, see, discovery_info=None):
    """Set up the Bluetooth Scanner."""
    # pylint: disable=import-error
    import bluetooth
    import bluetooth._bluetooth as bluez

    hass.states.set(DOMAIN + '.' + ENTITY_ID, STATE_ON)

    def turn_on(call):
        """Turn Bluetooth tracker on."""
        _LOGGER.info("Turning on Bluetooth")
        hass.states.set(DOMAIN + '.' + ENTITY_ID, STATE_ON)

    def turn_off(call):
        """Turn Bluetooth tracker off."""
        _LOGGER.info("Turning off Bluetooth")

        try:
            sock = bluez.hci_open_dev(0)
            bluez.hci_send_cmd(sock, bluez.OGF_LINK_CTL, bluez.OCF_INQUIRY_CANCEL)
            sock.close()

            _LOGGER.info("Turned off Bluetooth")
            hass.states.set(DOMAIN + '.' + ENTITY_ID, STATE_OFF)

        except Exception as err:
            _LOGGER.error("Error turning off Bluetooth: %s", err)
            sock.close()

    def see_device(device):
        """Mark a device as seen."""
        see(mac=BT_PREFIX + device[0], host_name=device[1])

    def discover_devices():
        if hass.states.get(DOMAIN + '.' + ENTITY_ID).state != STATE_ON:
            return []

        _LOGGER.debug("Discovering Bluetooth devices")

        """Discover Bluetooth devices."""
        result = bluetooth.discover_devices(
            duration=8, lookup_names=True, flush_cache=True,
            lookup_class=False)
        _LOGGER.debug("Bluetooth devices discovered = " + str(len(result)))
        return result

    hass.services.register(
        DOMAIN, BLUETOOTH_TRACKER_SERVICE_TURN_ON, turn_on, schema=BLUETOOTH_TRACKER_SERVICE_SCHEMA)

    hass.services.register(
        DOMAIN, BLUETOOTH_TRACKER_SERVICE_TURN_OFF, turn_off, schema=BLUETOOTH_TRACKER_SERVICE_SCHEMA)

    # Ensure the Bluetooth tracker is on (if that state has been set)
    if hass.states.get(DOMAIN + '.' + ENTITY_ID).state == STATE_ON:
        turn_on(None)

    yaml_path = hass.config.path(YAML_DEVICES)
    devs_to_track = []
    devs_donot_track = []

    # Load all known devices.
    # We just need the devices so set consider_home and home range
    # to 0
    for device in load_config(yaml_path, hass, 0):
        # Check if device is a valid bluetooth device
        if device.mac and device.mac[:3].upper() == BT_PREFIX:
            if device.track:
                devs_to_track.append(device.mac[3:])
            else:
                devs_donot_track.append(device.mac[3:])

    # If track new devices is true discover new devices on startup.
    track_new = config.get(CONF_TRACK_NEW, DEFAULT_TRACK_NEW)
    if track_new:
        for dev in discover_devices():
            if dev[0] not in devs_to_track and \
               dev[0] not in devs_donot_track:
                devs_to_track.append(dev[0])
                see_device(dev)

    interval = config.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    def update_bluetooth(now):
        """Lookup Bluetooth device and update status."""
        try:
            if track_new:
                for dev in discover_devices():
                    if dev[0] not in devs_to_track and \
                       dev[0] not in devs_donot_track:
                        devs_to_track.append(dev[0])
            for mac in devs_to_track:
                if hass.states.get(DOMAIN + '.' + ENTITY_ID).state != STATE_ON:
                    continue

                _LOGGER.debug("Scanning %s", mac)

                result = bluetooth.lookup_name(mac, timeout=5)
                if not result:
                    # Could not lookup device name
                    continue
                see_device((mac, result))
        except bluetooth.BluetoothError:
            _LOGGER.exception("Error looking up Bluetooth device")
        track_point_in_utc_time(
            hass, update_bluetooth, dt_util.utcnow() + interval)

    update_bluetooth(dt_util.utcnow())

    return True
