from core import NanonisController
from tasks.TipEtch import TipEtch


etch_level = '200u'
voltage = -10
input = 7
output = 2
resistance = 100
N = 4

TipEtch(NanonisController(), etch_level, voltage, input, output, resistance, N).do()