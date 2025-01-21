from tango import DeviceProxy


class TangoDevice:
    """
     Generic TANGO device class that reads a list of attributes as a value
        Needs : device address, dimension to plot, list of attributes to get
             """

    def __init__(self, *, address: str, dimension: str, attributes: list):
        self._address = address
        self._dimension = dimension
        self._attributes = attributes
        self._value = None
        self._unit = None
        self._connected = False

        self.createProxy(self._address)

    def createProxy(self, address: str):
        print("Creating device proxy")
        try:
            self.__deviceProxy = DeviceProxy(address)
            print(self.__deviceProxy)
            self._connected = True
        except Exception as e:
            self.__deviceProxy = None
            self._connected = False
            print(f'Create proxy error : {e}')

    @property
    def connected(self):
        return self._connected

    def getAttribute(self, attribute: str):
        try:
            self._value = self.__deviceProxy.read_attribute(attribute).value
        except Exception as e:
            self._value = None
            print(f"Error in getAttribute function: {e}")
        return self._value

    def getAttributes(self):
        return [self.getAttribute(attribute) for attribute in self._attributes]

    @property
    def value(self):
        return self.getAttributes()


def user_story():
    myDevice = TangoDevice(address='SY-SPECTRO_1/Spectrometer/FE1',
                           dimension='1D',
                           attributes=["lambda", "intensity", "boxcar", "Status"])
    print(myDevice.connected)
    print(myDevice.value)


if __name__ == "__main__":
    user_story()
