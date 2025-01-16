from pathlib import Path
import queue
import time
import tempfile
from threading import Lock

import numpy as np
from qtpy import QtCore, QtWidgets

from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.data import DataFromPlugins, Axis, DataToExport, DataRaw, DataCalculated
from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters, main
from pymodaq.utils.parameter import Parameter
from pymodaq.utils.parameter.pymodaq_ptypes import GroupParameter, registerParameterType
from pymodaq.utils.parameter.utils import iter_children
from pymodaq_plugins_mockexamples.hardware.photon_yielder import PhotonYielder, Photons
from pymodaq.utils.h5modules.saving import H5Saver
from pymodaq.utils.h5modules.data_saving import (DataEnlargeableSaver, DataToExportEnlargeableSaver, DataLoader,
                                                 NodeError)

lock = Lock()

image_params = [
    {'title': 'Time min (µs)', 'name': 'time_min', 'type': 'float', 'value': 0},
    {'title': 'Time max (µs)', 'name': 'time_max', 'type': 'float', 'value': 20},
]


class PresetScalableGroupPlot(GroupParameter):
    """
    """

    def __init__(self, **opts):
        opts['type'] = 'groupplot'
        opts['addText'] = "Add"
        super().__init__(**opts)

    def addNew(self):
        """

        """
        try:
            name_prefix = 'image'
            child_indexes = [int(par.name()[len(name_prefix) + 1:]) for par in self.children()]

            if child_indexes == []:
                newindex = 0
            else:
                newindex = max(child_indexes) + 1

            params = image_params

            children = [{'title': 'Name:', 'name': 'name', 'type': 'str', 'value': f'Image {newindex:02.0f}'}] + params

            child = {'title': f'Image {newindex:02.0f}', 'name': f'{name_prefix}{newindex:02.0f}',
                     'type': 'group', 'children': children, 'removable': True, 'renamable': False}

            self.addChild(child)
        except Exception as e:
            print(str(e))
registerParameterType('groupplot', PresetScalableGroupPlot, override=True)



class DAQ_NDViewer_MockEvents(DAQ_Viewer_base):
    """ Instrument plugin class for a 2D viewer.
    
    This object inherits all functionalities to communicate with PyMoDAQ’s DAQ_Viewer module through inheritance via
    DAQ_Viewer_base. It makes a bridge between the DAQ_Viewer module and the Python wrapper of a particular instrument.

    Attributes:
    -----------
    controller: PhotonYielder
        The particular object that allow the communication with the hardware, in general a python wrapper around the
         hardware library.
    """
    grabber_start_signal = QtCore.Signal(float, int)
    grabber_stop_signal = QtCore.Signal()
    saver_start_signal = QtCore.Signal()

    params = comon_parameters + [
        {'title': 'Acqu. Time (s)', 'name': 'acqui_time', 'type': 'float', 'value': 10},
        {'title': 'Refresh Time (ms)', 'name': 'refresh_time', 'type': 'int', 'value': 500},
        {'title': 'Wait Time (ms)', 'name': 'wait_time', 'type': 'int', 'value': 1},
        {'title': 'Show ND', 'name': 'prepare_viewers', 'type': 'bool_push', 'value': False, 'label': 'Prepare Viewers'},
        {'title': 'Show ND', 'name': 'show_nd', 'type': 'bool_push', 'value': False, 'label': 'Show ND'},
        {'title': 'Histogram:', 'name': 'histogram', 'type': 'group', 'children': [
            {'title': 'Apply weight?', 'name': 'apply_weight', 'type': 'bool', 'value': False},
            {'title': 'Time min (µs)', 'name': 'time_min_tof', 'type': 'float', 'value': 0},
            {'title': 'Time max (µs)', 'name': 'time_max_tof', 'type': 'float', 'value': 20},
            {'title': 'N Bin Time', 'name': 'nbin_time', 'type': 'int', 'value': 256},
            {'title': 'N Bin X', 'name': 'nbin_x', 'type': 'int', 'value': 256},
            {'title': 'N Bin y', 'name': 'nbin_y', 'type': 'int', 'value': 256},
        ]},
        {'title': '2D Histograms:', 'name': 'images_settings', 'type': 'groupplot'},
    ]

    def ini_attributes(self):
        self.controller: PhotonYielder = None

        self.x_axis: Axis = None
        self.y_axis: Axis = None
        self.time_axis: Axis = None

        self.h5temp : H5Saver() = None
        self.temp_path : tempfile.TemporaryDirectory = None
        self.saver: DataToExportEnlargeableSaver = None
        self._loader: DataLoader = None

        self.saver_thread: QtCore.QThread = None

        self._queue = queue.Queue()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.process_events)

    def commit_settings(self, param: Parameter):
        """Apply the consequences of a change of value in the detector settings

        Parameters
        ----------
        param: Parameter
            A given parameter (within detector_settings) whose value has been changed by the user
        """
        # TODO for your custom plugin
        if param.name() in iter_children(self.settings.child('histogram'), []):
            if self._loader is not None:
                self.process_events()
        elif param.name() == 'show_nd':
            if param.value():
                self.show_nd()
                param.setValue(False)
        elif param.name() == 'prepare_viewers':
            self.prepare_viewers()

    def prepare_viewers(self):
        dte = DataToExport('Events', data=[DataCalculated('TOF', data=[np.array([0, 1, 2])], )], )
        for image_settings in self.settings.child('images_settings').children():
            dte.append(DataCalculated(image_settings['name'], data=[np.array([[0, 1], [0, 1]])], ))
        for dwa in dte:
            dwa.create_missing_axes()
        self.dte_signal_temp.emit(dte)
        QtWidgets.QApplication.processEvents()
        QtWidgets.QApplication.processEvents()
        QtCore.QThread.msleep(1000)

    def ini_detector(self, controller=None):
        """Detector communication initialization

        Parameters
        ----------
        controller: (object)
            custom object of a PyMoDAQ plugin (Slave case). None if only one actuator/detector by controller
            (Master case)

        Returns
        -------
        info: str
        initialized: bool
            False if initialization failed otherwise True
        """

        self.ini_detector_init(old_controller=controller,
                               new_controller=PhotonYielder())

        callback = PhotonCallback(self.controller, self._queue)
        self.callback_thread = QtCore.QThread()  # creation of a Qt5 thread
        callback.moveToThread(self.callback_thread)  # callback object will live within this thread
        callback.data_sig.connect(self.emit_data)

        self.grabber_start_signal.connect(callback.grab)
        self.grabber_stop_signal.connect(callback.stop)
        self.callback_thread.callback = callback

        self.callback_thread.start()

        info = "Whatever info you want to log"
        initialized = True
        return info, initialized

    def emit_data(self):
        self.timer.stop()
        self.process_events(emit_temp=False)

    def process_events(self, emit_temp=True):
        try:
            node = self._loader.get_node('/RawData/myphotons/DataND/CH00/EnlData00')
            lock.acquire()
            dwa = self._loader.load_data(node, load_all=True)
            dwa = dwa.sort_data(0)
            lock.release()
            print(f'Nphotons: {dwa.size}')
            dte = self.compute_histogram(dwa, '1D')
            if emit_temp:
                self.dte_signal_temp.emit(dte)
            else:
                dwa.add_extra_attribute(save=True, plot=False)
                dte.append(dwa)
                self.dte_signal.emit(dte)
        except NodeError:
            pass

    def compute_image_histogram(self, dwa: DataRaw, name: str, time_min: float, time_max: float):
        index_min = dwa.get_axis_from_index(0)[0].find_index(time_min)
        index_max = dwa.get_axis_from_index(0)[0].find_index(time_max)
        dwa_croped = dwa.inav[index_min:index_max]
        pos_array, x_edges, y_edges = np.histogram2d(dwa_croped[1], dwa_croped[2],
                                                     bins=(self.settings['histogram', 'nbin_x'],
                                                           self.settings['histogram', 'nbin_y']),
                                                     range=((0, self.settings['histogram', 'nbin_x']),
                                                            (0, self.settings['histogram', 'nbin_y'])),
                                                     )
        dwa_image = DataFromPlugins(name, data=[pos_array],
                                    axes=[Axis('X', 'pxl', x_edges[:-1], index=0),
                                          Axis('Y', 'pxl', y_edges[:-1], index=1)],
                                    save=False, plot=True)
        return dwa_image

    def compute_histogram(self, dwa: DataRaw, dim='1D') -> DataToExport:
        dte = DataToExport('Histograms', )
        if dim == '1D':
            time_of_flight, time_array = np.histogram(dwa.axes[0].get_data_0D(),
                                                      bins=self.settings['histogram', 'nbin_time'],
                                                      range=(self.settings['histogram', 'time_min_tof'] * 1e-6,
                                                             self.settings['histogram', 'time_max_tof'] * 1e-6),
                                                      weights=dwa.data[0] if self.settings['histogram', 'apply_weight']
                                                      else None)
            dte.append(DataFromPlugins('TOF', data=[time_of_flight],
                                       axes=[Axis('Time', 's', time_array[:-1])],
                                       save=False, plot=True))

            for image_settings in self.settings.child('images_settings').children():
                dte.append(self.compute_image_histogram(dwa, image_settings['name'],
                                                        image_settings['time_min'] * 1e-6,
                                                        image_settings['time_max'] * 1e-6))

        else:
            data_array, edges = np.histogramdd(np.stack((dwa.axes[0].get_data_0D(),
                                                         np.squeeze(dwa[1].astype(int)),
                                                         np.squeeze(dwa[2]).astype(int)), axis=1),
                                               bins=(self.settings['histogram', 'nbin_time'],
                                                     self.settings['histogram', 'nbin_x'],
                                                     self.settings['histogram', 'nbin_y']),
                                               range=((self.settings['histogram', 'time_min_tof'] * 1e-6,
                                                      self.settings['histogram', 'time_max_tof'] * 1e-6),
                                                      (0, self.settings['histogram', 'nbin_x']),
                                                      (0, self.settings['histogram', 'nbin_y']))
                                               )
            dwa_tof = DataCalculated('TOF', data=[data_array],
                                     axes=[Axis('Time', 's', edges[0][:-1], index=0),
                                           Axis('X', 's', edges[1][:-1], index=1),
                                           Axis('Y', 's', edges[2][:-1], index=2)],
                                     nav_indexes=(1, 2), save=False, plot=True)
            dte.append(dwa_tof)
        return dte

    def show_nd(self):
        node = self._loader.get_node('/RawData/myphotons/DataND/CH00/EnlData00')
        dwa = self._loader.load_data(node, load_all=True)

        dte_tof = self.compute_histogram(dwa, 'ND')
        self.dte_signal_temp.emit(dte_tof)

    def close(self):
        """Terminate the communication protocol"""
        self.saver.close()

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
        if self.h5temp is not None:
            self.h5temp.close()
            self.temp_path.cleanup()
        if self.saver_thread is not None:
            if self.saver_thread.isRunning():
                self.saver_thread.terminate()
                while self.saver_thread.isRunning():
                    QtCore.QThread.msleep(100)
                    print('Thread still running')

        self.prepare_viewers()

        self.h5temp = H5Saver(save_type='detector')
        self.temp_path = tempfile.TemporaryDirectory(prefix='pymo')
        addhoc_file_path = Path(self.temp_path.name).joinpath('temp_data.h5')
        self.h5temp.init_file(custom_naming=True, addhoc_file_path=addhoc_file_path)
        self.h5temp.get_set_group('/RawData', 'myphotons')
        self.saver: DataToExportEnlargeableSaver = DataToExportEnlargeableSaver(self.h5temp,
                                                                                axis_name='photon index',
                                                                                axis_units='index')
        self._loader = DataLoader(self.h5temp)

        self.controller.ind_grabed = -1

        save_callback = SaverCallback(self._queue, self.saver)
        self.saver_thread = QtCore.QThread()
        save_callback.moveToThread(self.saver_thread)
        self.saver_thread.callback = save_callback
        self.saver_start_signal.connect(save_callback.work)
        self.saver_thread.start()

        self.grabber_start_signal.emit(self.settings['acqui_time'], self.settings['wait_time'])
        self.saver_start_signal.emit()
        self.timer.setInterval(self.settings['refresh_time'])
        self.timer.start()

    def stop(self):
        """Stop the current grab hardware wise if necessary"""
        return ''


class PhotonCallback(QtCore.QObject):
    """

    """
    data_sig = QtCore.Signal()

    def __init__(self, photon_grabber: PhotonYielder, event_queue: queue.Queue):
        super().__init__()
        self.photon_grabber = photon_grabber
        self.event_queue = event_queue
        self._stop = False

    def grab(self, acquisition_time: float, wait_time: int):
        self._stop = False
        start_acqui = time.perf_counter()
        while (time.perf_counter() - start_acqui) <= acquisition_time or self._stop:
            photons: Photons = self.photon_grabber.grab()
            self.event_queue.put(photons)
            QtCore.QThread.msleep(wait_time)
        self.data_sig.emit()

    def stop(self):
        self._stop = True


class SaverCallback(QtCore.QObject):
    def __init__(self, event_queue: queue.Queue, saver: DataToExportEnlargeableSaver):
        super().__init__()
        self.event_queue = event_queue
        self.saver = saver

    def work(self):
        while True:
            photons: Photons = self.event_queue.get()
            data = DataToExport('photons', data=[
                DataRaw('time', data=[photons.intensity, photons.x_pos, photons.y_pos],
                        labels=['intensity', 'x_pos', 'y_pos'],
                        nav_indexes=(0, ),
                        axes=[Axis('timestamps', data=photons.time_stamp, index=0)],
                        plot=False,
                        save=True
                        )
            ])
            lock.acquire()
            self.saver.add_data('/RawData/myphotons', axis_value=photons.time_stamp, data=data)
            lock.release()
            self.event_queue.task_done()


if __name__ == '__main__':
    main(__file__)
