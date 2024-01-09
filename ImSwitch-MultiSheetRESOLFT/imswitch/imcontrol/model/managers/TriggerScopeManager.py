from imswitch.imcommon.model import initLogger
import numpy as np
from imswitch.imcommon.framework import Signal, SignalInterface, Timer, Thread, Worker
from pyvisa.errors import VisaIOError, InvalidSession
from serial.serialutil import SerialException
import time

class TriggerScopeManager(SignalInterface):
    """ For interaction with TriggerScope hardware interfaces. """
    sigScanDone = Signal()
    sigScanStarted = Signal()

    def __init__(self, setupInfo, rs232sManager):
        super().__init__()

        self.__setupInfo = setupInfo
        daqInfo = self.__setupInfo.daq
        self._rs232manager = rs232sManager[
            daqInfo.managerProperties['rs232device']
        ]
        #Set timeout value for reading
        self._rs232manager.setTimeout(100000)

        self.__logger = initLogger(self)
        self.send("*")

        self._serialMonitor = SerialMonitor(self._rs232manager, 5)
        self._thread = Thread()
        self._serialMonitor.moveToThread(self._thread)
        self._thread.started.connect(self._serialMonitor.run)
        self._thread.finished.connect(self._serialMonitor.stop)
        self._thread.start()
        self._monitoring = True

        self._deviceInfo = {}
        self.__logger.debug('All devices: ' + str(setupInfo.getAllDevices()))
        for targetName, targetInfo in setupInfo.getAllDevices().items():
            analogChannel = targetInfo.getAnalogChannel()
            digitalLine = targetInfo.getDigitalLine()
            if analogChannel is not None:
                dev, chan = analogChannel.split('/')
                if dev == 'Triggerscope' and chan[0:3] == 'DAC':
                    chanNr = chan[-1]
                    self._deviceInfo.update({targetName: {'DACChannel': chanNr,
                                                          'MinV': targetInfo.managerProperties['minVolt'],
                                                          'MaxV': targetInfo.managerProperties['maxVolt']}})
            if digitalLine is not None:
                dev, line = digitalLine.split('/')
                if dev == 'Triggerscope' and line[0:3] == 'TTL':
                    lineNr = line[-1]
                    if targetName in self._deviceInfo.keys():
                        self._deviceInfo[targetName].update({'TTLLine': lineNr})
                    else:
                        self._deviceInfo.update({targetName: {'TTLLine': lineNr}})

        self.setParSleepTime = 0.05

        #Connect signals from serialMonitor
        self._serialMonitor.sigScanDone.connect(self.sigScanDone)
        self._serialMonitor.sigUnknownMessage.connect(self.unknownMsg)

    def __del__(self):
        self._thread.quit()
        self._thread.wait()
        if hasattr(super(), '__del__'):
            super().__del__()

    def unknownMsg(self, msg):
        self.__logger.info('[Triggerscope serial] ' + msg)

    def setParameter(self, parameterName, parameterValue):
        msg = 'PARAMETER,' + parameterName + ',' + str(parameterValue) + '\n'
        self.send(msg)
        time.sleep(self.setParSleepTime)

    def send(self, command):
        self._rs232manager.write(command)

    def runScan(self, parameterDict, type=None):
        self.__logger.debug('Running scan with parameters: ' + str(parameterDict))

        if type == 'rasterScan':
            self.runRasterScan(parameterDict)
        elif type == 'pLS-RESOLFTScan':
            self.runpLSRESOLFTScan(parameterDict)
        else:
            self.__logger.info('Unknown scan type')

    def runpLSRESOLFTScan(self, pLSRESOLFTScanParameters):
        deviceParameters = pLSRESOLFTScanParameters['deviceParameters']

        onLaserTTLLine = self._deviceInfo[deviceParameters['onLaser']]['TTLLine']
        offLaserTTLLine = self._deviceInfo[deviceParameters['offLaser']]['TTLLine']
        roLaserTTLLine = self._deviceInfo[deviceParameters['roLaser']]['TTLLine']
        roScanDACChan = self._deviceInfo[deviceParameters['roScanDevice']]['DACChannel']
        cycleScanDACChan = self._deviceInfo[deviceParameters['cycleScanDevice']]['DACChannel']

        self.setParameter('onLaserTTLChan', onLaserTTLLine)
        self.setParameter('offLaserTTLChan', offLaserTTLLine)
        self.setParameter('roLaserTTLChan', roLaserTTLLine)
        self.setParameter('roScanDACChan', roScanDACChan)
        self.setParameter('cycleScanDACChan', cycleScanDACChan)

        scanParameters = pLSRESOLFTScanParameters['scanParameters']

        for key, value in scanParameters.items():
            self.setParameter(key, value)


        self.__logger.debug('Parameters set')
        self.send('pLS-RESOLFT_SCAN')
        self.sigScanStarted.emit()

    def runRasterScan(self, rasterScanParameters):
        seqTime = rasterScanParameters['Digital']['sequence_time']
        self.setParameter('sequenceTimeUs', int(seqTime * 1e6))

        startTimes = rasterScanParameters['Digital']['TTL_start']
        if len(startTimes) > 0:
            endTimes = rasterScanParameters['Digital']['TTL_end']
            firstStart = np.min(startTimes)
            firstIndex = startTimes.index(firstStart)
            endOfPulse = endTimes[firstIndex]
            firstPulseTarget = rasterScanParameters['Digital']['target_device'][firstIndex]
            firstPulseLine = self._deviceInfo[firstPulseTarget]['TTLLine']

            self.setParameter('p1Line', int(firstPulseLine))
            self.setParameter('p1StartUs', int(firstStart * 1e6))
            self.setParameter('p1EndUs', int(endOfPulse * 1e6))

        self.__logger.debug('Setting parameters')
        try:
            chan = self._deviceInfo[rasterScanParameters['Analog']['targets'][0]]['DACChannel']
            self.setParameter('dimOneChan', chan)
            self.setParameter('dimOneStartV', rasterScanParameters['Analog']['startPos'][0])
            self.setParameter('dimOneLenV', rasterScanParameters['Analog']['lengths'][0])
            self.setParameter('dimOneStepSizeV', rasterScanParameters['Analog']['stepSizes'][0])
        except IndexError:
            pass
        try:
            chan = self._deviceInfo[rasterScanParameters['Analog']['targets'][1]]['DACChannel']
            self.setParameter('dimTwoChan', chan)
            self.setParameter('dimTwoStartV', rasterScanParameters['Analog']['startPos'][1])
            self.setParameter('dimTwoLenV', rasterScanParameters['Analog']['lengths'][1])
            self.setParameter('dimTwoStepSizeV', rasterScanParameters['Analog']['stepSizes'][1])
        except IndexError:
            pass
        try:
            chan = self._deviceInfo[rasterScanParameters['Analog']['targets'][2]]['DACChannel']
            self.setParameter('dimThreeChan', chan)
            self.setParameter('dimThreeStartV', rasterScanParameters['Analog']['startPos'][2])
            self.setParameter('dimThreeLenV', rasterScanParameters['Analog']['lengths'][2])
            self.setParameter('dimThreeStepSizeV', rasterScanParameters['Analog']['stepSizes'][2])
        except IndexError:
            pass
        try:
            chan = self._deviceInfo[rasterScanParameters['Analog']['targets'][3]]['DACChannel']
            self.setParameter('dimFourChan', chan)
            self.setParameter('dimFourStartV', rasterScanParameters['Analog']['startPos'][3])
            self.setParameter('dimFourLenV', rasterScanParameters['Analog']['lengths'][3])
            self.setParameter('dimFourStepSizeV', rasterScanParameters['Analog']['stepSizes'][3])
        except IndexError:
            pass
        self.setParameter('angleRad', np.deg2rad(0))
        self.__logger.debug('Parameters set')

        self.send('RASTER_SCAN')

        self.sigScanStarted.emit()

    def sendAnalog(self, dacLine, value):
        self.send("DAC" + str(dacLine) + "," + str(((value+5)/10)*65535), 0)

    def sendTTL(self, ttlLine, value):
        self.send("TTL" + str(ttlLine) + "," + str(value), 0)

    def setDigital(self, target, booleanValue):
        msg = 'TTL' + str(self._deviceInfo[target]['Channel']) + ',' + str(booleanValue)
        self.send(msg)

    def setAnalog(self, target, voltage):

        if self._deviceInfo[target]['MinV'] <= voltage <= self._deviceInfo[target]['MaxV']:
            msg = 'DAC' + str(self._deviceInfo[target]['DACChannel']) + ',' + str(voltage)
            self.send(msg)
        else:
            self.__logger.warning('Trying to set Triggerscope voltage outside allowed range')

    def closeMonitor(self):
        if self._monitoring:
            self._thread.quit()
            self._monitoring = False



class SerialMonitor(Worker):
    sigScanDone = Signal()
    sigTrigMSG = Signal(int)
    sigUnknownMessage = Signal(str)

    def __init__(self, rs232Manager, updatePeriod):
        super().__init__()

        self._rs232Manager = rs232Manager
        self._updatePeriod = updatePeriod
        self._vtimer = None

    def run(self):
        self._vtimer = Timer()
        self._vtimer.timeout.connect(self.checkSerial)
        self._vtimer.start(self._updatePeriod)

    def stop(self):
        if self._vtimer is not None:
            self._vtimer.stop()
        self._rs232Manager.finalize()

    def checkSerial(self):

        try:
            msg = self._rs232Manager.read(termination='\r\n')
        except (VisaIOError, InvalidSession, SerialException, TypeError):
            msg = None

        #Check content of message
        if msg != None:
            if msg == 'Scan done':
                self.sigScanDone.emit()
            elif msg[:3] == 'MSG':
                msgID = int(msg[3:])
                self.sigTrigMSG.emit(msgID)
            else:
                self.sigUnknownMessage.emit(msg)

