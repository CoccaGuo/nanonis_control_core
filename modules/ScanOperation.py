# ScanOperation.py by CoccaGuo at 2022/05/21 15:21

import logging
import time
from core import NanonisController, Operate


class Scan(Operate):
    def __init__(self, session: NanonisController, center_x, center_y, width_x, width_y, angle=0, channel='Z (m)'):
        super().__init__(session)
        self.center_x = self.session.try_convert(center_x)
        self.center_y = self.session.try_convert(center_y)
        self.width_x = self.session.try_convert(width_x)
        self.width_y = self.session.try_convert(width_y)
        self.angle = angle
        self.channel = channel

    def safety_check(self):
        s = self.session
        s.Home()
        s.TipXYSet(self.center_x, self.center_y+self.width_y/2)
        s.ScanFrameSet(self.center_x, self.center_y, self.width_x, self.width_y, self.angle)
        s.ZCtrlOnOffSet()
        s.WaitForZCtrlWork()
        time.sleep(2) # wait for Z to settle
        return True

        
    def _operate(self):
        s = self.session
        n = s.to_nano
        logging.info('Scanning start at {}, {}, Size {}.'.format(n(self.center_x), n(self.center_y), n(self.width_x)))
        s.ZCtrlOnOffSet()
        s.WaitForZCtrlWork()
        time.sleep(4)
        s.ScanStart()
        time.sleep(2)
    
    def _get_scan_data(self, channel=None):
        s = self.session
        if channel is None:
            channel = self.channel
        ind = s.SignalIndexGet(channel)
        data = s.ScanFrameData(ind)['data']
        return data
    