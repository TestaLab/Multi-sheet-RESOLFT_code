import os
import configparser
from ast import literal_eval
from ..basecontrollers import ImConWidgetController
from imswitch.imcommon.model import dirtools
import numpy as np

from imswitch.imcontrol.view import guitools
from imswitch.imcommon.view.guitools import colorutils

class TriggerScopeController(ImConWidgetController):
    """ Linked to TriggerScopeWidget."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._master.triggerScopeManager.sigScanDone.connect(self.scanDone)


        #Calibration values
        self.scan_nm2VFactor = 5.26316e-6

        # Connect PositionerWidget signals
        self._widget.sigRunScanClicked.connect(self.run)
        self._widget.sigSaveScanClicked.connect(self.saveScan)
        self._widget.sigLoadScanClicked.connect(self.loadScan)
        self._widget.sigPosParameterChanged.connect(self.changePosition)
        self._widget.sigPosIncrementChanged.connect(self.changeIncrement)

        self.scanDir = os.path.join(dirtools.UserFileDirs.Root, 'imcontrol_TS_scans')

        self.scanParameters = {'Step size [nm]': None,
                               'Number of steps': None,
                               'TTL time': None,
                               'Step time': None,
                               'Repetitions': None}

        self.positioners = {
            pName: pManager for pName, pManager in self._setupInfo.positioners.items()
            if pManager.forScanning
        }

        self.TTLDevices = self._setupInfo.getTTLDevices()

        self._widget.initControls(
            self.positioners.keys(),
            self.TTLDevices.keys(),
            self._master.scanManager.TTLTimeUnits
        )

        self._widget.sigSeqTimeParChanged.connect(self.plotSignalGraph)
        self._widget.sigSignalParChanged.connect(self.plotSignalGraph)

    def changeIncrement(self, positionerName):
        pass
    def changePosition(self, positionerName):
        pass
        # self._master.triggerScopeManager.sendAnalog(1, self.scan_nm2VFactor * newPosition)

    def getParameters(self):
        self.scanParameters['Step size [nm]'] = self._widget.stepSizeEdit.value()
        self.scanParameters['Number of steps'] = self._widget.nrOfStepsEdit.value()
        self.scanParameters['TTL time'] = self._widget.TTLtimeEdit.value()
        self.scanParameters['Step time'] = self._widget.stepTimeEdit.value()
        self.scanParameters['Repetitions'] = self._widget.repEdit.value()

    def setParameters(self):
        self._widget.stepSizeEdit.setValue(self.scanParameters['Step size [nm]'])
        self._widget.nrOfStepsEdit.setValue(self.scanParameters['Number of steps'])
        self._widget.TTLtimeEdit.setValue(self.scanParameters['TTL time'])
        self._widget.stepTimeEdit.setValue(self.scanParameters['Step time'])
        self._widget.repEdit.setValue(self.scanParameters['Repetitions'])

    def run(self):
        self._widget.setRunButtonChecked(True)
        self._commChannel.sigScanStarting.emit()

        self.getParameters()

        currentV = self.scan_nm2VFactor * self._widget.positionEdit.value()
        stepsSizeV = self.scan_nm2VFactor * self.scanParameters['Step size [nm]']
        steps = self.scanParameters['Number of steps']
        stepTime = self.scanParameters['Step time']
        TTLTime = self.scanParameters['TTL time']
        repetitions = self.scanParameters['Repetitions']

        finalV = currentV + steps * stepsSizeV
        dacarray = np.linspace(currentV, finalV, steps)
        ttlarray = np.ones(steps, dtype=int)


        params = self.setParams(1, 1, len(dacarray), 0, stepTime, TTLTime, repetitions)
        self._master.triggerScopeManager.run_wave(dacarray, ttlarray, params)

    def scanDone(self):
        self._logger.debug('Scan ended in TrScController')
        self._commChannel.sigScanEnded.emit()
        self._widget.setRunButtonChecked(False)

    def loadScan(self):
        fileName = guitools.askForFilePath(self._widget, 'Load scan', self.scanDir)
        if not fileName:
            return

        self.loadScanParamsFromFile(fileName)

    def loadScanParamsFromFile(self, filePath: str) -> None:
        """ Loads scanning parameters from the specified file. """

        config = configparser.ConfigParser()
        config.optionxform = str

        config.read(filePath)

        for key in self.scanParameters:
            self.scanParameters[key] = literal_eval(
                config._sections['snoutyScanParameterDict'][key]
            )

        self.setParameters()

    def saveScan(self):
        fileName = guitools.askForFilePath(self._widget, 'Save scan', self.scanDir, isSaving=True)
        if not fileName:
            return

        self.saveScanParamsToFile(fileName)

    def saveScanParamsToFile(self, filePath: str) -> None:
        """ Saves the set scanning parameters to the specified file. """
        self.getParameters()
        config = configparser.ConfigParser()
        config.optionxform = str

        config['snoutyScanParameterDict'] = self.scanParameters

        with open(filePath, 'w') as configfile:
            config.write(configfile)

    def setParams(self, analogLine, digitalLine, length, trigMode, delayDAC, delayTTL, reps):
        params = dict([])
        params["analogLine"] = analogLine
        params["digitalLine"] = digitalLine
        params["length"] = length
        params["trigMode"] = trigMode
        params["delayDAC"] = delayDAC
        params["delayTTL"] = delayTTL
        params["reps"] = reps
        return params


    def plotSignalGraph(self):

        dwellTime = float(self._widget.seqTimePar.text())
        graphSamples = 10000

        areas = []
        signals = []
        colors = []
        for deviceName in self.TTLDevices.keys():
            isLaser = deviceName in self._setupInfo.lasers
            x = np.linspace(0, dwellTime, graphSamples)
            signal = np.zeros(graphSamples)
            try:
                start = float(self._widget.pxParameters['sta' + deviceName].text())
                end = float(self._widget.pxParameters['end' + deviceName].text())
                signal[x > start] = 1
                signal[x > end] = 0
            except ValueError:
                pass
            areas.append(x)
            signals.append(signal)
            colors.append(
                colorutils.wavelengthToHex(
                    self._setupInfo.lasers[deviceName].wavelength
                ) if isLaser else '#ffffff'
            )
        self._widget.plotSignalGraph(areas, signals, colors)
