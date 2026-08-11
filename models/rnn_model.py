import torch.nn as nn
from utils.config import normalize_model_name


class Net(nn.Module):
    def __init__(self, hidden_dim=8, num_layers=1, mode='LSTM'):
        super(Net, self).__init__()
        mode = normalize_model_name(mode)
        if mode not in ('RNN', 'GRU', 'LSTM'):
            raise ValueError(f'{mode} 不是循环神经网络模型')
        self.hidden_dim = hidden_dim
        self.cell = nn.LSTM(input_size=1, hidden_size=hidden_dim, num_layers=num_layers, batch_first=True)
        if mode == 'GRU':
            self.cell = nn.GRU(input_size=1, hidden_size=hidden_dim, num_layers=num_layers, batch_first=True)
        elif mode == 'RNN':
            self.cell = nn.RNN(input_size=1, hidden_size=hidden_dim, num_layers=num_layers, batch_first=True)
        self.linear = nn.Linear(hidden_dim, 1)

    def forward(self, x):
        out, _ = self.cell(x)
        out = out[:, -1, :]
        out = self.linear(out)
        return out
