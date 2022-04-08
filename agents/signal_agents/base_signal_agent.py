from lib2to3.pytree import Base
from agents.base_agent import BaseAgent
from threading import Thread, Lock

""" BaseSignalAgent class to facilitate signal agents"""
class BaseSignalAgent(BaseAgent):

    def __init__(self):
        super().__init__()
        self.signals = []

    def signal(self):
        pass

    def latest(self):
        return self.signals[-1] if(len(self.signals) > 0) else 0

