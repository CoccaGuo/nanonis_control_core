# PLLOperation.py by CoccaGuo at 2022/05/16 20:35

import time
from core import *

class CheckFrequencyShift(Operate):
    def __init__(self, session: NanonisController):
        super().__init__(session)
    
    def safety_check(self):
        return True
    
    def _operate(self):
        logging.info('Checking frequency shift')
        self.session.PLLOutputSet(True)
        self.session.PLLAmpCtrlSet(True)
        self.session.PLLPhasCtrlSet(True)
        time.sleep(2)
        freq_shift = self.session.PLLFreqShiftGet()
        time.sleep(2)
        self.session.PLLOutputSet(False)
        self.session.PLLAmpCtrlSet(False)
        self.session.PLLPhasCtrlSet(False)
        logging.info('Frequency shift: {:.2f}'.format(freq_shift))
        return freq_shift
    
    @staticmethod
    def check_frequency_shift(freq_shift):
        if (freq_shift < -1 and freq_shift > -2):
            return True
        else:
            return False