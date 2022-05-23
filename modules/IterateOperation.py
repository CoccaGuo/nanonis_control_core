# IterateOperation.py by CoccaGuo at 2022/05/17 14:18

import logging
import time
from core import ExceptionType, NanonisController, Operate
from interface import nanonisException


class IterateOperation(Operate):
    '''
    try to iterate a area to do something point by point.
    '''

    def __init__(self, session: NanonisController, gridX='200n', gridY='200n', padding='20n', interval_time=1):
        super().__init__(session)
        self.gridX = self.session.try_convert(gridX)
        self.gridY = self.session.try_convert(gridY)
        self.padding = self.session.try_convert(padding)
        ranges = self.session.PiezoRangeGet()
        self.x_range = ranges['x']
        self.y_range = ranges['y']
        self.x_max = int((self.x_range/2 - self.padding)//self.gridX)
        self.y_max = int((self.y_range/2 - self.padding)//self.gridY)
        self.x_recorder = 0
        self.y_recorder = 0 # the recorder of the current point index
        self.x = 0
        self.y = 0 # absolute position of the current point
        self.this = 0 # the processing point index
        self.points = (min(self.x_max, self.y_max)*2 + 1) ** 2
        self.interval = interval_time
        # use this to pass values during the iteration
        self.iter_cxt = {}

    def safety_check(self):
        # try to change the tip position at the center of the Z range
        z_limits = self.session.ZLimitsGet()
        z_max = z_limits['high']
        z_min = z_limits['low']
        while True:
            if not self.session.ZCtrlOnOffGet():
                self.session.ZCtrlOnOffSet(True)  # turn on Z controller
            z0 = self.session.TipZGet()
            if abs(z_max-z0/z_max) < 0.1:  # try to change the tip position at the center of the Z range
                logging.info(
                    'Z is {:.1e} now, too high, motor Z+ for 1 step.'.format(z0))
                self.session.Withdraw()
                self.session.MotorMoveSet('Z+', 1)
                self.session.AutoApproachSet()
            elif abs(z_min-z0/z_min) < 0.1:
                logging.info(
                    'Z is {:.1e} now, too low, auto approach.'.format(z0))
                self.session.Withdraw()
                self.session.AutoApproachSet()
            else:
                logging.info(
                    'Iterator Safety check passed, moving to area center.')
                self.session.Home()
                time.sleep(0.2)
                self.session.TipXYSet(0, 0)
                return True

    def _task(self):
        pass

    def _xy_move_and_do(self, x, y):
        if abs(x) <= self.x_max and abs(y) <= self.y_max:
            self.x = x * self.gridX
            self.y = y * self.gridY
            self.session.Home()
            n = self.session.to_nano
            logging.info('Moving to ({}, {})'.format(n(x*self.gridX), n(y*self.gridY)))
            self.session.TipXYSet(x*self.gridX, y*self.gridY)
            self.session.ZCtrlOnOffSet(True)
            self.session.WaitForZCtrlWork()
            time.sleep(self.interval)
            try:
                self.session.ZLimitCheck()
                self._task()
            except nanonisException as e:
                if e.code == ExceptionType.Z_HIGH_LIMIT_REACHED:
                    self.session.Withdraw()
                    self.session.MotorMoveSet('Z+', 1)
                    self.session.AutoApproachSet()
                elif e.code == ExceptionType.Z_LOW_LIMIT_REACHED:
                    self.session.Withdraw()
                    self.session.AutoApproachSet()
                else: raise e
            time.sleep(self.interval)


    def _operate(self):
        logging.info('{} points to process in this area.'.format(self.points))
        _x_directions = [1, 0, -1, 0]
        _y_directions = [0, 1, 0, -1]
        _direction_adder = 0
        _length = 1
        _line_indicator = 0
        _length_add_flag = False
        while self.this < self.points:
            self._xy_move_and_do(self.x_recorder, self.y_recorder)
            self.this += 1
            logging.info('{}/{} points processed.'.format(self.this, self.points))
            xd = _x_directions[_direction_adder % 4]
            yd = _y_directions[_direction_adder % 4]
            self.x_recorder += xd
            self.y_recorder += yd
            _line_indicator += 1
            if _line_indicator == _length:
                _line_indicator = 0
                _direction_adder += 1
                if _length_add_flag:
                    _length += 1
                _length_add_flag = not _length_add_flag
        