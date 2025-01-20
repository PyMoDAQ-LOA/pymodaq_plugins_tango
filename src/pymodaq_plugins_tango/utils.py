# -*- coding: utf-8 -*-

from pathlib import Path
from pymodaq.utils.config import BaseConfig, USER


class Config(BaseConfig):
    """Main class to deal with configuration values for this plugin"""
    config_template_path = Path(__file__).parent.joinpath('resources/config_tango.toml')
    config_name = f"config_{__package__.split('pymodaq_plugins_')[1]}"
