import sys
import time
from app.controller import Controller

"""Run the controller of the MAS until keyboard interrupt"""
def run():
    try:
        controller = Controller()
        controller.register_agents()
        controller.start_agents()
        while True:
            time.sleep(1)
    except KeyboardInterrupt as e:
        controller.stop_agents()
        print('The server has been shutdown gracefully')
        sys.exit()