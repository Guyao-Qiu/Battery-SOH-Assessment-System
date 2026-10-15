import torch.nn as nn
from utils.config import normalize_model_name


class Net(nn.Module):
    """单层 RNN / GRU / LSTM，末端线性层输出下一个容量。

    ``input_size`` 是特征数：单变量容量序列为 1，多特征（capacity / dq_v /
    CCCT / CVCT / resistance）时为 F。
    """

    CELLS = {'RNN': nn.RNN, 'GRU': nn.GRU, 'LSTM': nn.LSTM}

    def __init__(self, hidden_dim=8, num_layers=1, mode='LSTM',
                 input_size=1, dropout=0.0):
        super(Net, self).__init__()
        mode = normalize_model_name(mode)
        if mode not in self.CELLS:
            raise ValueError(f'{mode} 不是循环神经网络模型')
        if isinstance(input_size, bool) or not isinstance(input_size, int) or input_size < 1:
            raise ValueError('输入特征数必须是正整数')
        self.hidden_dim = hidden_dim
        self.input_size = input_size
        self.num_layers = num_layers
        self.mode = mode
        # 直接建目标单元，不再「先建 LSTM 再替换」造成浪费
        self.cell = self.CELLS[mode](
            input_size=input_size,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.drop = nn.Dropout(dropout)
        self.linear = nn.Linear(hidden_dim, 1)

    def forward(self, x):
        out, _ = self.cell(x)
        return self.linear(self.drop(out[:, -1, :]))
