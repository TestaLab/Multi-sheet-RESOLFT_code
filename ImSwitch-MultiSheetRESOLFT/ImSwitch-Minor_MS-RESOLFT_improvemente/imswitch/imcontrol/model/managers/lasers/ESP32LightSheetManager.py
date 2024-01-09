from imswitch.imcommon.model import initLogger
from .LaserManager import LaserManager
from imswitch.imcontrol.model.interfaces.ESP32RestAPI import ESP32Client

class ESP32LightSheetManager(LaserManager):

    def __init__(self, LighsheetInfo, name, **lowLevelManagers):
        super().__init__(LighsheetInfo, name, isBinary=False, 
            valueUnits='mW', valueDecimals=0)
        self._rs232manager = lowLevelManagers['rs232sManager'][
            LighsheetInfo.managerProperties['rs232device']
        ]
        self.__axis = LighsheetInfo.managerProperties['axis']

        self.__logger = initLogger(self, instanceName=name)

    def setEnabled(self, enabled):
        """Turn on (N) or off (F) laser emission"""

    def setValue(self, value=0):
        """Handles output power.
        Sends a RS232 command to the laser specifying the new intensity.
        """
        if self.__axis == "pos_x":
            self._rs232manager._esp32.galvo_pos_x(value)
        elif self.__axis == "amp_y":
            self._rs232manager._esp32.galvo_amp_y(value)


# Copyright (C) 2020-2021 ImSwitch developers
# This file is part of ImSwitch.
#
# ImSwitch is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ImSwitch is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
