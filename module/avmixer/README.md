# AVmixer module

The purpose of this module is to provide an interface to the [AVmixer software](https://neuromixer.com/products/avmixer).

AVmixer incorporates a MIDI interface which can pick up software MIDI messages from other software running on the same computer. The MIDI settings pannel allows the mapping of the incoming MIDI messages onto software functions. It allows three presets for different MIDI interfaces.  

![AVmixer settings](./avmixer.png)

AVmixer can also be controlled using the TouchOSC app, which sends OSC messages that are translated by the [TouchOSC MIDI bridge](http://hexler.net/docs/touchosc-configuration-connections-bridge) into software MIDI commands. AVmixer includes a TouchOSC template layout that is configured to work out of the box with the factory configured presets "3".

![TouchOSC](./touchosc.png)

## Interfacing through regular MIDI

This works if the EEGsynth avmixer module runs on the same computer as the AVmixer software.  

## Interfacing through rtpMIDI over the network

This works regardless of whether the EEGsynth avmixer module is running on the same computer or not. The receiving computer should have network-MIDI, which includes every Mac and every iPhone/iPad and works with any software that uses the Core-MIDI framework. For MS Windows you can download the [driver](http://www.tobias-erichsen.de/software/rtpmidi.html) and follow the [instructions](http://www.tobias-erichsen.de/software/rtpmidi.html).