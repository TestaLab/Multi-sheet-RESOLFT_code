import serial
import time
import sys
import glob
import numpy as np

#open the port...
tgCom = 'COM12'
tgS = serial.Serial()
tgS.port = tgCom
tgS.baudrate = 115200
tgS.bytesize = serial.EIGHTBITS  # number of bits per bytes
tgS.parity = serial.PARITY_NONE  # set parity check: no parity
tgS.stopbits = serial.STOPBITS_ONE  # number of stop bits
# tgS.timeout = None          #block read
tgS.timeout = 0.5  # non-block read
tgS.xonxoff = False  # disable software flow control
tgS.rtscts = False  # disable hardware (RTS/CTS) flow control
tgS.dsrdtr = False  # disable hardware (DSR/DTR) flow control
tgS.writeTimeout = 0  # timeout for write

try:
    print("Activating Triggerscope...")
    tgS.open()
except Exception as e:
    print("ERROR: Triggerscope Com port NOT OPEN: " + str(e))
    exit()
if tgS.isOpen():
    try:
        tgS.flushInput()  # flush input buffer, discarding all its contents
        tgS.flushOutput()  # flush output buffer, aborting current output
        op = "*"
        tgS.write(op.encode() + "\n".encode('ascii'))  # send an ack to tgs to make sure it's up
        time.sleep(0.2)  # give the serial port sometime to receive the data
        print("Rx: " + tgS.readline().decode())
    except Exception as e1:
        print(" serial communication error...: " + str(e1))

else:
    print("cannot open tg cell  port ")


#functions below each perform a sample experiment as documented in the command syntax documentation

#this command performs a write
def writetgs(tgin):
    '''send a serial command to the triggerscope...
    Args:
        tgin: input string to send. Note the command terminator should be included in the string.
    Returns:
        char string of whatever comes back on the serial line.
    Raises:
        none.
    '''
    tgS.flushInput()  # flush input buffer, discarding all its contents
    tgS.flushOutput()  # flush output buffer, aborting current output
    tgS.write(tgin.encode())  # send command
    time.sleep(0.01)  # give the serial port sometime to receive the data 50ms works well...
    bufa = ''
    l = None
    while l != '':
        l = tgS.readline().decode()
        bufa += l
        time.sleep(0.001)
    return bufa


def setScanPars():
    setParameter('dimOneChan', 1)
    setParameter('dimOneStartV', 0)
    setParameter('dimOneLenV', 2)
    setParameter('dimOneStepSizeV', 0.1)
    setParameter('dimTwoChan', 3)
    setParameter('dimTwoStartV', 0)
    setParameter('dimTwoLenV', 0)
    setParameter('dimTwoStepSizeV', 0)
    setParameter('dimThreeChan', 5)
    setParameter('dimThreeStartV', 0)
    setParameter('dimThreeLenV', 1)
    setParameter('dimThreeStepSizeV',0.1)
    setParameter('dimFourChan', 6)
    setParameter('dimFourStartV', 0)
    setParameter('dimFourLenV', 1)
    setParameter('dimFourStepSizeV', 0.1)
    setParameter('settlingTimeUs', 1)
    setParameter('dwellTimeUs', 1)
    setParameter('angleRad', np.deg2rad(0))

def setPixelCyclePars():
    setParameter('sequenceTimeUs', 10000)
    setParameter('p1Line', 0)
    setParameter('p1StartUs', 0)
    setParameter('p1EndUs', 1500)
    setParameter('p2Line', 1)
    setParameter('p2StartUs', 2000)
    setParameter('p2EndUs', 3000)
    setParameter('p3Line', 2)
    setParameter('p3StartUs', 3500)
    setParameter('p3EndUs', 5000)

def setpLSRParameters():
    setParameter('onLaserTTLChan', 0)
    setParameter('offLaserTTLChan', 2)
    setParameter('roLaserTTLChan', 5)
    setParameter('roScanDACChan', 0)
    setParameter('cycleScanDACChan', 2)

    setParameter('onPulseTimeUs', 1000)
    setParameter('delayAfterOnUs', 500)
    setParameter('offPulseTimeUs', 1000)
    setParameter('delayAfterOffUs', 400)
    setParameter('delayAfterDACStepUs', 2000)
    setParameter('roPulseTimeUs', 1500)
    setParameter('roRestingV', 0)
    setParameter('roStartV', -0.5)
    setParameter('roStepSizeV', 0.1)
    setParameter('roSteps', 20)
    setParameter('cycleStartV', 0)
    setParameter('cycleStepSizeV', 0.2)
    setParameter('cycleSteps', 5)

def runpLSRScan():
    print(writetgs('pLS-RESOLFT_SCAN\n'))

def runRasterScan():
    print(writetgs('RASTER_SCAN\n'))

def setParameter(name, value):
    msg = 'PARAMETER,' + name + ',' + str(value) + '\n'
    print(writetgs(msg))