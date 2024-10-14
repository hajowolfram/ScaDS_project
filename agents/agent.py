import torch
import numpy 
import traci
from typing import List

class agent_00():
    def __init__(self, vehicleIDs, avID):
        self._vehicleIDs = vehicleIDs
        self._numVehicles = len(vehicleIDs)
        self._avID = avID
        self._step = 0
        self._state = []
    
    def observe(self, vehicleSpeeds: List[float], vehiclePosns: List[tuple]):
        self._state[self._step] = [vehicleSpeeds, vehiclePosns]
    
    def act(self, action: float) -> float:
        '''
        given an action, update state, get reward, check if terminated
        '''

    def reward(self, vehicleSpeeds) -> float:
        '''calculates the reward based on average speed of all vehicles
            Args:
            Returns:
        '''
        for i in range(self._numVehicles):
            reward += traci.vehicle.getSpeed(self._vehicleIDs[i])
            '''
            TODO: refactor to include the AV speed as well
            '''
        return (reward / self._numVehicles)

    def action(self):
        '''returns longitudinal acceleration value for AV
            Args:
            Returns:            
        '''
        accel, time = 0, 0
        traci.vehicle.setAcceleration(id, accel, time)
        
    def is_terminal(self):
        for value in self._state:
            if value == None:
                c+=1