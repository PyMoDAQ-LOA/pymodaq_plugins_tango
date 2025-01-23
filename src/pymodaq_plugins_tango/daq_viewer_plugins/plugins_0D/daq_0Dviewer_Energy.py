import numpy as np
import os
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.data import DataFromPlugins, Axis, DataToExport
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters, main
from pymodaq.utils.parameter import Parameter

import pymodaq.utils.math_utils as mutils

from pymodaq_plugins_tango.hardware.TANGO.tango_device import TangoDevice
from pymodaq_plugins_tango.hardware.TANGO.tango_config import TangoTomlConfig
from pathlib import Path


# TODO:
# (1) change the name of the following class to DAQ_1DViewer_TheNameOfYourChoice
# (2) change the name of this file to daq_1Dviewer_TheNameOfYourChoice ("TheNameOfYourChoice" should be the SAME
#     for the class name and the file name.)


class DAQ_0DViewer_Energy(DAQ_Viewer_base):

    config = TangoTomlConfig('energymeters', Path(__file__).parents[2]/'resources/config_tango.toml')
    params = comon_parameters + [{'title': 'Device address:', 'name': 'dev_address',
                                  'type': 'list', 'value': config.addresses[1],
                                  'limits': config.addresses,
                                  'readonly': False},]

    def ini_attributes(self):
        self.controller: TangoDevice = None
        self.device_proxy_success = False
        self._address = None

    def commit_settings(self, param: Parameter):
        print("called commit settings")

    def ini_detector(self, controller=None):
        self._address = self.settings.child('dev_address').value()
        print(self._address)
        self.ini_detector_init(controller, TangoDevice(address=self._address,
                                                       dimension='1D',
                                                       attributes=["energy_1"]))

        initialized = self.controller.connected
        info = 'Controller ok'

        return info, initialized

    def close(self):
        pass

    def grab_data(self, Naverage=1, **kwargs):

        data = np.array(self.controller.value)
        self.dte_signal.emit(DataToExport(name='myplugin',
                                          data=[DataFromPlugins(name='Energy', data=data,
                                                                dim='Data0D', labels=['energy'])]))

    def stop(self):
        return ""


if __name__ == '__main__':
    main(__file__)
