""" Telequip coin hopper driver"""

from struct import pack

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
        self.statusbyte = 'P'
        self.debug = debug
        self.inSetupMode = False

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


    def sendrawcommand(self, rawcmd):
        self.device.write(rawcmd)

        if self.debug:
            print "Sent: ", list(rawcmd)

        result = self.device.read(59).rstrip("\x00")

        if self.debug:
            print "Read: ", list(result)

        return result

    def sendcommand(self, command, parameter=None, expectStatus=True):
        """Send command to hopper and return the response."""
        cmdstring = self._commands.get(command,command)

        if parameter is None:
            rawcmd = "\x01" + self._EOT + cmdstring + self._ENQ
        else:
            rawcmd = "\x01" + self._EOT + cmdstring + self._STX + str(parameter) + self._ETX + self.checksum(parameter)

        if self.debug:
            print "Command: {}({})".format(command,parameter)

        result = self.sendrawcommand(rawcmd)

        if expectStatus:
            if ord(result[1])&0x40:
                self.statusbyte = result[1]
            elif ord(result[2])&0x40:
                self.statusbyte = result[2]

        if result[1] == self._STX:
            return result[2:result.find(self._ETX,2)]
        else:
            return result[2] == self._ACK

    def enterSetupMode(self):
        result = self.sendrawcommand("\x02\x16")
        self.inSetupMode = True
        return result[1]

    def exitSetupMode(self):
        result = self.sendrawcommand("\x02\x45")
        self.inSetupMode = False
        return result[1]

    def readEeprom(self,address,length=0x2a):
        if not self.inSetupMode or address > 0xff or length > 0x2a:
            return False
        result = self.sendrawcommand(pack('4B',0x02,0x2b,address,length))
        return result[2:length+2]

    def writeEeprom(self, address, byte):
        if not self.inSetupMode or address > 0xFF or byte > 0xFF:
            return False
        return self.sendrawcommand("\x02\x23"+chr(address)+chr(byte))

    @property
    def lowCoinStatus(self):
        reply = self.sendcommand('GetLowCoinStatus', expectStatus=False)
        data = ord(reply[0]) | (ord(reply[1])<<4)
        return [bool(x=='1') for x in list("{:08b}".format(data))]

    @property
    def serialNumber(self):
        reply = self.sendcommand('GetSerialNumber', expectStatus=False)
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
        return self.sendcommand('GetDispenseBelowValue',expectStatus=False)

    @dispenseBelowValue.setter
    def dispenseBelowValue(self, value):
        result = self.sendcommand('SetDispenseBelowValue', value)

    @property
    def history(self):
        return [self.sendcommand("C"+chr(104+column),expectStatus=False) for column in range(0,9) if column != 5]

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

    #print h.sensorStatus
    #print h.machineStatus
    #print h.lowCoinStatus
    #print h.dispenseBelowValue
    #print h.getFaultByHopper()
    #print h.serialNumber
    #h.reset()
    #h.dispense(10)
    #print h.status
    #print h.history
    #try:
    #    h.enterSetupMode()
    #    print list(h.readEeprom(0x2a))
    #finally:
    #    h.exitSetupMode()
