# replay buffer class
# need actor and critic networks
# need target actor and target critic networks
# batch normalisation
# deterministic policy
# soft updates 
# class for noise
'''
Pseudocode:
initialise critic and actor networks
initialise target networks with corresponding weights
initalise replay buffer
for episode:
    initialise a random noise N (UO-process) for exploration
    initial observation state 
    for t = 1, T do:
        pick action deterministically according to policy and noise
        execute action and observe reward, new state, and termination
        store experience (s,a,r,s') in replay buffer R
        sample a random minibatch of N transitions (s,a,r,s') from R
        set y = temporal difference to setup equation to optimise
        update critic by SGD/adam to minimise loss
        update actor policy using sampled PG
        update target networks (soft update)
'''