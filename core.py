# core.py by CoccaGuo at 2022/05/16 16:45
from abc import ABCMeta, abstractmethod
from enum import Enum
import logging
import time
import numpy as np

from interface import *


class NanonisController(nanonis_programming_interface):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        setupLog()

    def try_convert(self, value):
        if type(value) is str:
            return self.convert(value)
        else:
            return float(value)

    def MotorMoveSet(self, direction, steps, wait=True):
        direct_map = {'X+': 0, 'X-': 1, 'Y+': 2, 'Y-': 3, 'Z+': 4, 'Z-': 5}
        try:
            direction = direct_map[direction.upper()]
        except KeyError:
            raise nanonisException(
                'Invalid direction. Please use X+, X-, Y+, Y-, Z+, Z- expressions.')
        if direction == 5:
            raise nanonisException('Moving Z- is not Safe.')
        self.send('Motor.StartMove', 'uint32', direction, 'uint16',
                  steps, 'uint32', 0, 'uint32', int(wait))

    def AutoApproachOpen(self):
        self.send('AutoApproach.Open')

    def AutoApproachSet(self, on=True):
        self.send('AutoApproach.OnOffSet', 'uint16', int(on))

    def AutoApproachGet(self):
        parsedResponse = self.parse_response(
            self.send('AutoApproach.OnOffGet'), 'uint16')
        return parsedResponse['0']

    def ZGainGet(self):
        parsedResponse = self.parse_response(
            self.send('ZCtrl.GainGet'), 'float32', 'float32', 'float32')
        return {
            'P': parsedResponse['0'],
            'T': parsedResponse['1'],
            'I': parsedResponse['2']
        }

    def ZGainSet(self, P, T, I):
        if type(P) is str:
            P_val = self.convert(P)
        else:
            P_val = float(P)
        if type(T) is str:
            T_val = self.convert(T)
        else:
            T_val = float(T)
        if type(I) is str:
            I_val = self.convert(I)
        else:
            I_val = float(I)
        self.send('ZCtrl.GainSet', 'float32', P_val,
                  'float32', T_val, 'float32', I_val)

    def ZGainPSet(self, P):
        if type(P) is str:
            P_val = self.convert(P)
        else:
            P_val = float(P)
        present = self.ZGainGet()
        self.ZGainSet(P_val, present['T'], present['I'])

    def ZGainTSet(self, T):
        if type(T) is str:
            T_val = self.convert(T)
        else:
            T_val = float(T)
        present = self.ZGainGet()
        self.ZGainSet(present['P'], T_val, present['I'])

    def PLLOutputSet(self, on=True):
        self.send('PLL.OutOnOffSet', 'int', 1, 'uint32', int(on))

    def PLLFreqShiftGet(self):
        parsedResponse = self.parse_response(
            self.send('PLL.FreqShiftGet', 'int', 1), 'float32')
        return parsedResponse['0']

    def PLLAmpCtrlSet(self, on=True):
        self.send('PLL.AmpCtrlOnOffSet', 'int', 1, 'uint32', int(on))

    def PLLPhasCtrlSet(self, on=True):
        self.send('PLL.PhasCtrlOnOffSet', 'int', 1, 'uint32', int(on))

    def ZCtrlOnOffGet(self):
        parsedResponse = self.parse_response(
            self.send('ZCtrl.OnOffGet'), 'uint32')
        return parsedResponse['0']

    def ZCtrlOnOffSet(self, on=True):
        self.send('ZCtrl.OnOffSet', 'uint32', int(on))

    def ZLimitsGet(self):
        parsedResponse = self.parse_response(
            self.send('ZCtrl.LimitsGet'), 'float32', 'float32')
        return {
            'high': parsedResponse['0'],
            'low': parsedResponse['1']
        }

    def ZLimitCheck(self):
        '''
        intermediate api
        '''
        z1 = self.TipZGet()
        z_limits = self.ZLimitsGet()
        z_max = z_limits['high']
        z_min = z_limits['low']
        if abs(z_max-z1)/z_max < 0.01:  # if the tip is at the piezo top limit
            self.Withdraw()
            logging.info('Piezo reached the z-high-limit, withdraw')
            raise nanonisException(
                'Piezo reached the z-high-limit', ExceptionType.Z_HIGH_LIMIT_REACHED)
        if abs(z1-z_min/z_min) < 0.01:
            logging.info('Piezo reached the z-low-limit, need auto approach')
            raise nanonisException(
                'Piezo reached the z-low-limit', ExceptionType.Z_LOW_LIMIT_REACHED)

    def ZLimitCheckWithAction(self):
        try:
            self.ZLimitCheck()
        except nanonisException as e:
            if e.code == ExceptionType.Z_HIGH_LIMIT_REACHED:
                self.Withdraw()
                self.MotorMoveSet('Z+', 1)
                self.AutoApproachSet()
            elif e.code == ExceptionType.Z_LOW_LIMIT_REACHED:
                self.Withdraw()
                self.AutoApproachSet()
            else:
                raise e
        finally:
            self.WaitForZCtrlWork()

    def BiasPulse(self, bais, width=0.1, wait=True):
        self.send('Bias.Pulse', 'uint32', int(wait), 'float32', float(
            width), 'float32', float(bais), 'uint16', 0, 'uint16', 0)

    def PiezoRangeGet(self):
        parsedResponse = self.parse_response(
            self.send('Piezo.RangeGet'), 'float32', 'float32', 'float32')
        return {
            'x': parsedResponse['0'],
            'y': parsedResponse['1'],
            'z': parsedResponse['2'],
        }

    def SignalsNamesGet(self):
        response = self.send('Signals.NamesGet')
        cursor = 4
        name_number = from_binary('int', response['body'][cursor: cursor+4])
        cursor += 4
        names = []
        for i in range(name_number):
            name_size = from_binary('int', response['body'][cursor: cursor+4])
            cursor += 4
            name = from_binary(
                'string', response['body'][cursor: cursor+name_size])
            if self.channel_name_filter(name):
                names.append(name)
            cursor += name_size
        return names

    def SignalIndexGet(self, name):
        if not hasattr(self, 'signal_chart'):
            self.signal_chart = self.SignalsNamesGet()
        if name not in self.signal_chart:
            raise nanonisException('Invalid signal name.')
        return self.signal_chart.index(name)

    def ScanStart(self, direction='down'):
        if direction == 'down':
            d = 0
        elif direction == 'up':
            d = 1
        else:
            raise nanonisException('Invalid direction. Please use down or up.')
        self.send('Scan.Action', 'uint16', 0, 'uint32', d)

    def ScanStop(self):
        self.send('Scan.Action', 'uint16', 1, 'uint32', 0)

    def ScanPause(self):
        self.send('Scan.Action', 'uint16', 2, 'uint32', 0)

    def ScanResume(self):
        self.send('Scan.Action', 'uint16', 3, 'uint32', 0)

    def ScanStatusGet(self):
        return self.parse_response(self.send('Scan.StatusGet'), 'uint32')['0']

    def ScanFrameSet(self, center_x, center_y, width, height, angle=0):
        self.send('Scan.FrameSet', 'float32', center_x, 'float32',
                  center_y, 'float32', width, 'float32', height, 'float32', angle)

    def ScanFrameData(self, channel_index, data_dir=1):
        '''
        need to be rewritten, use this version first, I don't want to think.
        '''
        response = self.send('Scan.FrameDataGrab', 'uint32',
                             channel_index, 'uint32', data_dir)
        cursor = 0
        name_length = from_binary('int', response['body'][cursor: cursor+4])
        cursor += 4
        channel_name = from_binary(
            'string', response['body'][cursor: cursor + name_length])
        cursor += name_length
        row_length = from_binary('int', response['body'][cursor: cursor + 4])
        cursor += 4
        col_length = from_binary('int', response['body'][cursor: cursor + 4])
        cursor += 4
        data = np.empty((row_length, col_length))
        for i in range(row_length):
            for j in range(col_length):
                data[i, j] = from_binary(
                    'float32', response['body'][cursor: cursor + 4])
                cursor += 4
        scan_direction = from_binary(
            'uint32', response['body'][cursor: cursor + 4])
        cursor += 4
        return {
            'data': data,
            'row': row_length,
            'col': col_length,
            'scan_direction': scan_direction,
            'channel_name': channel_name
        }

    def to_nano(self, value):
        return "{:.1f}n".format(value/1e-9)

    def channel_name_filter(self, channel_name: str):
        '''
        Local nanonis mechanine only have 8 Input/Output, so index with bigger than 8 should be removed.
        '''
        if channel_name.startswith('Input'):
            ind = int(channel_name[5:7])
            if ind > 8:
                return False
            else:
                return True
        elif channel_name.startswith('Output'):
            ind = int(channel_name[6:8])
            if ind > 8:
                return False
            else:
                return True
        else:
            return True

    def WaitEndOfScan(self):
        self.send('Scan.WaitEndOfScan', 'int', -1)

    def isZCtrlWork(self):
        '''
        make sure it is current mode.
        '''
        curr = self.CurrentGet()
        point = self.SetpointGet()
        if (abs(curr)-abs(point))/abs(point) < 0.1:
            return True
        else:
            return False

    def WaitForZCtrlWork(self):
        while not self.isZCtrlWork():
            time.sleep(1)

    
    def TipShaperStart(self):
        print(self.transmit(construct_command('TipShaper.PropsGet')))

    
    def TipShaperPropsSet(self, tip_lift='-300p', left_time_1='90m', bias_lift=3, bias_setting_t='90m'):
        tip_lift = self.try_convert(tip_lift)
        left_time_1 = self.try_convert(left_time_1)
        left_time_1 = self.try_convert(left_time_1)
        bias_lift = self.try_convert(bias_lift)
        bias_setting_t = self.try_convert(bias_setting_t)
        self.send('TipShaper.PropsSet', 'float32', 0.05, 'uint32', 0, 'float32', 0., 'float32', tip_lift,
                'float32', left_time_1, 'float32', bias_lift, 'float32', bias_setting_t, 'float32', 0., 
                'float32', 0.02, 'float32', 0.1, 'uint32', 0)


class Operate(metaclass=ABCMeta):
    '''
    The base class of all Operations.
    '''

    def __init__(self, session: NanonisController):
        self.session = session

    @abstractmethod
    def safety_check(self):
        pass

    @abstractmethod
    def _operate(self):
        pass

    def _reset(self):
        pass

    def do(self):
        if self.safety_check():
            result = self._operate()
            self._reset()
            return result
        else:
            raise nanonisException('Safety check failed.')


class ExceptionType(Enum):
    '''
    Exception types
    '''
    UNDEFINED = 0

    Z_TIP_TOUCHED = 101
    Z_HIGH_LIMIT_REACHED = 110
    Z_LOW_LIMIT_REACHED = 111

    PROCESS_FINISHED = 200


def setupLog():
    r'''
    simple logger setup
    '''

    LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
    DATE_FORMAT = "%Y/%d/%m %H:%M:%S"
    logging.basicConfig(level=logging.DEBUG,
                        format=LOG_FORMAT, datefmt=DATE_FORMAT)
