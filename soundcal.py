#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created by Gavin Cooper for Gavin Cooper.
University of Newcastle
2016
"""
# Imports
from __future__ import division, print_function
from psychopy import visual, core, data, event, logging, gui, sound, parallel
import csv
import os  # handy system and path functions
import sys
from itertools import izip, chain
from collections import defaultdict
import matplotlib.pyplot as plt
import pandas as pd
import ast


def readSounds(soundfile):
    """Read and parse the sounds.csv file"""
    with open(soundfile) as soundfile:
        soundreader = csv.DictReader(soundfile)
        for row in soundreader:
            row['PortCode'] = int(row['PortCode'])
            row['Frequency'] = ast.literal_eval(row['Frequency'])
            yield row


def graphCumulativePercent(*data):
    """create plot of cumulative % correct, save to disk and return filename"""
    with NamedTemporaryFile(delete=False, suffix='.png') as figfile:
        for label, df in data:
            df['CumPercent'].plot(label=label)
        plt.legend()
        plt.savefig(figfile)
        plt.close()
    return figfile.name


class Calibration(object):
    """Holds all experiment details such as implementation, run data (date etc)
    and creates resources like file descriptors and display adapters"""
    def __init__(self, name='Calibration'):
        """Setup the experiment, create windows and gather subject details"""
        super(Experiment, self).__init__()
        self.subject = {'Subject ID': ''}
        self.date = data.getDateStr()
        self.name = name
        self.sounds = gui.fileOpenDlg(prompt=u'Select sound file specs to run')
        self._filehandling()
        self._hwsetup()

    def _filehandling(self):
        """Create file paths, setup logging, change working directories"""
        # Ensure that relative paths start from the same directory as script
        _thisDir = os.path.dirname(os.path.abspath(__file__)).decode(
            sys.getfilesystemencoding())
        os.chdir(_thisDir)
        # Create base output filename
        filestruct = '{{0.sounds}_{0.name}_{0.date}'.format(self)
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
        if self.frameRate is not None:
            self.frameDur = 1.0/round(self.frameRate)
        else:
            self.frameDur = 1.0/60.0  # couldn't get a reliable measure/guess
        # Set up the sound card
        sound.init(rate=48000, stereo=True, buffer=256)
        self.volume = 0.4
        # Create some handy timers
        self.clock = core.Clock()  # to track the time since experiment started
        # Create a parallel port handler
        self.port = parallel.ParallelPort(address=0x0378)

    def buildStimuli(self):
        """Build individual stimuli for use in the experiment"""
        self.stimuli = dict()

        # Initialize components for Routine "TDTInstructions"
        self.defaulttext = dict(font='Arial', height=0.1, alignHoriz='center')

        self.soundlist = list(readSounds())
        self.generated_sounds=dict()


    def runInstructions(self):
        """Present the instructions"""
        itext = '''
        This task will present sounds to be measured. The keys
        to use will be as follows:
            ← - go to previous sound
            → - go to next sound
            ↓ - change volume down
            ↑ - change volume up
            i - change volume increment (0.1, 0.01, 0.001)
            m - mark volume as correct
            p - plot results
            Escape - quits
        Press any key to continue
        '''
        instruction = visual.TextStim(win=self.win, name='InstrText',
                                      text=itext, **self.defaulttext)
        instruction.draw()
        self.win.flip()
        while True:
            theseKeys = event.getKeys()
            if theseKeys:
                break

    def getSound(self, freq, dur):
        """return a pre-made sound, or generate and return"""
        try:
            return self.generated_sounds[(freq, dur)]
        except KeyError:
            newSound = sound.Sound(value=freq, secs=dur)
            self.generated_sounds[(freq, dur)] = newSound
            return newSound

    def check_keys(self, sound=None)
        event.clearEvents()
        repeatTimer = core.CountdownClock(1.5)
        keymap = {'left':self.previous,
                  'right':self.next,
                  'up':self.increase,
                  'down':self.decrease,
                  'i':self.toggleinc,
                  'm':self.mark,
                  'p':self.plot,
                  'escape'self.cleanQuit}
        while True:
            if repeatTimer < 0:
                sound.play()
                repeatTimer.reset()
            theseKeys = event.getKeys(keyList=keys)
            if len(theseKeys) > 0:  # at least one key was pressed
                # grab just the first key pressed
                key = theseKeys[0]
                # perform action
                keymap[key]()

    def getCurrentData(self):
        """Grab all data to date from the ExperimentHandler"""
        data = pd.DataFrame(self.handler.entries)
        data.dropna(subset=['Description'], inplace=True)
        data['Ones'] = 1
        grouped_data = data.groupby('Length')
        data['CumCorr'] = grouped_data['Correct'].cumsum()
        data['CumCount'] = grouped_data['Ones'].cumsum()
        data['CumPercent'] = data['CumCorr']/data['CumCount']
        return grouped_data, data['Correct'].mean()

    def plot(self):
        """Show feedback for the block"""
        gdata, meanCorrect = self.getCurrentData()
        fbtxt = 'Total Percent Correct so far is {}'.format(meanCorrect)
        feedback = visual.TextStim(win=self.win, name='Feedback',
                                   text=fbtxt, pos=(0.0, -0.5),
                                   **self.defaulttext)
        graphname = graphCumulativePercent(gdata)
        fbgraph = visual.ImageStim(win=self.win, image=graphname,
                                   pos=(0.0, 0.5), name='Graph')
        feedback.draw()
        fbgraph.draw()
        self.win.flip()
        self.handler.addData('Message', 'Feedback')
        self.handler.addData('Timestamp', self.clock.getTime())
        displayTimeClock = core.CountdownTimer(block['Feedback'])
        while displayTimeClock.getTime() > 0:
            theseKeys = event.getKeys()
            if 'escape' in theseKeys:
                self.cleanQuit()

    def doBreak(self, block):
        """Show the break/countdown text"""
        onesecondTimer = core.CountdownTimer(1)
        if block['Break']:
            breakTimer = core.CountdownTimer(block['Break'])
            brtxt = ('5 MINUTE BREAK\n',
                     'Feel free to have a stretch and wiggle.\n',
                     'If you need anything, please ask the researcher.')
            breakText = visual.TextStim(win=self.win, name='Feedback',
                                        text=brtxt, **self.defaulttext)
            breakText.draw()
            self.win.flip()
            while breakTimer.getTime() > 0:
                theseKeys = event.getKeys()
                if 'escape' in theseKeys:
                    self.cleanQuit()
        for n in reversed(xrange(block['Countdown'])):
            countdownText = visual.TextStim(win=self.win, name='Countdown',
                                            text=str(n+1), **self.defaulttext)
            countdownText.draw()
            self.win.flip()
            onesecondTimer.reset()
            while onesecondTimer.getTime() > 0:
                theseKeys = event.getKeys()
                if 'escape' in theseKeys:
                    self.cleanQuit()

    def runTask(self):
        """Create a Quest staircase and run the tasks from blocks.csv"""
        sd = self.stimuli['init_large_dur'] - self.stimuli['short_dur']
        minVal = self.stimuli['short_dur']
        maxVal = self.stimuli['init_large_dur'] + sd
        staircase = data.QuestHandler(
            self.stimuli['init_large_dur'], sd, pThreshold=0.75,
            method='quantile', ntrials=800, minVal=minVal, maxVal=maxVal,
            range=maxVal-minVal)
        # add the loop to the experiment and initialise some vals
        self.handler.addLoop(staircase)
        # Draw our screen now
        self.stimuli['fixation'].draw()
        self.win.flip()
        soaClock = core.CountdownTimer(self.soa)
        keyClock = core.Clock()
        short = self.stimuli['short_dur']
        keymatch = {'long': {'left': 0, 'right': 1},
                    'short': {'left': 1, 'right': 0}}

        for block_cntr, block in enumerate(self.blocks, 1):
            self.send_code(code=254)
            for stimulus in block['Sequence']:
                sndlength = stimulus['Length']
                dur = staircase.next() if sndlength == 'long' else short
                freq = stimulus['Frequency']
                thisSound = self.getSound(freq, dur)
                self.handler.addData('Block', block_cntr)
                self.handler.addData('Duration', dur)
                for key, val in stimulus.items():
                    self.handler.addData(key, val)
                thisSound.setVolume(self.stimuli['volume'])
                while soaClock.getTime() > 0:
                    timeleft = soaClock.getTime()
                    if timeleft > 0.2:
                        core.wait(timeleft-0.2, hogCPUperiod=0.2)

                keyClock.reset()
                soaClock.reset()  # clock
                self.handler.addData('Timestamp', self.clock.getTime())
                thisSound.play()
                self.send_code(stimulus=stimulus)

                # Check for a response
                resp = self.check_keys(timer=keyClock,
                                       keymap=keymatch[sndlength])
                for key, val in resp.items():
                    self.handler.addData(key, val)
                if sndlength == 'long':
                    staircase.addResponse(resp['Correct'])

                self.handler.nextEntry()
            self.send_code(code=255)
            self.showFeedback(block)
            self.doBreak(block)
        # staircase completed
        staircase.printAsText()

    def runThanks(self):
        """Present the Thank you screen"""
        self.stimuli['thanksText'].draw()
        self.win.flip()
        starttime = self.clock.getTime()
        while True:
            theseKeys = event.getKeys()
            if 'escape' in theseKeys:
                self.cleanQuit()
            elif theseKeys:
                if self.clock.getTime() - starttime > 0.5:
                    break
        # store data for thisExp (ExperimentHandler)
        self.handler.addData('Message', 'ThankYou')
        self.handler.addData('Timestamp', self.clock.getTime())
        self.handler.nextEntry()

    def cleanQuit(self):
        """Cleanly quit psychopy and run any internal cleanup"""
        # Finalising data writing etc
        # these shouldn't be strictly necessary (should auto-save)
        self.handler.saveAsWideText(self.filename+'.csv')
        self.handler.saveAsPickle(self.filename)
        logging.flush()
        # make sure everything is closed down
        self.handler.abort()  # or data files will save again on exit
        self.win.close()
        core.quit()
        for tf in self.tempfiles:
            os.remove(tf)

    def run(self, debug=False):
        """Run the whole experiment"""
        # Setup
        self.buildStimuli()
        self.buildSequences()

        if debug:
            debugSequences(self)

        self.runInstructions()
        self.runTask()
        self.runThanks()

        self.cleanQuit()


if __name__ == '__main__':
    exp = Experiment()
    exp.run(debug=True)
