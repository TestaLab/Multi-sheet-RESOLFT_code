from thorlabs_apt_device.devices.bsc import BSC
from qtpy import QtCore
from ..basecontrollers import ImConWidgetController
from serial.serialutil import SerialException

"""If motors freak out, open the Kinesis software and make sure the device is set to HS NanoMax 300 X/Y/Z"""

"""
Windows Only: Enable Virtual COM Port¶
On Windows, the virtual serial communications port (VCP) may need to be enabled in the driver options for the USB 
interface device. First, open the Windows Device Manager. If plugging in the controller causes a new COM device to 
appear under the “Ports (COM & LPT)” section, then there is nothing more to do. If a new COM device does not appear, 
then find the controller device under “Universal Serial Bus Controllers”, it may be called “Thorlabs APT Controller” 
or similar (see what new device appears when plugging in the controller). Right-click->Properties->Advanced tab, check 
the “Load VCP” box, then OK out of the dialog back to the device manager. Unplug and re-plug the USB connection to the 
controller, and ensure than a new COM device now appears.
"""

"""
Note that the bay-type devices such as BBD and BSCs are referred to as a x-channel controllers, but the actual device 
layout is that the controller is a “rack” system with three bays, where x number of single-channel controller cards may 
be installed. In other words, the BBD203 “3 channel” controller actually has 3 populated bays 
(bays=(EndPoint.BAY0, EndPoint.BAY1, EndPoint.BAY2)), each of which only controls a single channel (channels=(1,)).
"""


"""
From manual of thorlabs
How to calculate the linear displacement per microstep
The stepper motor used in the DRV001 actuator has 200 full steps per revolution of the motor. Each full step is broken down into 2048 microsteps. There are
409,600 microsteps per revolution of the motor when using the BSC201 controller. The end result is the leadscrew advances by 0.5 mm. To calculate the linear
displacement of the actuator microstep, use the following:
409,600 microsteps per revolution of the lead screw
The linear displacement of the lead screw per microstep is:
0.5 mm / 409,600 = 1.2 x 10-6 mm
To calculate the linear displacment for a full step, substitute 409,600 with 200.
"""

STEPS_PER_REV = 409600
REV_PER_MM = 2


move_step_mm = 1
Xchan = 1
Ychan = 0
Zchan = 2
class BSC203Controller(ImConWidgetController):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        home = False
        port = 'COM11'
        try:
            self.dev = BSC(serial_port=port, vid=None, pid=None, manufacturer=None, product=None, serial_number=None,
                           location=None, home=home, x=3, invert_direction_logic=False, swap_limit_switches=True)
        except SerialException:
            self._logger.warning('Could not initialize NanoMax motorized stage, might not be switched on.')
            self._widget.setEnabled(False)
            return
        self.dev._log.setLevel('DEBUG')
        if home:
            self._logger.debug('Is homing')
            while self.homing():
                pass
            self._logger.debug('Finished homing')

        self.initialZPos_mm = 1
        self.initVelXY, self.initVelZ = 300, 300
        self.initAccXY, self.initAccZ = 4000, 4000
        self.initialize()
        self.getPosUpdateInterv_ms = 100

        """Mouse move variables"""
        self.initMousePos = None
        self.initMouseWheelPos = self.initialZPos_mm
        self.um_per_pixel = 10
        self.um_per_wheelStep = 1

        self._widget.XYVelEdit.setValue(self.initVelXY)
        self._widget.ZVelEdit.setValue(self.initVelZ)

        #Connect GUI signals
        self._widget.moveToBtn.clicked.connect(self.moveTo)
        self._widget.stopBtn.clicked.connect(self.stopAll)
        self._widget.XYVelEdit.editingFinished.connect(self.setXYVelocity)
        self._widget.ZVelEdit.editingFinished.connect(self.setZVelocity)
        self._widget.sigHomeAll.connect(self.homeAll)

        #Connect keyboard/mouse signals
        self._commChannel.sigKeyPressed.connect(self.keyPressed)
        self._commChannel.sigKeyReleased.connect(self.keyReleased)
        self._commChannel.sigWheelMoved.connect(self.wheelMoved)

        "Start timer"
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.getPosition_mm)
        self.timer.start(self.getPosUpdateInterv_ms)

    def homeAll(self):
        self.dev.home(bay=0)
        self.dev.home(bay=1)
        self.dev.home(bay=2)
        while self.homing():
            pass


    def homing(self):
        return not all([self.dev.status_[0][0]['homed'],
                        self.dev.status_[1][0]['homed'],
                        self.dev.status_[2][0]['homed']])

    def to_enc_steps(self, mm):
        steps = mm * REV_PER_MM * STEPS_PER_REV
        return int(steps)

    def to_mm(self, steps):
        mm = steps / (REV_PER_MM * STEPS_PER_REV)
        return mm

    def initialize(self):
        self._logger.debug('Setting initial position')
        self.dev.set_velocity_params(acceleration=4506, max_velocity=21987328 * 5, bay=0, channel=0)
        self.dev.set_velocity_params(acceleration=4506, max_velocity=21987328 * 5, bay=1, channel=0)
        self.dev.set_velocity_params(acceleration=4506, max_velocity=21987328 * 5, bay=2, channel=0)
        # self.move_absolute_mm(self.initialZPos_mm, 2)
        self.setInitialVelocity()

    def setInitialVelocity(self):
        self._logger.debug('Setting initial velocity')
        self.dev.set_velocity_params(acceleration=int(self.initAccXY / 1000 * 4506), max_velocity=int(self.initVelXY / 1000 * 21987328), bay=0, channel=0)
        self.dev.set_velocity_params(acceleration=int(self.initAccXY / 1000 * 4506), max_velocity=int(self.initVelXY / 1000 * 21987328), bay=1, channel=0)
        self.dev.set_velocity_params(acceleration=int(self.initAccZ / 1000 * 4506), max_velocity=int(self.initVelZ / 1000 * 21987328), bay=2, channel=0)

    def setVelocity(self, um_per_s, axis):
        self.dev.set_velocity_params(acceleration=4506, max_velocity=int((um_per_s * 21987328) / 1000), bay=axis, channel=0)

    def setXYVelocity(self):
        um_per_s = self._widget.XYVelEdit.value()

        self.setVelocity(um_per_s, 0)
        self.setVelocity(um_per_s, 1)
        self._logger.debug('Set XY velocity with', um_per_s)

    def setZVelocity(self):
        um_per_s = self._widget.ZVelEdit.value()
        self.setVelocity(um_per_s, 2)

    def moveTo(self):
        Xpos_mm = self._widget.setXEdit.value() / 1000
        Ypos_mm = self._widget.setYEdit.value() / 1000
        Zpos_mm = self._widget.setZEdit.value() / 1000

        self.move_absolute_mm(Xpos_mm, Xchan)
        self.move_absolute_mm(Ypos_mm, Ychan)
        self.move_absolute_mm(Zpos_mm, Zchan)

    def getPosition_mm(self):
        x, y, z = self.to_mm(self.dev.status_[Xchan][0]['position']), \
                  self.to_mm(self.dev.status_[Ychan][0]['position']), \
                  self.to_mm(self.dev.status_[Zchan][0]['position'])

        self._widget.pos0EditLabel.setText(str(x*1000))
        self._widget.pos1EditLabel.setText(str(y*1000))
        self._widget.pos2EditLabel.setText(str(z*1000))

        return [x,y,z]

    def setJogPars(self):
        size_mm = self.jogStepEdit.value() / 1000
        acc_mm = self.jogAccEdit.value()
        maxV_mm = self.jogMaxVEdit.value()
        for b in range(3):
            self.dev.set_jog_params(self.to_enc_steps(size_mm),
                                    self.to_enc_steps(acc_mm),
                                    self.to_enc_steps(maxV_mm),
                                    continuous=False,
                                    immediate_stop=False,
                                    bay=b,
                                    channel=0)

    def jog(self, direction, axis):
        self.dev.move_jog(direction=direction, bay=axis, channel=0)

    def move_relative_mm(self, distance_mm, axis):
        steps = self.to_enc_steps(distance_mm)
        self.dev.move_relative(steps, now=True, bay=axis, channel=0)

    def move_constant(self, direction, axis):
        self.dev.move_velocity(direction=direction, bay=axis, channel=0)

    def move_absolute_mm(self, position_mm, axis):
        pos = self.to_enc_steps(position_mm)
        self.dev.move_absolute(pos, now=True, bay=axis, channel=0)

    def stopAll(self):
        self._logger.debug('Stopping all movement')
        self.stop(0)
        self.stop(1)
        self.stop(2)

    def stop(self, axis):
        self.dev.stop(bay=axis)

    def moving(self):
        move_list = [self.dev.status_[0][0]['moving_forward'],
                    self.dev.status_[0][0]['moving_reverse'],
                    self.dev.status_[1][0]['moving_forward'],
                    self.dev.status_[1][0]['moving_reverse'],
                    self.dev.status_[2][0]['moving_forward'],
                    self.dev.status_[2][0]['moving_reverse']]
        if any(move_list):
            return True
        else:
            return False

    def keyPressed(self, event):
        if not event.isAutoRepeat():
            self._logger.debug('Key press detected')
            if event.key() == QtCore.Qt.Key_Right:
                print('Right key pressed')
                self.move_constant(False, Xchan)
            elif event.key() == QtCore.Qt.Key_Left:
                print('Left key pressed')
                self.move_constant(True, Xchan)
            elif event.key() == QtCore.Qt.Key_Up:
                print('Up key pressed')
                self.move_constant(True, Ychan)
            elif event.key() == QtCore.Qt.Key_Down:
                print('Down key pressed')
                self.move_constant(False, Ychan)
            elif event.key() == QtCore.Qt.Key_Q:
                print('Plus key pressed')
                self.move_constant(True, Zchan)
            elif event.key() == QtCore.Qt.Key_A:
                print('Minus key pressed')
                self.move_constant(False, Zchan)


    def keyReleased(self, event):
        if not event.isAutoRepeat():
            self._logger.debug('Key release detected')
            if (event.key() == QtCore.Qt.Key_Right or event.key() == QtCore.Qt.Key_Left):
                print('Right/Left key released')
                self.stop(Xchan)
            if (event.key() == QtCore.Qt.Key_Up or event.key() == QtCore.Qt.Key_Down):
                print('Up/Down key released')
                self.stop(Ychan)
            if (event.key() == QtCore.Qt.Key_A or event.key() == QtCore.Qt.Key_Q):
                print('A/Q key released')
                self.stop(Zchan)

    def wheelMoved(self, event):
        pass
        # wheelDir = int(event.angleDelta().y() / 120)
        # currentZPos = self.getPosition_mm()[2]
        # self.move_absolute_mm(currentZPos + (self.um_per_wheelStep / 1000) * wheelDir, axis=2)