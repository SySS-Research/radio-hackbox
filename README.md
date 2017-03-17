# SySS Radio Hack Box

The SySS Radio Hack Box is a proof-of-concept software tool to demonstrate the
replay and keystroke injection vulnerabilities of the wireless keyboard 
Cherry B.Unlimited AES.


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

## Disclaimer

Use at your own risk. Do not use without full consent of everyone involved.
For educational purposes only.

