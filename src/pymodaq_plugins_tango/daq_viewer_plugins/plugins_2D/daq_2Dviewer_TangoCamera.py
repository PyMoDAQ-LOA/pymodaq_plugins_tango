from qtpy.QtCore import QThread, Slot, QRectF
from qtpy import QtWidgets
import numpy as np
import pymodaq.utils.math_utils as mutils
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, main, comon_parameters
from pymodaq.utils.daq_utils import ThreadCommand, getLineInfo
from pymodaq.utils.data import DataFromPlugins, Axis, DataToExport
from pymodaq.utils.array_manipulation import crop_array_to_axis

from pymodaq_plugins_tango.hardware.TANGO.tango_device import TangoDevice
from pymodaq_plugins_tango.hardware.TANGO.tango_config import TangoTomlConfig
from pathlib import Path


class DAQ_2DViewer_TangoCamera(DAQ_Viewer_base):

    config = TangoTomlConfig('cameras', Path(__file__).parents[2] / 'resources/config_tango.toml')
    params = comon_parameters + [
        {'title': 'Nimages colors:', 'name': 'Nimagescolor', 'type': 'int', 'value': 1, 'default': 1, 'min': 0,
         'max': 3},
        {'title': 'Nimages pannels:', 'name': 'Nimagespannel', 'type': 'int', 'value': 1, 'default': 0, 'min': 0},
        {'title': 'Use ROISelect', 'name': 'use_roi_select', 'type': 'bool', 'value': False},
        {'title': 'Cam. Prop.:', 'name': 'cam_settings', 'type': 'group', 'children': []},
        {'title': 'Device address:', 'name': 'dev_address', 'type': 'list', 'value': config.addresses[0],
         'limits': config.addresses,
         'readonly': False},
    ]

    def ini_attributes(self):

        self.tangoCam = None
        self._address = self.config.addresses[0]
        self.controller: TangoDevice = None
        self.image = None

        self.x_axis = None
        self.y_axis = None
        self.live = False
        self.ind_commit = 0
        self.ind_data = 0
        self._ROI = dict(position=[10, 10], size=[5, 5])

    @Slot(QRectF)
    def ROISelect(self, roi_pos_size: QRectF):
        self._ROI['position'] = int(roi_pos_size.left()), int(roi_pos_size.top())
        self._ROI['size'] = int(roi_pos_size.width()), int(roi_pos_size.height())

    def commit_settings(self
                        , param):
        """
            Activate parameters changes on the hardware.

            =============== ================================ ===========================
            **Parameters**   **Type**                          **Description**
            *param*          instance of pyqtgraph Parameter   the parameter to activate
            =============== ================================ ===========================

            See Also
            --------
            set_Mock_data
        """
        #self.get_cam_data()
        pass

    def get_cam_data(self):
        """
        """
        x_axis = np.linspace(0, self.settings.child('Nx').value(), self.settings.child('Nx').value(),
                             endpoint=False)
        print(f"settings : {self.settings.child('Nx').value()}")
        y_axis = np.linspace(0, self.settings.child('Ny').value(), self.settings.child('Ny').value(),
                             endpoint=False)

        self.image = np.array(self.tangoCam.value[0])

        QThread.msleep(100)
        self.x_axis = Axis(label='Horizontal', data=x_axis, index=1)
        self.y_axis = Axis(label='Vertical', data=y_axis, index=0)

        return self.image

    def ini_detector(self, controller=None):
        self._address = self.settings.child('dev_address').value()
        print(self._address)
        self.ini_detector_init(controller, TangoDevice(address=self._address,
                                                       dimension='2D',
                                                       attributes=["image"]))
        print("Starting tango Camera")
        print("Finished Config")
        print(self.controller.connected)
        print(self.controller.value)

        #self.x_axis = self.get_xaxis()
        #self.y_axis = self.get_yaxis()

        # initialize viewers with the future type of data but with 0value data
        #self.dte_signal_temp.emit(self.average_data(1, True))

        initialized = True
        info = 'Init'
        return info, initialized

    def close(self):
        """
            not implemented.
        """
        pass

    def get_xaxis(self):
        self.get_cam_data()
        return self.x_axis

    def get_yaxis(self):
        self.get_cam_data()
        return self.y_axis

    def grab_data(self, Naverage=1, **kwargs):
        """
            Getting image as numpy array
        """
        data = self.controller.value[0]
        data = DataFromPlugins(name='Front-end far-field', data=[data])
        self.dte_signal.emit(DataToExport('Front-end far-field', data=[data]))


    def stop(self):
        """
            not implemented.
        """
        self.live = False
        return ""


if __name__ == '__main__':
    main(__file__)
