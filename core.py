# core.py by CoccaGuo at 2022/05/16 16:45
from abc import ABCMeta, abstractmethod

from interface import *


r'''
The base class of all Operations. Include Read(Get) and Write(Set)
'''
class Operate(metaclass=ABCMeta):

    def __init__(self, session):
            self.session = session

    @abstractmethod
    def safety_check(self):
        pass

    def __call__(self, *args, **kwargs):
        if self.safety_check():
            return self.session.send(*args, **kwargs)
        else :
            raise nanonisException('safety check failed')

class SafeOperate(Operate):

    def safety_check(self):
       return True

class NanonisController(nanonis_programming_interface):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
