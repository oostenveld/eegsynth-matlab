#!/bin/bash

export RTMIDI_API=MACOSX_CORE
export DYLD_LIBRARY_PATH=/System/Library/Frameworks/ImageIO.framework/Versions/A/Resources
export DYLD_LIBRARY_PATH=$DYLD_LIBRARY_PATH:/usr/local/lib

MODULE=`basename $0 .sh`

EEGSYNTH=$HOME/eegsynth
PATCH=`dirname $0`

$EEGSYNTH/src/module/$MODULE/$MODULE.py -i $PATCH/playbacksignal_sound.ini
