# TipRepair.py by CoccaGuo at 2022/05/17 17:00

import logging
import time
from core import ExceptionType, Operate
from interface import nanonisException
from modules.IterateOperation import IterateOperation
from modules.BaisOperation import MultiPulse
from modules.MotorOperation import ChangeArea
from modules.PLLOperation import CheckFrequencyShift


class SingleAreaTipRepairer(IterateOperation):
    '''
    The class handles the tip repair process on a single area.
    Includes the following steps:
     - Iterate through the area
     - do pulses
     - check frequency shift
    '''

    def __init__(self, session, gridX='200n', gridY='200n', padding='15n', interval_time=1, init_pulse=7):
        super().__init__(session, gridX, gridY, padding, interval_time)
        self.multi_pulse = MultiPulse(self.session, init_pulse)

    def _task(self):
        if (self.this % 5 == 1 and self.multi_pulse.value > 8) or (self.this % 3 == 1 and self.multi_pulse.value > 9):
            freq = CheckFrequencyShift(self.session).do()
            logging.info('Frequency shift now: {:.2f}'.format(freq))
            if CheckFrequencyShift.check_frequency_shift(freq):
                logging.critical(
                    '''**********************************************************
                    \n\n Frequency shift now is {:.2f} ! Check if it\'s OK to use.\n\n
                       **********************************************************
                    '''.format(freq))
                raise nanonisException(ExceptionType.PROCESS_FINISHED)
        else:
            counts = self.multi_pulse.do()
            logging.info('Pulse counts: {} at position ({}, {})'.format(
                counts, self.x_recorder, self.y_recorder))
            if counts > 3 and self.multi_pulse.value < 10:
                self.multi_pulse.value += 1
                logging.warn('Pulse bais set to {}'.format(
                    self.multi_pulse.value))

    def _operate(self):
        try:
            super()._operate()
            return self.multi_pulse.value
        except nanonisException as e:
            if e.code == ExceptionType.Z_TIP_TOUCHED:
                self.session.MotorMoveSet('Z+', 5)
                logging.error(
                    'Z tip touched, move motor Z+ up. Goto next area.')
                return self.multi_pulse.value
            else:
                raise e


class TipRepair(Operate):

    def __init__(self, session, direction='Y-', init_pulse_bias=7):
        super().__init__(session)
        self.direction = direction
        self.pulse_bias = init_pulse_bias

    def safety_check(self):
        logging.warn('Start Auto Tip Repairing Operation')
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
        logging.info('Start tip repairing process')
        while True:
            try:
                self.pulse_bias = SingleAreaTipRepairer(
                    self.session, init_pulse=self.pulse_bias).do()
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
                    logging.fatal(
                        'Unexpected error: {}'.format(e.with_traceback()))
                    self.session.Withdraw()
                    raise e
            except Exception as e:
                logging.fatal(
                    'Unexpected error: {}'.format(e.with_traceback()))
                self.session.Withdraw()
