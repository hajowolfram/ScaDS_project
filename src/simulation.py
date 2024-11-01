import os
import sys
import optparse
import traci
import traci._vehicletype
import traci.constants as tc
from sumolib import checkBinary
from demo_00_listener import Listener_00
from typing import List
from dotenv import load_dotenv

load_dotenv()

class Simulation:
    def __init__(self, num_vehicles, num_agents, route_id):
        self._N = num_vehicles + num_agents
        self._num_vehicles = num_vehicles
        self._num_agents = num_agents
        self._route_id = route_id
        self._step = 0
        self._options = None
        self._fleet_ids = None
        self._agent_ids = None
        self._vehicle_ids = None
    
    def setup_sumo(self) -> None:
        if 'SUMO_HOME' in os.environ:
            tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
            sys.path.append(tools)
        else:
            print("SUMO_HOME path not set but continue...")
            # sys.exit("SUMO_HOME path not set correctly")

    def get_options(self) -> None:
        opt_parser = optparse.OptionParser()
        opt_parser.add_option(
            "--nogui", 
            action="store_true",
            default=False,
            help="run the commandline version of sumo"
        )
        self._options, _ = opt_parser.parse_args()
        
    def start_sumo(self) -> None:
        root_path = os.getenv("SUMO_PROJECT_PATH")
        config_file_path = os.path.join(root_path, "config/demo_00.sumocfg")
        output_file_path = os.path.join(root_path, "output/tripinfo.xml")

        if not os.path.exists(config_file_path):
            sys.exit(f"config file not found at {config_file_path}")
        if not os.path.exists(output_file_path):
            sys.exit(f"output file not found at {output_file_path}")

        if self._options.nogui:
            sumoBinary = checkBinary('sumo')
        else:
            sumoBinary = checkBinary('sumo-gui')
        
        sumoCmd = [
            sumoBinary, 
            "-c", 
            config_file_path, 
            "--tripinfo-output", 
            output_file_path
        ]
        traci.start(sumoCmd)

    def _vehicle_init(self) -> List[str]:
        vehicleIDs = [None] * self._num_vehicles
        
        for i in range(self._num_vehicles):
            vehicleIDs[i] = str(i)
        
        for id in vehicleIDs:
            traci.vehicle.add(id, self._route_id)
        
        return vehicleIDs

    def simulation_init(self) -> None:
        # initialising vehicles
        self._fleet_ids = self._vehicle_init()
        self._vehicle_ids = [self._fleet_ids[i] for i in range(self._num_vehicles)]
        self._agent_ids = [self._fleet_ids[i] for i in range(self._num_vehicles, len(self._fleet_ids))]

        # initialising listener 
        self._listener = Listener_00(self._vehicle_ids, self._route_id)
        traci.addStepListener(self._listener)

        # initalising DDPG agent --> responsibility of the environment
        
    def simulation_step(self) -> None:
        self._step += 1
        traci.simulation.step()
    
    def fast_forward(self) -> None:
        while traci.simulation.getMinExpectedNumber() < self._num_vehicles:
            traci.simulation.step()
            step += 1
        
    def end_simulation(self) -> None:
        traci.close(False)
        sys.stdout.flush()

    def get_step(self) -> int:
        return self._step
    
    def get_ids(self) -> tuple[List[int], List[int]]:
        return self._vehicle_ids, self._agent_ids
    
    def get_terminated(self) -> bool:
        return not traci.simulation.getMinExpectedNumber() > 0
    
    def get_obs(self) -> tuple[List[float], List[float]]:
        speeds = self._listener.getSpeeds()
        posns = self._listener.getPosns()
        return speeds, posns
        
    def set_acceleration(self, action: List[float]) -> None:
        '''todo: add error handling'''
        for id in self._agent_ids:
            traci.vehicle.setAcceleration(id, action[int(id)])
