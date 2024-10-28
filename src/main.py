import gym, gym_examples
from gym.utils.env_checker import check_env

def main():
    env = gym.make(
        "gym_examples/SumoEnv-v0", 
        num_vehicles=5,
        num_agents=1,
        route_id="0"
    )
    check_env(env)

if __name__ == "__main__":
    main()