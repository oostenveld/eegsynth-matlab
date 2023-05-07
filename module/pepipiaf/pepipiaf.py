#!/usr/bin/env python

# This module reads data from the PepiPIAF over the PepiUSB dongle
#
# This software is part of the EEGsynth project, see <https://github.com/eegsynth/eegsynth>.
#
# Copyright (C) 2023 EEGsynth project
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import threading
import time
import serial
import serial.tools.list_ports
from fuzzywuzzy import process

if hasattr(sys, 'frozen'):
    path = os.path.split(sys.executable)[0]
    file = os.path.split(__file__)[-1]
    name = os.path.splitext(file)[0]
elif __name__ == '__main__' and sys.argv[0] != '':
    path = os.path.split(sys.argv[0])[0]
    file = os.path.split(sys.argv[0])[-1]
    name = os.path.splitext(file)[0]
elif __name__ == '__main__':
    path = os.path.abspath('')
    file = os.path.split(path)[-1] + '.py'
    name = os.path.splitext(file)[0]
else:
    path = os.path.split(__file__)[0]
    file = os.path.split(__file__)[-1]
    name = os.path.splitext(file)[0]

# eegsynth/lib contains shared modules
sys.path.insert(0, os.path.join(path, '../../lib'))
import EEGsynth


OK = b'OK\r'

command = {}
command['B'] = 'Boot (redémarrage suite à un défaut logiciel)'
command['C'] = 'Effacement de la mémoire'
command['D'] = 'Type de carte, version du logiciel, transmetteur et mode de transmission'
command['e'] = 'Mise à jour des entrées sélectionnées'
command['F'] = 'Renvoi « entrées sélectionnées » et « pas de mesure »'
command['G'] = 'Renvoi « Pas de mesure » et « Taille mémoire »'
command['H'] = 'Transfert Hexa (transfert binaire rapide)'
command['I'] = 'Non implémenté'
command['J'] = 'Mise à jour transmetteur LORA ou SIGFOX en mode de transmission'
command['K'] = 'Changement du canal radio HF'
command['L'] = 'Test Sigfox/Lora envoi une trame de test sur le réseau'
command['M'] = 'Mise à l’heure Ou Changement du numéro du boitier'
command['m'] = 'Mise à l’heure avec pas = 30mn et profondeur mémoire = 10800 mesures N Configuration du module LORA/SIGFOX'
command['P'] = 'Renvoi tension pile'
command['S'] = 'Mise à jour du pas de mesure et occupation mémoire'
command['T'] = 'Lecture de l’heure du capteur'

card_type = {}
card_type[10] = 'Carte Solartron 3'
card_type[13] = 'Carte USB Dresden sans mémoire'
card_type[14] = 'Carte USB Dresden avec mémoire 2GB'
card_type[16] = 'Carte Xylo 2.0'
card_type[17] = 'Carte PepiPIAF USB Version 3'
card_type[18] = 'CARTE_Xylo_2_Hum'
card_type[19] = 'Xylo 3'
card_type[20] = 'Carte USB Bleu'
card_type[21] = 'Xylo Météo 1.0'
card_type[22] = 'Carte ALPHA EcoSys'
card_type[23] = 'Carte ALPHA EcoSys Amplifiée'
card_type[24] = 'CARTE_USB_FORTINEAU'
card_type[25] = 'CARTE_Xylo_Meteo_2'
card_type[26] = 'CARTE_8_Thermocouple'
card_type[27] = 'CARTE_PAR_Thermo_Hygro'
card_type[28] = 'e‐PépiPIAF'
card_type[29] = 'also an e‐PépiPIAF ??'

measurement_type = {}
measurement_type[1] = 'LVDT'
measurement_type[2] = 'PAR 80'
measurement_type[3] = 'HUMECTANCE'
measurement_type[4] = '?'
measurement_type[5] = '?'
measurement_type[6] = '?'
measurement_type[7] = '?'
measurement_type[8] = '?'
measurement_type[9] = 'LICOR'
measurement_type[10] = '?'
measurement_type[11] = 'TEMPERATURE EXTERNE'
measurement_type[12] = 'HYGROMETRIE'
measurement_type[13] = '?'
measurement_type[14] = 'TEMPERATURE RADIANTE'
measurement_type[15] = 'ANEMOMETRE'
measurement_type[16] = 'TEMPERTURE INTERNE A 0.1°'
measurement_type[17] = 'TEMPERATURE EXTERNE'
measurement_type[18] = 'WATERMARK'


def _setup():
    '''Initialize the module
    This adds a set of global variables
    '''
    global patch, name, path, monitor

    # configure and start the patch, this will parse the command-line arguments and the ini file
    patch = EEGsynth.patch(name=name, path=path)

    # this shows the splash screen and can be used to track parameters that have changed
    monitor = EEGsynth.monitor(name=name, patch=patch, debug=patch.getint(
        'general', 'debug', default=1), target=patch.get('general', 'logging', default=None))

    # there should not be any local variables in this function, they should all be global
    if len(locals()):
        print('LOCALS: ' + ', '.join(locals().keys()))


def _start():
    '''Start the module
    This uses the global variables from setup and adds a set of global variables
    '''
    global patch, name, path, monitor
    global serialdevice, s

    # get the specified serial device, or the one that is the closest match
    serialdevice = patch.getstring('serial', 'device')
    serialdevice = EEGsynth.trimquotes(serialdevice)
    serialdevice = process.extractOne(serialdevice, [comport.device for comport in serial.tools.list_ports.comports()])[
        0]  # select the closest match

    try:
        s = serial.Serial(serialdevice, patch.getint('serial', 'baudrate'), timeout=35)
        monitor.success("Connected to serial port")
    except:
        raise RuntimeError("cannot connect to serial port")

    # remove junk that might be remaing from a previous attempt
    resetUSB()
    readRemaining()

    # there should not be any local variables in this function, they should all be global
    if len(locals()):
        print('LOCALS: ' + ', '.join(locals().keys()))


def _loop_once():
    '''Run the main loop once
    This uses the global variables from setup and start, and adds a set of global variables
    '''
    global patch, name, path, monitor
    global serialdevice, s

    # we can get the data from the PepiPIAF about every 30 seconds
    try:
        monitor.info('requesting data...')
        buf = getData()
        monitor.info('parsing data')
        data = parseData(buf)
    except:
        monitor.error('failed reading data, will try again')
        # remove junk that might be remaing from a previous attempt
        resetUSB()
        readRemaining()
        # construct an empty dictionary
        data = {}

    for item in data.keys():
        if isinstance(data[item], list):
            key = patch.getstring('output', 'prefix') + '.' + item
            val = data[item]    # this is a list
            val = val[-1]       # take the last value from the list
            patch.setvalue(key, val)
            monitor.update(key, val)
        else:
            key = patch.getstring('output', 'prefix') + '.' + item
            val = data[item]
            patch.setvalue(key, val)
            monitor.update(key, val)


def _loop_forever():
    '''Run the main loop forever
    '''
    global monitor, patch
    while True:
        monitor.loop()
        _loop_once()
        time.sleep(patch.getfloat('general', 'delay'))


def _stop():
    '''Stop and clean up on SystemExit, KeyboardInterrupt, RuntimeError
    '''
    global monitor, s
    monitor.success("Closing serial port")
    s.close()


##################################################################################################
# the code above is EEGsynth specific
# the code below is PepiPIAF specific
##################################################################################################

# resetUSB()
# readRemaining()
# snifferOn()
# snifferOff()
# printBattery()
# printCardtype()
# printClock()
# printReboots()
# printMeasures()
# printMemory()
# setMemory()
# clearMemory()
# getData()
# determineOffset(buf)
# printFirstLine(buf)
# printBuffer(buf)
# parseData(buf)


def resetUSB():
    s.write(b'+\r')
    buf = s.read(3)  # OK\r
    print(buf)


def readRemaining():
    n = 0
    while s.in_waiting:
        buf = s.read()
        n += len(buf)
    print('read %d bytes' % (n))


def snifferOn():
    s.write(b'Z1\r')


def snifferOff():
    s.write(b'Z0\r')


def printBattery():
    # get the battery status
    s.flush()
    s.write(b'P2\r')
    buf = s.read(3)  # OK\r
    print(buf)
    buf = s.read(5)  # O<pp>;\r
    battery = int(buf[1:3], 16)
    battery = 3.0 / 255 * battery
    print('battery = %f V' % (battery))


def printCardtype():
    # get the type of card
    s.flush()
    s.write(b'D2\r')
    buf = s.read(3)  # OK\r
    print(buf)
    buf = s.read(2)
    type = int.from_bytes(buf[0:1], 'big')
    version = int.from_bytes(buf[1:2], 'big')
    print('type = %d, version = %d' % (type, version))


def printClock():
    s.flush()
    # get the clock
    s.flush()
    s.write(b'T2\r')
    buf = s.read(3)  # OK\r
    print(buf)
    buf = s.read(19)
    year = int(buf[0:2], 16) + 2000
    month = int(buf[3:5], 16)
    day = int(buf[6:8], 16)
    hour = int(buf[9:11], 16)
    minute = int(buf[12:14], 16)
    second = int(buf[15:17], 16)
    print('clock = %04d-%02d-%02d %02d:%02d:%02d' % (year, month, day, hour, minute, second))


def printReboots():
    s.flush()
    # get the number of reboots
    s.flush()
    s.write(b'B2\r')
    buf = s.read(3)  # OK\r
    print(buf)
    buf = s.read(6)
    reboots = int(buf[0:-2], 32)  # ???
    print('reboots = %d' % (reboots))


def printMeasures():
    s.flush()
    # get the selected measures and rate
    s.flush()
    s.write(b'F2\r')
    buf = s.read(3)  # OK\r
    print(buf)
    buf = s.read(4)
    print(buf)


def printMemory():
    # get the amount of memory and rate
    s.flush()
    s.write(b'G2\r')
    buf = s.read(3)  # OK\r
    print(buf)
    buf = s.read(2)
    rate = int.from_bytes(buf[0:1], 'big')
    memory = int.from_bytes(buf[1:2], 'big')
    print('rate = %d, memory = %d' % (rate, memory))
    # rate 1=1m, 2=5m, ... 5=30m ..., but also 8=3m and 0=30s
    # memory 0=2160, 1=4320, etc


def setMemory():
    # set the rate and memory
    s.flush()
    s.write(b'S2\r')
    buf = s.read(3)  # OK\r
    print(buf)
    buf = s.read(2)  # OD
    print(buf)
    rate = 1  # 1=1m, 2=5m, ... 5=30m ..., but also 8=3m and 0=30s, setting it to 30s fails
    memory = 0  # 0=2160, 1=4320, etc
    s.write(bytearray([rate, memory]))
    buf = s.read(1)  # F, or f in case of error
    print(buf)


def clearMemory():
    # clear the memory
    s.flush()
    s.write(b'C2\r')
    buf = s.read(3)  # OK\r
    print(buf)
    buf = s.read(2)  # OD
    print(buf)
    s.write(b'O')
    buf = s.read(1)  # F, or f in case of error
    print(buf)


def getData():
    # transfer all data
    s.flush()
    n = s.write(b'H2\r')
    buf = s.read(3)  # OK\r
    print(buf)
    buf = s.read(1)  # O
    print(buf)
    # now we expect 123456 etcetera
    buf = bytearray()
    while True:
        if not s.in_waiting:
            time.sleep(1)
            if not s.in_waiting:
                break
        buf += s.read(s.in_waiting)
        print('read %d bytes' % (len(buf)))
    return buf


def determineOffset(buf):
    # find the end of the first line by looking for [0x12 0x00 0xff 0xff]
    offset = 0
    slice = [b for b in buf[offset:(offset + 4)]]
    while not (slice[0] == 18 and slice[1] == 0 and slice[2] == 255 and slice[3] == 255):
        offset += 1
        slice = [b for b in buf[offset:(offset + 4)]]
    offset += 4
    return offset


def printFirstLine(buf):
    offset = determineOffset(buf)
    line = buf[0:offset]
    print(["{:02x}".format(b) for b in line])


def printBuffer(buf):
    offset = determineOffset(buf)
    # all subsequent lines appear to be the same length as the first one
    length = offset
    while offset + length < len(buf):
        line = buf[offset:(offset + length)]
        print(["{:02x}".format(b) for b in line])
        offset += length


def parseData(buf):
    offset = determineOffset(buf)
    length = offset

    # keep a list for each of the possible measurements
    luminosity = []
    temperature05 = []  # internal at 0.5 degrees
    minutes = []
    minutes15 = []
    hour = []
    day = []
    month = []
    hygro = []
    temperatureExt = []
    temperature01 = []  # internal at 0.1 degrees
    temperatureRad = []
    wind1min = []
    windAvg = []
    lvdt = []
    watermark1 = []
    watermark2 = []
    battery = []

    while offset + length < len(buf):
        line = buf[offset:(offset + length)]
        # each line ends with 2 bytes
        byte1 = line[-2]
        byte2 = line[-1]
        # the first four bits of the first byte code the type of measurement
        measure = (byte1 & 0xF0) >> 4
        if measure == 0x0:
            # Les mesures de luminosité, PAR 80 ou LICOR
            for i in range(int(length / 2) - 1):
                byte1 = line[2 * i]
                byte2 = line[2 * i + 1]
                if (byte1 == 0xFF) and (byte2 == 0xFF):
                    continue
                elif (byte1 == 0x00) and (byte2 == 0x00):
                    continue
                luminosity.append((byte1 << 8) + byte2)  # uint16
        elif measure == 0x1:
            # Température interne, concaténée avec l’information des minutes
            for i in range(int(length / 2) - 1):
                byte1 = line[2 * i]
                byte2 = line[2 * i + 1]
                if (byte1 == 0xFF) and (byte2 == 0xFF):
                    continue
                elif (byte1 == 0x00) and (byte2 == 0x00):
                    continue
                minutes.append((byte1 & 0xFE) >> 1)
                sign = 1 - 2 * (byte1 & 0x01)
                temperature05.append(0.5 * sign * byte2)
        elif measure == 0x2:
            # La date
            for i in range(int(length / 2) - 1):
                byte1 = line[2 * i]
                byte2 = line[2 * i + 1]
                if (byte1 == 0xFF) and (byte2 == 0xFF):
                    continue
                elif (byte1 == 0x00) and (byte2 == 0x00):
                    continue
                minutes15.append((byte2 & 0x03) * 15)  # this seems not to work
                hour.append((byte2 & 0x7C) >> 2)
                day.append(((byte1 & 0x0F) << 1) + ((byte2 & 0x80) >> 7))
                month.append((byte1 & 0xF0) >> 4)
        elif measure == 0x3:
            # L’hygrométrie
            for i in range(int(length / 2) - 1):
                byte1 = line[2 * i]
                byte2 = line[2 * i + 1]
                if (byte1 == 0xFF) and (byte2 == 0xFF):
                    continue
                elif (byte1 == 0x00) and (byte2 == 0x00):
                    continue
                hygro.append(0.5 * byte2)
        elif measure == 0x4:
            # La température externe avec une résolution de 0.1°
            for i in range(int(length / 2) - 1):
                byte1 = line[2 * i]
                byte2 = line[2 * i + 1]
                if (byte1 == 0xFF) and (byte2 == 0xFF):
                    continue
                elif (byte1 == 0x00) and (byte2 == 0x00):
                    continue
                sign = 1 - 2 * ((byte1 & 0x80) >> 7)
                temperatureExt.append(0.1 * (sign * (((byte1 & 0x7f) << 8) + byte2)))
        elif measure == 0x5:
            # La température interne avec une résolution de 0.1°
            for i in range(int(length / 2) - 1):
                byte1 = line[2 * i]
                byte2 = line[2 * i + 1]
                if (byte1 == 0xFF) and (byte2 == 0xFF):
                    continue
                elif (byte1 == 0x00) and (byte2 == 0x00):
                    continue
                sign = 1 - 2 * ((byte1 & 0x80) >> 7)
                temperature01.append(0.1 * (sign * (((byte1 & 0x7f) << 8) + byte2)))
        elif measure == 0x6:
            # La température Radiante
            for i in range(int(length / 2) - 1):
                byte1 = line[2 * i]
                byte2 = line[2 * i + 1]
                if (byte1 == 0xFF) and (byte2 == 0xFF):
                    continue
                elif (byte1 == 0x00) and (byte2 == 0x00):
                    continue
                sign = 1 - 2 * ((byte1 & 0x80) >> 7)
                temperatureRad.append(0.1 * (sign * (((byte1 & 0x7f) << 8) + byte2)))
        elif measure == 0x7:
            # Anémomètre
            for i in range(int(length / 2) - 1):
                byte1 = line[2 * i]
                byte2 = line[2 * i + 1]
                if (byte1 == 0xFF) and (byte2 == 0xFF):
                    continue
                elif (byte1 == 0x00) and (byte2 == 0x00):
                    continue
                wind1min.append(byte1)
                windAvg.append(byte2)
        elif measure == 0x8:
            # Le LVDT
            for i in range(int(length / 2) - 1):
                byte1 = line[2 * i]
                byte2 = line[2 * i + 1]
                if (byte1 == 0xFF) and (byte2 == 0xFF):
                    continue
                elif (byte1 == 0x00) and (byte2 == 0x00):
                    continue
                sign = 1 - 2 * ((byte1 & 0x80) >> 7)
                value = ((byte1 & 0x7f) << 8) + byte2
                lvdt.append(0.0005 * sign * value)  # in mm
        elif measure == 0x9:
            # unknown
            pass
        elif measure == 0xA:
            # Tensiomètre WATERMARK 1
            for i in range(int(length / 2) - 1):
                byte1 = line[2 * i]
                byte2 = line[2 * i + 1]
                if (byte1 == 0xFF) and (byte2 == 0xFF):
                    continue
                elif (byte1 == 0x00) and (byte2 == 0x00):
                    continue
                watermark1.append(10.0 * ((byte1 << 8) + byte2))  # uint16, in Ohm
        elif measure == 0xB:
            # Tensiomètre WATERMARK 2
            for i in range(int(length / 2) - 1):
                byte1 = line[2 * i]
                byte2 = line[2 * i + 1]
                if (byte1 == 0xFF) and (byte2 == 0xFF):
                    continue
                elif (byte1 == 0x00) and (byte2 == 0x00):
                    continue
                watermark2.append(10.0 * ((byte1 << 8) + byte2))  # uint16, in Ohm
        elif measure == 0xC:
            # unknown
            pass
        elif measure == 0xD:
            # unknown
            pass
        elif measure == 0xE:
            # unknown
            pass
        elif measure == 0xF:
            # unknown
            pass
        offset += length

    data = {}
    if len(luminosity):
        data['luminosity'] = luminosity
    if len(temperature05):
        data['temperature05'] = temperature05
    if len(minutes):
        data['minutes'] = minutes
    if len(temperature01):
        data['temperature01'] = temperature01
    if len(temperatureExt):
        data['temperatureExt'] = temperatureExt
    if len(temperatureRad):
        data['temperatureRad'] = temperatureRad
    if len(minutes15):
        data['minutes15'] = minutes15
    if len(hour):
        data['hour'] = hour
    if len(day):
        data['day'] = day
    if len(month):
        data['month'] = month
    if len(hygro):
        data['hygro'] = hygro
    if len(lvdt):
        data['lvdt'] = lvdt
    if len(wind1min):
        data['wind1min'] = wind1min
    if len(windAvg):
        data['windAvg'] = windAvg
    if len(watermark1):
        data['watermark1'] = watermark1
    if len(watermark2):
        data['watermark2'] = watermark2

    # for k in data.keys():
    #    print('data includes', k)

    # the last 8 bytes of the buffer code the battery voltage and current clock
    current_battery = (3.0 / 255) * buf[-8]
    print('current battery = %f V' % (current_battery))
    current_year = buf[-7] + 2000
    current_month = buf[-6]
    current_day = buf[-5]
    current_hour = buf[-4]
    current_minute = buf[-3]
    current_second = buf[-2]
    print('current clock = %04d-%02d-%02d %02d:%02d:%02d' %
          (current_year, current_month, current_day, current_hour, current_minute, current_second))

    data['battery'] = current_battery
    # the current date and time are confusing, given that the date and time of the measurement are also specified
    # data['current_year'] = current_year
    # data['current_month'] = current_month
    # data['current_day'] = current_day
    # data['current_hour'] = current_hour
    # data['current_minute'] = current_minute
    # data['current_second'] = current_second

    return data

##################################################################################################


if __name__ == '__main__':
    _setup()
    _start()
    try:
        _loop_forever()
    except (SystemExit, KeyboardInterrupt, RuntimeError):
        _stop()
    sys.exit()
