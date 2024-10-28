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

class simulation:
    def __init__(self, num_vehicles, num_agents, route_id):
        self._N = num_vehicles + num_agents
        self._num_vehicles = num_vehicles
        self._num_agents = num_agents
        self._route_id = route_id
        self._step = 0
    
    def setup_sumo():
        if 'SUMO_HOME' in os.environ:
            tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
            sys.path.append(tools)
        else:
            sys.exit("SUMO_HOME path not set correctly")

    def get_options(self):
        opt_parser = optparse.OptionParser()
        opt_parser.add_option(
            "--nogui", 
            action="store_true",
            default=False,
            help="run the commandline version of sumo"
        )
        self._options, _ = opt_parser.parse_args()

    def vehicle_init(self) -> List[str]:
        vehicleIDs = [None] * self._num_vehicles
        
        for i in range(self._num_vehicles):
            vehicleIDs[i] = str(i)
        
        for id in vehicleIDs:
            traci.vehicle.add(id, self._route_id)
        
        return vehicleIDs

    def simulation_init(self):
        # initialising vehicles
        self._fleet_ids = self.vehicle_init(
            (self._num_vehicles + self._num_agents), 
            self._route_id
        )
        self._vehicle_ids = [self._fleet_ids[i] for i in range(self._num_vehicles)]
        self._agent_ids = [self._fleet_ids[i] for i in range(self._num_vehicles, len(self._fleet_ids))]

        # initialising listener 
        self._listener = Listener_00(self._vehicle_ids, self._route_id)
        traci.addStepListener(self._listener)

        # initalising DDPG agent
        
    def simulation_step(self) -> None:
        self._step += 1
        traci.simulation.step()
    
    def simulation_run(self, fast_forward: bool) -> None:
        # loop to state in which all vehicles are initalised/moving
        if fast_forward:
            while traci.simulation.getMinExpectedNumber() < self._num_vehicles:
                traci.simulation.step()
                step += 1

        # interface with agent while vehicles are active
        while traci.simulation.getMinExpectedNumber() > 0:
                
            if step % 1000 == 0:
                posns = self._listener.getPosns()
                speeds = self._listener.getSpeeds()

                print(f"==STEP==: {step}")
                
                print("--posns--")
                for posn in posns: 
                    if posn:
                        print(f"({posn[0]:.4f}, {posn[1]:.4f}), ")
                    else:
                        print("None, ")

                print("--speeds--")
                for speed in speeds:
                    if speed:
                        print(f"{float(speed):.2f}, ")
                    else:
                        print("none, ")
                    
            # interfacing with RL agent

            # agent is given current state info
            # agent chooses action
            # action is performed (longitudinal accel/deccel of AV chosen)
            '''
            TODO:
            agent_00.choose_action()
            '''

            traci.simulationStep()

            '''
            TODO:
            observe new state and reward
            agent_00.learn()
            
            every M iterations or so:
                agent_00.update_network_parameters()

            '''
            step += 1
        
        # ending simulation
        traci.close(False)
        sys.stdout.flush()

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

    def get_step(self) -> int:
        return self._step
    
    def get_ids(self) -> tuple[List[int], List[int]]:
        return self._vehicle_ids, self._agent_ids
    
    def is_terminated(self) -> bool:
        return not traci.simulation.getMinExpectedNumber() > 0
    
    def get_obs(self) -> tuple[List[float], List[float]]:
        speeds = self._listener.getSpeeds()
        posns = self._listener.getPosns()
        return speeds, posns
    
    def end_simulation(self) -> None:
        traci.close(False)
        sys.stdout.flush()
        
    def set_acceleration(self, action: List[float]) -> None:
        for id in self._agent_ids:
            traci.vehicle.setAcceleration(id, action[int(id)])
             