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

def setup_sumo():
    if 'SUMO_HOME' in os.environ:
        tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
        sys.path.append(tools)
    else:
        sys.exit("SUMO_HOME path not set correctly")

def get_options():
    opt_parser = optparse.OptionParser()
    opt_parser.add_option(
        "--nogui", 
        action="store_true",
        default=False,
        help="run the commandline version of sumo"
    )
    options, args = opt_parser.parse_args()
    return options

def vehicle_init(N: int, routeID: str = "") -> List[str]:
    ''' initialises N vehicles at random positions around the circle
    Args:
        N: number of distinct vehicles to be initiated
        routeID: which route to initiate vehicles on 
    Returns:
        vehicleIDs: list of vehicleID strings
    '''
    vehicleIDs = [None] * N
    for i in range(N):
        vehicleIDs[i] = str(i)

    for id in vehicleIDs:
        traci.vehicle.add(id, routeID)

    return vehicleIDs

def run_simulation():
    step = 0
    numVehicles = 6
    numAgents = 2
    routeID = "route_0"
    
    # initialising vehicles
    fleetIDs = vehicle_init((numVehicles + numAgents), routeID)
    vehicleIDs = [fleetIDs[i] for i in range(numVehicles)]
    agentIDs = [fleetIDs[i] for i in range(numVehicles, len(fleetIDs))]

    # initialising listener 
    listener = Listener_00(vehicleIDs, routeID)
    traci.addStepListener(listener)

    # initalise DDPG agent

    '''
    TODO agent_setup(alpha, beta, input_dims, tau, n_actions)
    ALTERNATIVELY: subclass gym.env with traci API 
    attributes:
    - action_space
    - observation_space
    - action_to_direction
    - 
    '''

    # loop to state in which all vehicles are initalised/moving
    while traci.simulation.getMinExpectedNumber() < numVehicles:
        traci.simulation.step()
        step += 1

    # interface with agent while vehicles are active
    while traci.simulation.getMinExpectedNumber() > 0:
             
        if step % 1000 == 0:
            posns = listener.getPosns()
            speeds = listener.getSpeeds()

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

def start_sumo(options):

    root_path = os.getenv("SUMO_PROJECT_PATH")
    config_file_path = os.path.join(root_path, "config/demo_00.sumocfg")
    output_file_path = os.path.join(root_path, "output/tripinfo.xml")

    if not os.path.exists(config_file_path):
        sys.exit(f"config file not found at {config_file_path}")
    if not os.path.exists(output_file_path):
        sys.exit(f"output file not found at {output_file_path}")

    if options.nogui:
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
