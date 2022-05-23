import sys
import logging
from core import NanonisController
from tasks.TipRepairOn2DIce import TipRepair


if __name__ == '__main__':
    direction_list = ['X+', 'X-', 'Y+', 'Y-']
    direction = 'Y-'

    area_count = 100

    if len(sys.argv) > 1:
        direction = sys.argv[1].upper()
        if direction not in direction_list:
            logging.warn('Invalid direction. Using Y-')
            direction = 'Y-'

    nanonis = NanonisController()
    TipRepair(nanonis, direction=direction, area_counts=area_count).do()