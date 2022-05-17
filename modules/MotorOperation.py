# MotorOperation.py by CoccaGuo at 2022/05/16 19:09

import time
from core import *


class ChangeArea(Operate):
    def __init__(self, session, direction='Y-', Zsteps=100, XYsteps=100, P='40p', setpoint='40p', interval_time=2):
        super().__init__(session)
        self.direction = direction
        self.Zsteps = Zsteps
        self.XYsteps = XYsteps
        self.P = P
        self.setpoint = setpoint
        self.interval = interval_time

    def safety_check(self):
        self.session.Withdraw()
        logging.info('Safety check: Withdraw')
        return True

    def _operate(self):
        logging.info('Start to change area')
        self.session.MotorMoveSet('Z+', self.Zsteps)  # rise the tip
        logging.info('Raised the tip for {} steps'.format(self.Zsteps))
        time.sleep(self.interval)
        self.session.MotorMoveSet(self.direction, self.XYsteps)  # change area
        time.sleep(self.interval)
        logging.info('Changed area at {} for {} steps'.format(
            self.direction, self.XYsteps))
        prev_gain = self.session.ZGainGet()
        prev_setpnt = self.session.SetpointGet()
        logging.info('Changed proportional to {:.2e}, setpoint to {:.2e}'.format(
            self.session.try_convert(self.P), self.session.try_convert(self.setpoint)))
        self.session.SetpointSet(self.P)  # prepare for approach
        self.session.ZGainPSet(self.setpoint)
        self.session.AutoApproachOpen()
        self.session.AutoApproachSet()
        logging.warn('Start to approach...')

        # wait till auto-approach is finished
        while self.session.AutoApproachGet():
            time.sleep(2)

        self.session.Withdraw()
        logging.info('Approach finished')
        self.session.ZGainSet(prev_gain['P'], prev_gain['T'], prev_gain['I'])
        self.session.SetpointSet(prev_setpnt)
        logging.info('Reset proportional to {:.2e}, setpoint to {:.2e}'.format(
            prev_gain['P'], prev_setpnt))
