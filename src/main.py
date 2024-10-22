from demo_00 import setup_sumo, get_options, start_sumo, run_simulation
from gym.envs.registration import register

register(
    id="gym_examples/demo_env",
    entry_point="gym_examples.envs:demoEnv",
    max_episode=300,
)

def main():
    setup_sumo()    
    options = get_options()
    start_sumo(options)
    run_simulation()
    '''
    add the initialisation of the env package
    '''

if __name__ == "__main__":
    main()