# TipEtch.py by CoccaGuo at 2022/05/19 14:00

import time
import matplotlib.pyplot as plt
from core import Operate


class TipEtch(Operate):
    def __init__(self, session, etch_level='200u', volt=-10, input=7, output=2, resistance=100, N=4):
        super().__init__(session)
        self.etch_level = self.session.try_convert(etch_level)
        self.volt = self.session.try_convert(volt)
        self.input = input
        self.output = output
        self.resistance = resistance
        self.N = N

    def curr(self):
        ch = self.input - 1
        volt = self.session.parse_response(self.session.send('Signals.ValGet', 'int', ch, 'uint32', 1), 'float32')['0']
        return volt / self.resistance
    
    def bias(self, value):
        self.session.send('UserOut.ValSet', 'int', self.output, 'float32', value)

    def _operate(self):
        current_list = []
        self.bias(self.volt)
        i = self.curr()
        count = 0
        while count < self.N:
            i = self.curr()
            if abs(i) < self.etch_level:
                count += 1
            current_list.append(i*1000)
            time.sleep(0.1)
        self.bias(0)
        plt.plot(current_list)
        plt.title('Tip Etching Curve')
        plt.xlabel('Time (0.1s)')
        plt.ylabel('Current (mA)')
        plt.show()

    def safety_check(self):
        self.session.send('UserOut.ModeSet', 'int', self.output, 'uint16', 0)
        return True


