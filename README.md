# TTS Bluetooth Speaker for Home Assistant

This project provides the following custom components for Home Assistant, and allows them to place nicely together:

- Bluetooth tracker (presence detection)
- Bluetooth speaker (for TTS)

Since the Bluetooth tracker constantly scans for devices, playback of audio on the Bluetooth speaker may be disrupted / become choppy while scanning. These custom components work together to ensure only one of them is accessing Bluetooth at any givem time.

The flow is something like this:

- Bluetooth tracker component continually scans for devices (presence detection)
- TTS service gets called to play something on the Bluetooth speaker
- TTS Bluetooth speaker component disables Bluetooth tracker component
- TTS Bluetooth speaker terminates any running Bluetooth scans
- TTS Bluetooth speaker component plays the TTS MP3 file
- TTS Bluetooth speaker component enables Bluetooth tracker component
- Bluetooth tracker component continues scanning for devices (presence detection)

## Getting Started

### 1) Install Pulse Audio (with Bluetooth support) and MPlayer

```
sudo apt-get install pulseaudio pulseaudio-module-bluetooth bluez mplayer
```

### 2) Add HA user to 'pulse-access' group

The example assume that HA runs under the 'pi' account, so make sure you add the appropriate user in your case.

```
sudo adduser pi pulse-access
```

### 3) Add Bluetooth discovery to Pulse Audio

In `/etc/pulse/system.pa`, add the following to the bottom of the file:

```
### Bluetooth Support
.ifexists module-bluetooth-discover.so
load-module module-bluetooth-discover
.endif
```

### 4) Create a service to run Pulse Audio at startup
Create the file `/etc/systemd/system/pulseaudio.service` and add the following to it:

```
[Unit]
Description=Pulse Audio

[Service]
Type=simple
ExecStart=/usr/bin/pulseaudio --system --disallow-exit --disable-shm --exit-idle-time=-1

[Install]
WantedBy=multi-user.target
```

Enable the service to start at boot time.

```
sudo systemctl daemon-reload
sudo systemctl enable pulseaudio.service
```

### 5) Add the TTS Bluetooth Speaker to HA

Copy the TTS Bluetooth Speaker component (from this GitHub repo)
**custom_components/media_player/tts_bluetooth_speaker.py** and save it to the`/home/pi/.homeassistant/custom_components/media_player/` directory.

### 6) Add the (new) Bluetooth Tracker to HA

Copy the Bluetooth Tracker component (from this GitHub repo)
**custom_components/device_tracker/bluetooth_tracker.py** and save it to the `/home/pi/.homeassistant/custom_components/device_tracker/` directory.

### 7) Create a script to pair the Bluetooth speaker at startup

This step assumes you have already trusted and paired your Bluetooth speaker (using `bluetoothctl`). That utility will also display the Bluetooth address for your speaker.

Create the file `/home/pi/.homeassistant/scripts/pair_bluetooth.sh` and add the following to it. Make sure to replace the Bluetooth address with that of your Bluetooth speaker.

```
#!/bin/bash

bluetoothctl << EOF
connect 00:2F:AD:12:0D:42
EOF
```

In `/etc/rc.local`, add the following to the end of the file to run the script at startup:

```
# Pair Bluetooth devices
/home/pi/.homeassistant/scripts/pair_bluetooth.sh

exit 0
```

### 8) Start using it in HA

By this stage (after a reboot), you should be able to start using the TTS Bluetooth speaker in HA.

Below is an example of how these components are configured. You need to specify the Bluetooth address of your speaker, and optionally set the volume level (must be between 0 and 1). If you've change your TTS cache directory (in your TTS config), then you should set the `cache_dir:` here to match.

```
device_tracker:
  - platform: bluetooth_tracker

media_player:
  - platform: tts_bluetooth_speaker
    address: 00:2F:AD:12:0D:42
    volume: 0.45
#    cache_dir: /tmp/tts    # Optional - make sure it matches the same setting in TTS config
```

Below is a simple automation to test out the TTS Bluetooth speaker component:

```
automation: 
  - alias: Home Assistant Start
    trigger:
      platform: homeassistant
      event: start
    action:
      - service: tts.google_say
        data:
          entity_id: media_player.tts_bluetooth_speaker
          message: 'Home Assistant has started'
```
