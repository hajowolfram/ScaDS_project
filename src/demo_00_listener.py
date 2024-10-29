import traci
import traci.constants as tc
from typing import List

class Listener_00(traci.StepListener):
    def __init__(self, vehicleIDs, routeID):
        super().__init__()
        self._vehicleIDs = vehicleIDs
        self._routeID = routeID
        self._speeds = [None] * len(vehicleIDs)
        self._posns = [None] * len(vehicleIDs)
    
    def getPosns(self) -> List[tuple]:
        return self._posns

    def getSpeeds(self) -> List[float]:
        return self._speeds

    def step(self, t) -> bool:
        for id in self._vehicleIDs:
            vehicle_index = int(id)

            try:
                pos = traci.vehicle.getPosition(id)
                self._posns[vehicle_index] = pos
            except traci.TraCIException:
                self._posns[vehicle_index] = None

            try:
                speed = traci.vehicle.getSpeed(id)
                self._speeds[vehicle_index] = speed
            except traci.TraCIException:
                self._speeds[vehicle_index] = None
                
        return True
    
       
