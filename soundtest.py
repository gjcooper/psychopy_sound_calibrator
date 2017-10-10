#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created by Gavin Cooper for Gavin Cooper.
University of Newcastle
2016
"""
# Imports
from __future__ import division, print_function
from psychopy import prefs
prefs.general['audioLib'] = ['sounddevice', 'pyo', 'pygame']  # noqa E402
prefs.general['audiodevice'] = u'SB Audigy 2 ZS Audio [B000]'  # noqa E402
from psychopy import visual, core, data, event, logging, gui, sound, parallel
from psychopy.constants import PLAYING
import csv
import os  # handy system and path functions
import sys
import pandas as pd
from numpy import linspace
import ast

volume = 0.2


class SoundSpec(object):
    def __init__(self):
        self._sound = None
        self.volume = volume

    @property
    def sound(self):
        """return a sound if it exists, otherwise generate and return it"""
        if self._sound:
            return self._sound
        self._generate()
        return self._sound


class SoundFromSpec(SoundSpec):
    '''Holds a sound specification and returns a psychopy sound object when
    queried'''
    def __init__(self, specification=None):
        """One and only one of filename or specification must be not None"""
        super(SoundFromSpec, self).__init__()
        self.freq = specification['Frequency']
        self.dur = float(specification['Length'])
        self.repeats = int(specification['Repeats'])

    def _generate(self):
        self._sound = sound.Sound(value=self.freq, secs=self.dur,
                                  volume=volume)

    def __eq__(self, other):
        if not isinstance(other, SoundFromSpec):
            return NotImplemented
        return (self.freq == other.freq and
                self.dur == other.dur and
                self.repeats == other.repeats)

    def __hash__(self):
        return hash((self.freq, self.dur, self.repeats))

    def __str__(self):
        return 'Freq:({0.freq}), Duration:({0.dur})'.format(self)


class SoundFromFile(SoundSpec):
    '''Holds a sound file and generates psychopy sound object as needed'''
    def __init__(self, filename=None, repeats=None):
        super(SoundFromFile, self).__init__()
        self.filename = filename
        self.repeats = int(repeats)

    def _generate(self):
        self._sound = sound.Sound(value=self.filename, volume=volume)

    def __eq__(self, other):
        if not isinstance(other, SoundFromFile):
            return NotImplemented
        return (self.filename == other.filename and
                self.repeats == other.repeats)

    def __hash__(self):
        return hash((self.filename, self.repeats))

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


class SoundTest(object):
    """Holds all experiment details such as implementation, run data (date etc)
    and creates resources like file descriptors and display adapters"""
    def __init__(self, name='Calibration'):
        """Setup the experiment, create windows and gather subject details"""
        super(SoundTest, self).__init__()
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
                            title='Enter number of repeats per file - CSV for > 1')

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
        # An ExperimentHandler isn't essential but helps with data saving
        self.handler = data.ExperimentHandler(name=self.name,
                                              dataFileName=self.filename)

    def _hwsetup(self):
        """Set up hardware like displays, sounds, etc"""
        self.win = visual.Window(size=(1280, 1024), fullscr=True,
                                 allowGUI=False, useFBO=True,
                                 monitor='testMonitor', units='norm')
        # store frame rate of monitor if we can measure it successfully
        self.frameRate = self.win.getActualFrameRate()
        # Create a parallel port handler
        self.port = parallel.ParallelPort(address=0x0378)
        self.clock = core.Clock()  # to track the time since experiment started
        if self.frameRate is not None:
            self.frameDur = 1.0/round(self.frameRate)
        else:
            self.frameDur = 1.0/60.0  # couldn't get a reliable measure/guess
        # Set up the sound card
        sound.init(rate=48000, stereo=True, buffer=256)

    def send_code(self, code=1, duration=0.005, stimulus=None):
        """Send a code and clear it after duration, use code from stimulus if
        it exists"""
        if stimulus:
            self.port.setData(stimulus['PortCode'])
        else:
            self.port.setData(code)
        core.wait(duration)
        self.port.setData(0)

    def buildStimuli(self):
        """Build individual stimuli for use in the experiment"""
        # Initialize components for Routine "TDTInstructions"
        self.defaulttext = dict(font='Arial', height=0.05, alignHoriz='center')

        self.sounds = []
        for filename, repeats in self.readSounds.items():
            self.sounds.append(SoundFromFile(filename=filename, repeats=repeats))

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
        It expects a special cable from parallel and sound output to another
        PC's sound input to record pulses and outputted sound.
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

    @property
    def current(self):
        """Return current sound"""
        return self.sounds[self.idx]

    def runSoundtest(self):
        '''Run through all sounds to check timing'''
        rtext = u'''
        Timing test in progress
        '''
        runText = visual.TextStim(win=self.win, name='RunText',
                                  text=rtext, **self.defaulttext)
        runText.wrapWidth += 0.7
        runText.draw()
        self.win.flip()
        for snd in self.sounds:
            for rep in range(snd.repeats):
                print(rep)
                self.handler.addData('Snd', rep)
                self.handler.addData('Timestamp', self.clock.getTime())
                snd.sound.play()
                self.send_code()
                while (snd.sound.status == PLAYING):
                    pass
                core.wait(0.05)
            print('Snd' + str(snd))

    def cleanQuit(self):
        """Cleanly quit psychopy and run any internal cleanup"""
        # Finalising data writing etc
        # these shouldn't be strictly necessary (should auto-save)
        logging.flush()
        # make sure everything is closed down
        self.win.close()
        core.quit()

    def run(self, debug=False):
        """Run the whole experiment"""
        # Setup
        self.buildStimuli()

        self.runInstructions()
        self.runSoundtest()

        self.cleanQuit()


if __name__ == '__main__':
    exp = SoundTest()
    exp.run()
