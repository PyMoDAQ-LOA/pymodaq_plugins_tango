# -*- coding: utf-8 -*-
"""
Created 17/01/2025
@author: Aline Vernier
"""
from pathlib import Path
from pymodaq.utils.config import BaseConfig, USER
import tango
import tomllib


class TangoTomlConfig:
    DEVICES = ['spectrometers', 'cameras', 'energymeters']

    def __init__(self, dev_type, toml_file):
        assert dev_type in self.DEVICES
        self._addresses = []
        self._config = {}

        self.parse_config(dev_type, toml_file)

    @property
    def addresses(self):
        return self._addresses

    @property
    def config(self):
        return self._config

    def parse_config(self, dev_type, toml_file):
        try:
            with open(toml_file, "rb") as f:
                self._config = tomllib.load(f)

            self._addresses = [self._config[dev_type][key]['address'] for key in self._config[dev_type].keys()]
        except Exception as e:
            print(e)


class TangoCom:

    def __init__(self):
        self._devices = None
        self._tangoHost = None

    @property
    def tango_host(self):
        return self.get_tango_host()

    def get_tango_host(self):
        self._tangoHost = tango.ApiUtil.get_env_var("TANGO_HOST")

    def get_all_devices(self):
        try:
            db = tango.Database()
            self._devices = db.get_device_exported("*")
        except:
            return None
        else:
            return self._devices




class Config(BaseConfig):
    """Main class to deal with configuration values for this plugin"""
    config_template_path = Path(__file__).parent.joinpath('resources/config_tango.toml')
    config_name = f"config_{__package__.split('pymodaq_plugins_')[1]}"
