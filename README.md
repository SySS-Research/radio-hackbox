# SySS Radio Hack Box

The SySS Radio Hack Box is a proof-of-concept software tool to demonstrate the
replay and keystroke injection vulnerabilities of the wireless keyboard 
Cherry B.Unlimited AES.

![SySS Radio Hack Box](https://github.com/SySS-Research/radio-hackbox/blob/master/images/radio_hack_box.png)


## Requirements

- Raspberry Pi
- Raspberry Pi Radio Hack Box shield (a LCD, some LEDs, and some buttons)
- nRF24LU1+ USB radio dongle with flashed [nrf-research-firmware](https://github.com/BastilleResearch/nrf-research-firmware) by the Bastille Threat Research Team, e. g.
	* [Bitcraze CrazyRadio PA USB dongle](https://www.bitcraze.io/crazyradio-pa/)
	* Logitech Unifying dongle (model C-U0007, Nordic Semiconductor based)
- Python2
- PyUSB


## Automatic startup

For automatically starting the Radio Hack Box process on the Raspberry Pi
after a reboot, either use the provided init.d script or the following crontab
entry:

```
@reboot python2 /home/pi/radiohackbox/radiohackbox.py &
```

## Usage

The Radio Hack Box currently has four simple push buttons for
- start/stop recording
- start playback (replay attack)
- start attack (keystroke injection attack)
- start scanning

A **graceful shutdown** of the Radio Hack Box without corrupting the file system
can be performed by pressing the **SCAN button directly followed by the RECORD
button**.

![SySS Radio Hack Box usage](https://github.com/SySS-Research/radio-hackbox/blob/master/images/radio_hack_box_usage.png)


## Demo Video

A demo video illustrating replay and keystroke injection attacks against an AES encrypted wireless keyboard using the SySS Radio Hack Box a.k.a. Cherry Picker is available on YouTube: [SySS Cherry Picker](https://www.youtube.com/watch?v=KMlmd-LhMmo)

![Cherry Picker Demo Video](https://github.com/SySS-Research/radio-hackbox/blob/master/images/radio_hack_box_video.png)

## Pi Radio Hack Box Shield

The hand-crafted Pi shield simply consists of an LCD, some LEDs, some buttons, resistors, and wires soldered to a perfboard.

![Pi Radio Hack Box Shield front](https://github.com/SySS-Research/radio-hackbox/blob/master/images/pi_shield_front.png)
![Pi Radio Hack Box Shield back](https://github.com/SySS-Research/radio-hackbox/blob/master/images/pi_shield_back.png)
![Pi Radio Hack Box Shield breadboard design](https://github.com/SySS-Research/radio-hackbox/blob/master/images/radiohackbox_breadboard.png)


## Disclaimer

Use at your own risk. Do not use without full consent of everyone involved.
For educational purposes only.

