# BaisOperation.py by CoccaGuo at 2022/05/16 21:17

import logging
import time
from core import ExceptionType, Operate
from interface import nanonisException


class MultiPulse(Operate):
    '''
    duration: unit: s
    count: 0: do until Z elevated
          >0: do count times
    '''

    def __init__(self, session, value, count=0, duration=2, tip_touched_current='5n'):
        super().__init__(session)
        self.value = self.session.try_convert(value)
        self.count = count
        self.duration = self.session.try_convert(duration)
        self.tip_touched_current = self.session.try_convert(tip_touched_current)

    def safety_check(self):
        if (self.session.ZCtrlOnOffGet() == 0):
            self.session.ZCtrlOnOffSet()
            logging.warning('Z-control is off, turn on Z-control')
            self.session.WaitForZCtrlWork()
            time.sleep(3)
            return True
        elif (self.count != 0):
            logging.warning('Manual pulse is not safe present, avoid to use.')
            return False
        else: 
            return True

    def _operate(self):
        if self.count > 0:
            for i in range(self.count):
                self.session.BiasPulse(self.value)
                time.sleep(self.duration)
            logging.info('Pulse finished {} times at {:.1f} V'.format(
                self.count, self.value))
            return self.count
        else:
            return self._auto_pulse()

    def _auto_pulse(self):
        s = self.session
        count = 0
        while True:
            z0 = s.TipZGet()
            s.BiasPulse(self.value)
            count += 1
            time.sleep(0.2)  # wait for 200ms  to see the change on Z
            z1 = s.TipZGet()
            z_limits = s.ZLimitsGet()
            z_max = z_limits['high']
            z_min = z_limits['low']
            if abs(z_max-z1)/z_max < 0.01:  # if the tip is at the piezo top limit
                _curr = abs(s.CurrentGet())
                if _curr > self.tip_touched_current:  # tip touched the substrate
                    s.Withdraw()
                    logging.warning(
                        'Tip touched the substrate with current {:.1e}'.format(_curr))
                    # need to withdraw, raise the tip, and change area
                    raise nanonisException(
                        'Tip touched the substrate with current {:.1e}'.format(_curr), ExceptionType.Z_TIP_TOUCHED) 
                else:  # tip not touch the substrate but need to withdraw
                    s.Withdraw()
                    logging.info('Piezo reached the z-high-limit, withdraw')
                    raise nanonisException('Piezo reached the z-high-limit', ExceptionType.Z_HIGH_LIMIT_REACHED)
            if abs(z1-z_min/z_min) < 0.01:
                logging.info('Piezo reached the z-low-limit, need auto approach')
                raise nanonisException('Piezo reached the z-low-limit', ExceptionType.Z_LOW_LIMIT_REACHED)
            diff = z1 - z0
            if diff <= 0:
                logging.info('Z-position not elevated, continue to pulse')
                time.sleep(self.duration)
            else:
                logging.info(
                    'Z-position elevated by {:.2e} m, stop'.format(diff))
                return count
