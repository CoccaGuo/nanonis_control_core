# core.py by CoccaGuo at 2022/05/16 16:45
from abc import ABCMeta, abstractmethod
from enum import Enum
import logging

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
            raise nanonisException('Invalid direction. Please use X+, X-, Y+, Y-, Z+, Z- expressions.')
        if direction == 5:
            raise nanonisException('Moving Z- is not Safe.')
        self.send('Motor.StartMove', 'uint32', direction, 'uint16', steps, 'uint32', 0, 'uint32', int(wait))
    

    def AutoApproachOpen(self):
        self.send('AutoApproach.Open')
        
    
    def AutoApproachSet(self, on=True):
        self.send('AutoApproach.OnOffSet', 'uint16', int(on))

    
    def AutoApproachGet(self):
        parsedResponse = self.parse_response(self.send('AutoApproach.OnOffGet'), 'uint16')
        return parsedResponse['0']

    
    def ZGainGet(self):
        parsedResponse = self.parse_response(self.send('ZCtrl.GainGet'), 'float32', 'float32', 'float32')
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
        present = self.ZGainGet()
        if type(I) is str:
            I_val = self.convert(I)
        else:
            I_val = float(I)
        self.send('ZCtrl.GainSet', 'float32', P_val, 'float32', T_val, 'float32', I_val)

    
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
        self.send('PLL.OutOnOffSet','int', 1, 'uint32', int(on))

    
    def PLLFreqShiftGet(self):
        parsedResponse = self.parse_response(self.send('PLL.FreqShiftGet', 'int', 1), 'float32')
        return parsedResponse['0']

    
    def PLLAmpCtrlSet(self, on=True):
        self.send('PLL.AmpCtrlOnOffSet', 'int', 1, 'uint32', int(on))

    
    def PLLPhasCtrlSet(self, on=True):
        self.send('PLL.PhasCtrlOnOffSet', 'int', 1, 'uint32', int(on))

    
    def ZCtrlOnOffGet(self):
        parsedResponse = self.parse_response(self.send('ZCtrl.OnOffGet'), 'uint32')
        return parsedResponse['0']

    
    def ZCtrlOnOffSet(self, on=True):
        self.send('ZCtrl.OnOffSet', 'uint32', int(on))

    
    def ZLimitsGet(self):
        parsedResponse = self.parse_response(self.send('ZCtrl.LimitsGet'), 'float32', 'float32')
        return {
            'high': parsedResponse['0'],
            'low': parsedResponse['1']
        }

    def BiasPulse(self, bais, width=0.1, wait=True):
        self.send('Bias.Pulse','uint32', int(wait), 'float32', float(width), 'float32', float(bais), 'uint16', 0, 'uint16', 0)
    

    def PiezoRangeGet(self):
        parsedResponse = self.parse_response(self.send('Piezo.RangeGet'), 'float32', 'float32', 'float32')
        return {
            'x': parsedResponse['0'],
            'y': parsedResponse['1'],
            'z': parsedResponse['2'],
        }

    
    def isZCtrlWork(self):
        '''
        make sure it is current mode.
        '''
        curr = self.CurrentGet()
        point = self.SetpointGet()
        if abs(curr)-abs(point)/abs(point) < 0.1:
            return True
        else: 
            return False
       


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

    def do(self):
        if self.safety_check():
            return self._operate()
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
    logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT, datefmt=DATE_FORMAT)