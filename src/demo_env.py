import gym
from gym import spaces
import numpy as np
import traci
import traci.constants as tc
from sumolib import checkBinary
from demo_00 import vehicle_init
from demo_00_listener import Listener_00
from typing import List

class demoEnv(gym.Env):
    metadata = {"render.modes": ["console"]}

    def __init__(self, config):
        super().__init__()
        traci.start(config)

        self._config = config

        self._step = 0
        self._numVehicles = 6
        self._numAgents = 2
        self._routeID = "route_0"
        
        # initialising vehicles
        self._fleetIDs = vehicle_init((self._numVehicles + self._numAgents), self._routeID)
        self._vehicleIDs = [self._fleetIDs[i] for i in range(self._numVehicles)]
        self._agentIDs = [self._fleetIDs[i] for i in range(self._numVehicles, len(self._fleetIDs))]

        # initialising listener 
        listener = Listener_00(self._vehicleIDs, self._routeID)
        traci.addStepListener(listener)
  
        self.observation_space = spaces.Dict({
            "agents": spaces.Dict({
                "agent_id": spaces.Tuple((
                    spaces.Box(low=0, high=100, shape=(2,), dtype=int), # posn
                    spaces.Discrete(200) # speed
                ))
            }),
            "vehicles": spaces.Dict({
                "vehicle_id": spaces.Tuple((
                    spaces.Box(low=0, high=100, shape=(2,), dtype=int), # posn
                    spaces.Discrete(200) # speed
                ))
            }),
        })

        no_vehicles = 6 # needs to be set
        high = np.array([np.inf] * no_vehicles * 3) # (x, y, speed) for each vehicle
        self.observation_space = spaces.Box(low=-high, high=high, dtype=np.float32)

        self.action_space = spaces.Box( # acceleration (a), where -3 < a < 1 (ms^-2)
            low=np.array([-3]), 
            high=np.array([1]), 
            dtype=np.float32
        )

    def _get_obs(self):
        ''' todo'''
        pass
        

    def _get_info(self):
        ''' todo'''
        pass
        
    def step(self, action):
        traci.simulationStep()
        traci.vehicle.setAcceleration(self._agentID, action[0])
        vehicle_info = [None] * len(self._vehicleIDs)

        posns = Listener_00.getPosns()
        speeds = Listener_00.getSpeeds()

        for id in self._vehicleIDs:
            id_index = int(id)
            vehicle_info[id_index] = (posns[id_index][0], posns[id_index][1], speeds[id_index])

        padded_obs = np.pad(vehicle_info, (0, len(self._vehicleIDs) * 3))
        observation = np.array(padded_obs)
        reward = self.calculate_reward()
        done = traci.simulation.getMinExpectedNumber() == 0
        info = {}

        return observation, reward, done, info

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        # Reset the state of the environment to an initial state
        traci.load(["-c", "demo_00.sumocfg"])
        for id in self._agentIDs:
            try:
                traci.vehicle.setSpeedMode(id, 0)
            except traci.TraCIException:
                pass
            
            try:
                traci.vehicle.setAcceleration(id, 0)
            except traci.TraCIException:
                pass

        return self.get_initial_observation()  # your initial observation

    def render(self, mode="console"):
        if mode == "console":
            print("environment state...")
    
    def close(self):
        traci.close()

    def get_initial_observations(self):
        traci.close()
        traci.start(self._config)
        # initialising vehicles
        self._fleetIDs = vehicle_init((self._numVehicles + self._numAgents), self._routeID)
        self._vehicleIDs = [self._fleetIDs[i] for i in range(self._numVehicles)]
        self._agentIDs = [self._fleetIDs[i] for i in range(self._numVehicles, len(self._fleetIDs))]

        # initialising listener 
        listener = Listener_00(self._vehicleIDs, self._routeID)
        traci.addStepListener(listener) 

    def calculate_reward():
        ''' todo'''
        pass