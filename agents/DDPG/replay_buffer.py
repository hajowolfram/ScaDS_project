import numpy as np

class ReplayBuffer():
    def __init__(self, max_size, input_shape, n_actions):
        self.buffer_size = max_size
        self.buffer_count = 0
        self.state_memory = np.zeros((self.buffer_size, *input_shape))
        self.new_state_memory = np.zeros((self.buffer_size, *input_shape))
        self.action_memory = np.zeros((self.buffer_size, *n_actions))
        self.reward_memory = np.zeros(self.buffer_size)
        self.terminal_memory = np.zeros(self.buffer_size, dtype=np.bool) 
    
    def store_experience(self, state, action, reward, new_state, terminated=False):
        index = self.buffer_count % self.buffer_size
        
        self.state_memory[index] = state
        self.new_state_memory[index] = new_state
        self.reward_memory[index] = reward
        self.action_memory[index] = action
        self.terminal_memory[index] = terminated
        self.buffer_count += 1
        '''
        why is buffer size predetermined?
        why the modulus operation
        '''
        
    def buffer_sample(self, batch_size):
        max_index = min(self.buffer_count, self.buffer_size)
        batch = np.random.choice(max_index, batch_size)

        states = self.state_memory[batch]
        actions = self.action_memory[batch]
        rewards = self.reward_memory[batch]
        new_states = self.new_state_memory[batch]
        terminated = self.terminal_memory[batch]

        return states, actions, rewards, new_states, terminated