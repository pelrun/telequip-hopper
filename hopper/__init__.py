""" Telequip coin hopper driver"""

class Hopper(object):

    _STX = "\x02"
    _ETX = "\x03"
    _EOT = "\x04"
    _ENQ = "\x05"
    _ACK = "\x06"
    _NAK = "\x21"

    _commands = dict(GetInventoryStatus='C\0x0A',
                    RebootMachine='C\0x1B',
                    GetHopperConfiguration='C\0x7F',

                    GetLowCoinStatus='Ca',
                    ClearHistory='Cc',
                    GetLastDispense='Cd',
                    GetMachineErrors='Ce',
                    GetSerialNumber='Cg',
                    GetHistory='Ch',
                    GetDispenseBelowValue='Cm',
                    GetFaultByHopper='Cq',
                    ResetMachineStatus='Cr',
                    GetMachineStatus='Cs',
                    GetPIDNumber='Ct',
                    GetExtendedMachineErrors='Cu',
                    GetFirmwareRevision='Cv',
                    GetBootloaderRevision='Cw',
                    GetCoinDefIniRevision='Cx',
                    UpdateLowCoinStatus='Cy',
                    GetRealtimeCoinSensorStatus='Cz',
                    
                    SetHopperConfiguration='CU',
                    
                    DispenseByAmount='C',
                    SetHistory='H',
                    SetDispenseBelowValue='M',
                    DispenseByHopper='P',
                    DispenseOverride='O',
                    SpinByBin='S'
                   )

    def __init__(self, device, isCX25=True, debug=False):
        self.isCX25 = isCX25
        self.device = device
        self.statusbyte = 0
        self.debug = debug 

    def checksum(self, text):
        """Calculate checksum for hoppers."""
        result = 0
        if self.isCX25:
            for x in str(text):
                result ^= ord(x)
            return chr(result+1)
        else:
            # after everything, the t-flex doesn't actually care about the checksum
            for x in str(text):
                result ^= ord(x)
            return chr(result ^ 3)

    @property
    def status(self):
        """Unpack status byte into a dict."""
        s = ord(self.statusbyte)
        return dict(parityerror=bool(s&1),
                    functionerror=bool(s&2),
                    malfunction=bool(s&4),
                    busy=bool(s&8),
                    lowcoin=bool(s&16),
                    coindispensed=bool(s&32)
                   )

    def sendcommand(self, command=None, parameter=None):
        """Send command to hopper and return the response."""
        cmdstring = self._commands.get(command,'')
        if cmdstring == '':
            return None

        if parameter is None:
            rawcmd = "\x01" + self._EOT + cmdstring + self._ENQ
        else:
            rawcmd = "\x01" + self._EOT + cmdstring + self._STX + str(parameter) + self._ETX + self.checksum(parameter)

        self.device.write(rawcmd)
        result = self.device.read(59).rstrip("\x00")

        if self.debug:
            print "Command: {}({})".format(command,parameter)
            print "Sent: ", list(rawcmd)
            print "Read: ", list(result)

        self.statusbyte = result[1]
        if result[1] == self._STX:
            return result[2:result.find(self._ETX,2)]
        else:
            return result[2] == self._ACK

    def getLowCoinStatus(self):
        reply = self.sendcommand('GetLowCoinStatus')
        return [bool(x=='1') for x in list("{:08b}".format(ord(reply[0])))]

    @property
    def serialNumber(self):
        reply = self.sendcommand('GetSerialNumber')
        return reply

    def reset(self):
        self.sendcommand('ResetMachineStatus')

    def dispense(self, cents):
        self.reset()
        self.sendcommand('DispenseByAmount',str(cents))
        return self.status['coindispensed']

    def getFaultByHopper(self):
        result = self.sendcommand('GetFaultByHopper')

    @property
    def machineStatus(self):
        return self.sendcommand('GetMachineStatus')

    @property
    def machineErrors(self):
        return self.sendcommand('GetExtendedMachineErrors')

    @property
    def sensorStatus(self):
        return self.sendcommand('GetRealtimeCoinSensorStatus')

    @property
    def dispenseBelowValue(self):
        return self.sendcommand('GetDispenseBelowValue')

    @dispenseBelowValue.setter
    def dispenseBelowValue(self, value):
        result = self.sendcommand('SetDispenseBelowValue', value)

"""

Canister Not present
Canister was removed 
Coins exit blocked.
Coin Jam Latch
Column Sensor Failed
Coins dispensed with retires
Dispense Abort.
Canister Not present
Canister was removed 
Coins exit blocked.
Coin Jam Latch
Column Sensor Failed
Coins dispensed with retires
Dispense Abort.
"""

if __name__ == "__main__":
    f = open("/dev/coinhopper0","r+b")
    h = Hopper(f,debug=True)

    h.reset()
    print h.sensorStatus
    #print h.statusbyte
    #print h.status
    #print h.serialNumber
    #h.dispense(80)
    #print h.status

