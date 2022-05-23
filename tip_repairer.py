
import sys
import logging
from core import NanonisController
from tasks.TipRepair import TipRepair


if __name__ == '__main__':
    direction_list = ['X+', 'X-', 'Y+', 'Y-']
    direction = 'Y-'

    # max area count of the direction
    area_count = 100

    if len(sys.argv) > 1:
        direction = sys.argv[1].upper()
        if direction not in direction_list:
            logging.warn('Invalid direction. Using Y-')
            direction = 'Y-'

    nanonis = NanonisController()
    TipRepair(nanonis, direction=direction, init_pulse_bias=7, area_counts=area_count).do()
