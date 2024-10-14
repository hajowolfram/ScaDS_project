import torch
import numpy 
import traci
from torch import nn
from typing import List

class NeuralNetwork(nn.Module):
    def __init__(self, in_features, hidden_size, out_features):
        super().__init__()
        self.fc1 = nn.Linear(in_features, hidden_size)
        self.fc2 = nn.Linear(in_features, hidden_size) 
        self.fc3 = nn.Linear(hidden_size, out_features)
        self.relu = nn.ReLU()

    def forward(self, x):
        return self.fc3(self.relu(self.fc2(self.relu(self.fc1(x)))))
