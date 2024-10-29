import gymnasium as gym
import gymnasium_env
from gymnasium_env.envs.sumo_env import DemoEnv
from gymnasium.utils.env_checker import check_env

def main():
    env = gym.make(
        'gymnasium_env/SumoEnv-v0',
        num_vehicles=5,
        num_agents=1,
        route_id="route_0"
    )
    check_env(env)


# import gym, gym_examples
# from gym.utils.env_checker import check_env

# def main():
#     env = gym.make(
#         "gym_examples/SumoEnv-v0", 
#         num_vehicles=5,
#         num_agents=1,
#         route_id="0"
#     )
#     check_env(env)

if __name__ == "__main__":
    main()