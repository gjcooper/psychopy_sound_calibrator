#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created by Gavin Cooper for Gavin Cooper.
University of Newcastle
2016
"""
# Imports
from __future__ import division, print_function
from psychopy import visual, core, data, event, logging, gui, sound
import csv
import os  # handy system and path functions
import sys
import pandas as pd
from numpy import linspace
import ast


class SoundSpec(object):
    def __init__(self):
        self._sound = None
        self.volume = 1.0
        self._genVol = None

    @property
    def sound(self):
        """return a sound if it exists, otherwise generate and return it"""
        if self._sound and self.volume == self._genVol:
            return self._sound
        self._generate()
        self._genVol = self.volume
        return self._sound


class SoundFromSpec(SoundSpec):
    '''Holds a sound specification and returns a psychopy sound object when
    queried'''
    def __init__(self, specification=None):
        """One and only one of filename or specification must be not None"""
        super(SoundFromSpec, self).__init__()
        self.freq = specification['Frequency']
        self.dur = float(specification['Length'])
        self.target = specification['Target']

    def _generate(self):
        self._sound = sound.Sound(value=self.freq, secs=self.dur,
                                  volume=self.volume)

    def __eq__(self, other):
        if not isinstance(other, SoundFromSpec):
            return NotImplemented
        return (self.freq == other.freq and
                self.dur == other.dur and
                self.target == other.target)

    def __hash__(self):
        return hash((self.freq, self.dur, self.target))

    def __str__(self):
        return 'Freq:({0.freq}), Duration:({0.dur})'.format(self)


class SoundFromFile(SoundSpec):
    '''Holds a sound file and generates psychopy sound object as needed'''
    def __init__(self, filename=None, target=None):
        super(SoundFromFile, self).__init__()
        self.filename = filename
        self.target = target

    def _generate(self):
        self._sound = sound.Sound(value=self.filename, volume=self.volume)

    def __eq__(self, other):
        if not isinstance(other, SoundFromFile):
            return NotImplemented
        return (self.filename == other.filename and
                self.target == other.target)

    def __hash__(self):
        return hash((self.filename, self.target))

    def __str__(self):
        return self.filename


def loadSounds(soundfile):
    """Read and parse the sounds.csv file"""
    with open(soundfile) as soundfile:
        soundreader = csv.DictReader(soundfile)
        for row in soundreader:
            length = row['Length']
            if ';' in length:
                row['Length'] = ast.literal_eval(length.replace(';', ','))
            else:
                row['Length'] = ast.literal_eval(length)
            row['Frequency'] = ast.literal_eval(row['Frequency'])
            yield row


class Calibration(object):
    """Holds all experiment details such as implementation, run data (date etc)
    and creates resources like file descriptors and display adapters"""
    def __init__(self, name='Calibration'):
        """Setup the experiment, create windows and gather subject details"""
        super(Calibration, self).__init__()
        self.date = data.getDateStr()
        self.name = name
        file_filter = 'Sound specifications (*.csv);;Sound files (*.wav)'
        self._inputhandling(gui.fileOpenDlg(allowed=file_filter))
        self._filehandling()
        self._hwsetup()

    def _inputhandling(self, filelist):
        """Handles the result of the file selection dialog"""
        if not filelist:
            self.cleanQuit()
        self.genSounds = []
        self.readSounds = {}
        for f in filelist:
            if f[-3:] == 'csv':
                self.genSounds.extend(list(loadSounds(f)))
            else:
                self.readSounds[f] = ''
        if self.readSounds:
            gui.DlgFromDict(self.readSounds,
                            title='Enter dB Target per file - CSV for > 1')

    def _filehandling(self):
        """Create file paths, setup logging, change working directories"""
        # Ensure that relative paths start from the same directory as script
        _thisDir = os.path.dirname(os.path.abspath(__file__)).decode(
            sys.getfilesystemencoding())
        os.chdir(_thisDir)
        # Create base output filename
        filestruct = '{0.name}_{0.date}'.format(self)
        self.filename = os.path.join(_thisDir, 'data/'+filestruct)
        # save a log file for detail verbose info
        self.logFile = logging.LogFile(self.filename + '.log',
                                       level=logging.EXP)
        logging.console.setLevel(logging.WARNING)  # this outputs to the screen

    def _hwsetup(self):
        """Set up hardware like displays, sounds, etc"""
        self.win = visual.Window(size=(1280, 1024), fullscr=True,
                                 allowGUI=False, useFBO=True,
                                 monitor='testMonitor', units='norm')
        # store frame rate of monitor if we can measure it successfully
        self.frameRate = self.win.getActualFrameRate()
        if self.frameRate is not None:
            self.frameDur = 1.0/round(self.frameRate)
        else:
            self.frameDur = 1.0/60.0  # couldn't get a reliable measure/guess
        # Set up the sound card
        sound.init(rate=48000, stereo=True, buffer=256)
        self.volume = 0.4

    def buildStimuli(self):
        """Build individual stimuli for use in the experiment"""
        # Initialize components for Routine "TDTInstructions"
        self.defaulttext = dict(font='Arial', height=0.1, alignHoriz='center')

        self.sounds = []
        for filename, target in self.readSounds.items():
            self.sounds.append(SoundFromFile(filename=filename, target=target))

        for spec in self.genSounds:
            try:
                self.sounds.append(SoundFromSpec(spec))
            except TypeError:
                for dur in linspace(*spec['Length']):
                    newspec = spec.copy()
                    newspec['Length'] = dur
                    self.sounds.append(SoundFromSpec(newspec))

    def runInstructions(self):
        """Present the instructions"""
        itext = u'''
        This task will present sounds to be measured.
        The keys to use will be as follows:

            ←\t\t\t- go to previous sound
            →\t\t\t- go to next sound
            ↓\t\t\t- change volume down
            ↑\t\t\t- change volume up
            i\t\t\t\t- change volume increment (0.1, 0.01, 0.001)
            m\t\t\t- mark volume as correct
            p\t\t\t- plot results
            Escape\t- quits

        Press any key to continue
        '''
        instruction = visual.TextStim(win=self.win, name='InstrText',
                                      text=itext, **self.defaulttext)
        instruction.wrapWidth += 0.7
        instruction.draw()
        self.win.flip()
        while True:
            theseKeys = event.getKeys()
            if theseKeys:
                break

    def previous(self):
        self.idx -= 1
        if self.idx < 0:
            self.idx = len(self.marked) - 1

    def next(self):
        self.idx += 1
        if self.idx == len(self.marked):
            self.idx = 0

    def increase(self):
        self.vol += self.inc
        if self.vol > 1.0:
            self.vol = 1.0

    def decrease(self):
        self.vol -= self.inc
        if self.vol < 0.0:
            self.vol = 0.0

    def toggleinc(self):
        toggle = {0.1: 0.01, 0.01: 0.001, 0.001: 0.1}
        self.inc = toggle[self.inc]

    def mark(self):
        self.marked[self.current].append(self.vol)

    def check_keys(self, sound=None):
        event.clearEvents()
        repeatTimer = core.CountdownTimer(1.5)
        keymap = {'left': self.previous,
                  'right': self.next,
                  'up': self.increase,
                  'down': self.decrease,
                  'i': self.toggleinc,
                  'm': self.mark,
                  'escape': self.cleanQuit}
        sound.play()
        while True:
            theseKeys = event.getKeys(keyList=keymap.keys())
            if len(theseKeys) > 0:  # at least one key was pressed
                # grab just the first key pressed
                key = theseKeys[0]
                # return action
                return keymap[key]
            if repeatTimer.getTime() < 0:
                sound.play()
                repeatTimer.reset()

    @property
    def current(self):
        """Return current sound"""
        return self.sounds[self.idx]

    def runCalibration(self):
        '''Run through all sounds and check calibration'''
        self.idx = 0
        self.vol = 0.4
        self.inc = 0.1
        self.marked = {k: [] for k in self.sounds}
        rtext = u'''
        Calibration in progress

            Sound:\t\t\t{}
            Target:\t\t\t{}
            Marked:\t\t\t{}
            Volume:\t\t\t{}
            <Escape>\t- quits
        '''
        while True:
            # Display our current information
            txt = rtext.format(self.current, self.current.target,
                               bool(self.marked[self.current]), self.vol)
            runText = visual.TextStim(win=self.win, name='RunText',
                                      text=txt, **self.defaulttext)
            runText.wrapWidth += 0.7
            runText.draw()
            self.win.flip()
            # Check keys, play sounds and then perform resulting actions
            self.current.volume = self.vol
            action = self.check_keys(self.current.sound)
            action()

    def cleanQuit(self):
        """Cleanly quit psychopy and run any internal cleanup"""
        # Finalising data writing etc
        # these shouldn't be strictly necessary (should auto-save)
        results = pd.DataFrame.from_dict(self.marked, orient='index')
        results.to_csv(self.filename+'.csv')
        logging.flush()
        # make sure everything is closed down
        self.win.close()
        core.quit()

    def run(self, debug=False):
        """Run the whole experiment"""
        # Setup
        self.buildStimuli()

        self.runInstructions()
        self.runCalibration()

        self.cleanQuit()


if __name__ == '__main__':
    exp = Calibration()
    exp.run()
