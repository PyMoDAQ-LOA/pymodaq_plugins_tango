import numpy as np
import tango
import tomllib

class TangoTomlConfig:
    DEVICES = ['spectrometers', 'cameras', 'energymeters']

    def __init__(self, devType, tomlFile):
        assert devType in self.DEVICES
        self._addresses = []
        self._config = {}

        self.parseConfig(devType, tomlFile)

    @property
    def addresses(self):
        return self._addresses
    @property
    def config(self):
        return self._config()

    def parseConfig(self, devType, tomlFile):
        try:
            with open(tomlFile, "rb") as f:
                self._config = tomllib.load(f)

            self._addresses = [self._config[devType][key]['address'] for key in self._config[devType].keys()]
        except Exception as e:
            print(e)



class TangoCom:

    def __init__(self):
        self._tangoHost = None
    @property
    def tangoHost(self):
        return self.get_tangoHost()
    def get_tangoHost(self):
        self._tangoHost = tango.ApiUtil.get_env_var("TANGO_HOST")


    def get_all_devices(self):
        try:
            db = tango.Database()
            self._devices = db.get_device_exported("*")
        except:
            return None
        else:
            return self._devices

def user_story():
    tc = TangoTomlConfig('spectrometers', "tango_devices.toml")
    print(tc.addresses)


if __name__ == "__main__":
    user_story()


