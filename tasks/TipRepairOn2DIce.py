# TipRepairOn2DIce.py by CoccaGuo at 2022/05/21 16:11

import logging
import time
import numpy as np
from core import ExceptionType, Operate
from interface import nanonisException
from modules.BaisOperation import MultiPulse
from modules.IterateOperation import IterateOperation
from modules.MotorOperation import ChangeArea
from modules.PLLOperation import CheckFrequencyShift
from modules.ScanOperation import Scan
from modules.TipShaper import TipShaper


class LowerAreaFinder(Scan):
    def __init__(self, session, center_x, center_y, width_x='150n', width_y='50n', angle=0, channel='Z (m)'):
        super().__init__(session, center_x, center_y, width_x, width_y, angle, channel)

    def _operate(self):
        super()._operate()
        while self.session.ScanStatusGet():
            time.sleep(1)
        data = self._get_scan_data()
        x_s, y_s = np.where(data==np.min(data))
        y_s, x_s = x_s[0], y_s[0]
        start_x = self.center_x - self.width_x/2
        start_y = self.center_y + self.width_y/2
        p_x = start_x + x_s/256*self.width_x
        p_y = start_y - y_s/256*self.width_y
        return (p_x, p_y)
            


class SingleAreaTipRepairer(IterateOperation):
    '''
    The class handles the tip repair process on a single area.
    Includes the following steps:
     - Iterate through the area
     - do tip repair
     - check frequency shift 
        - if frequency shift is too large, do multi pulse
        - if frequency shift is small, do tip shaper
    '''

    def __init__(self, session, gridX='200n', gridY='100n', padding='15n', interval_time=1):
        super().__init__(session, gridX, gridY, padding, interval_time)
        self.freq = 0

    def _task(self):
        pos = LowerAreaFinder(self.session, self.x, self.y).do()
        self.session.TipXYSet(pos[0], pos[1])
        time.sleep(1)
        self.session.ZCtrlOnOffSet(True)
        self.session.WaitForZCtrlWork()
        time.sleep(2)
        
        self.freq = CheckFrequencyShift(self.session).do()
        logging.info('Frequency shift now: {:.2f}'.format(self.freq))
        if CheckFrequencyShift.check_frequency_shift(self.freq):
            logging.critical(
                    '''\n**********************************************************
                    \n\n Frequency shift now is {:.2f} ! Check if it\'s OK to use.\n\n
                       **********************************************************
                    '''.format(self.freq))
            raise nanonisException(
                    "process finished", ExceptionType.PROCESS_FINISHED)
        
        if abs(self.freq) > 5:
            MultiPulse(self.session, 10).do()
        else:
            TipShaper(self.session).do()



class TipRepair(Operate):

    def __init__(self, session, direction='Y-', area_counts=100):
        super().__init__(session)
        self.direction = direction
        self.area_counts = area_counts

    def safety_check(self):
        logging.warn('Start Auto Tip Repairing Operation On 2D Ice')
        logging.info('Coarse Motion direction: {}'.format(self.direction))
        self.session.Withdraw()
        logging.info('Safety check: Withdraw')
        _curr = self.session.CurrentGet()
        if abs(_curr) > self.session.convert('1n'):
            logging.warn(
                'Current is too high: {:.2e}, do coarse Z+'.format(_curr))
            self.session.MotorMoveSet('Z+', 10)
        logging.info('Try auto approach')
        self.session.AutoApproachOpen()
        # wait till auto-approach is finished
        while self.session.AutoApproachGet():
            time.sleep(2)
        logging.info('Auto approach finished')
        self.session.Withdraw()
        logging.info('Basic Safety check finished.')
        time.sleep(1)
        return True

    def _operate(self):
        time_start = time.time()  # record the start time
        logging.info('Start tip repairing process.')
        count = 0
        while count < self.area_counts:
            try:
                SingleAreaTipRepairer(self.session).do()
                count += 1
                logging.warn('Area number {} finished'.format(count))
                ChangeArea(self.session).do()
            except nanonisException as e:
                if e.code == ExceptionType.PROCESS_FINISHED:
                    time_pass = time.time() - time_start
                    m, s = divmod(time_pass, 60)
                    h, m = divmod(m, 60)
                    logging.info(
                        'Total time cost: {}h {:2d}m {:2d}s'.format(h, m, s))
                    break
                else:
                    time_pass = time.time() - time_start
                    m, s = divmod(time_pass, 60)
                    h, m = divmod(m, 60)
                    logging.info(
                        'Total time cost: {}h {:2d}m {:2d}s'.format(h, m, s))
                    logging.fatal(
                        'Unexpected error: {}'.format(e))
                    self.session.Home()
                    break
            except Exception as e:
                logging.fatal(
                    'Unexpected error: {}'.format(e))
                self.session.Home()
                break
            finally:
                self.session.Home()
