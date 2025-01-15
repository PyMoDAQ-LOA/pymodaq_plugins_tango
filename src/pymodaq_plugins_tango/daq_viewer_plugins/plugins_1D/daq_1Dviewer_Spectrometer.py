import numpy as np
import os
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.data import DataFromPlugins, Axis, DataToExport
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters, main
from pymodaq.utils.parameter import Parameter

import pymodaq.utils.math_utils as mutils

from pymodaq_plugins_tango.hardware.TANGO.tango_device import TangoDevice
from pymodaq_plugins_tango.hardware.TANGO.tango_utils import TangoTomlConfig


class DAQ_1Dviewer_Spectrometer(DAQ_Viewer_base):
    """ Instrument plugin class for a generic spectrometer.
        * Any spectrometer on the tango bus can be viewed. Address and attributes should be entered in toml file
        * Tested with TANGO controls on a virtual machine (communication through the virtual switch)
        * PyMoDAQ Version 4.4.7
        * OS : Microsoft 11 Pro 10.0.22631
        * pyTango and tomllib should be installed. To test pyTango install, run the following lines in the CLI
            python
            from tango import DeviceProxy
            tango_host = tango.ApiUtil.get_env_var("TANGO_HOST")
            print(tango_host)
            print(tango.__version__)
        To test communication, run :
            my_device = DeviceProxy(<some known device address, e.g. "SY-SPECTRO_1/Spectrometer/FE1">)
            print(my_device.read_attribute(<some known attribute, e.g. "lambda">).value)
        * The wrapper is in the hardware folder. It uses the tango bus as some sort of virtual hardware.
        This is also where the toml config file is located. It has to be filled for the plugin to work !
z
    This object inherits all functionalities to communicate with PyMoDAQ’s DAQ_Viewer module through inheritance via
    DAQ_Viewer_base. It makes a bridge between the DAQ_Viewer module and the Python wrapper of a particular instrument.


    Attributes:
    -----------
    controller: object
        The particular object that allow the communication with the hardware, in general a python wrapper around the
         hardware library.

    """

    """Find right place for toml file"""
    print(os.getcwd())
    config = TangoTomlConfig('spectrometers', "./src/hardware/TANGO/tango_devices.toml")
    print(config.addresses)
    params = comon_parameters + [{'title': 'Device address:', 'name': 'dev_address',
                                  'type': 'list', 'value': 'SY-SPECTRO_1/Spectrometer/FE1',
                                  'limits': ['SY-SPECTRO_1/Spectrometer/FE1', 'SY-SPECTRO_1/Spectrometer/FE2',
                                             'SY-SPECTRO_1/Spectrometer/FE3'],
                                  'readonly': False}, ]

    def ini_attributes(self):
        self.controller: TangoDevice = None
        self.device_proxy_success = False
        self._address = None

    def commit_settings(self, param: Parameter):
        pass

    def ini_detector(self, controller=None):
        self._address = self.settings.child('dev_address').value()
        print(self._address)
        self.ini_detector_init(controller, TangoDevice(address=self._address,
                                                       dimension='1D',
                                                       attributes=["lambda", "intensity"]))

        initialized = self.controller.connected
        info = 'Controller ok'

        return info, initialized

    def close(self):
        pass

    def grab_data(self, Naverage=1, **kwargs):
        """Start a grab from the detector

        Parameters
        ----------
        Naverage: int
            Number of hardware averaging (if hardware averaging is possible, self.hardware_averaging should be set to
            True in class preamble and you should code this implementation)
        kwargs: dict
            others optionals arguments
        """

        xaxis, data = self.controller.value
        data = DataFromPlugins(name='Spectrum', data=[data],
                               axes=[Axis('Wavelength', data=xaxis)])

        self.dte_signal.emit(DataToExport('Spectrum', data=[data]))

    def stop(self):
        return ""


if __name__ == '__main__':
    main(__file__)
