from gym.envs.registration import register

register(
    id="gym_examples/SumoEnv-v0",
    entry_point="gym_examples.envs:DemoEnv" 
)
