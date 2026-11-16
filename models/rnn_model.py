import math
import torch
import torch.nn as nn
import torch.nn.functional as F

from utils.config import normalize_model_name


class Autoencoder(nn.Module):
    """降噪自编码器（对齐 XiuzeZhou/RUL Transformer - CALCE.ipynb）。"""

    def __init__(self, input_size=16, hidden_dim=8, noise_level=0.0):
        super().__init__()
        if input_size < 1 or hidden_dim < 1:
            raise ValueError('自编码器输入维度与隐层维度必须为正整数')
        self.input_size = int(input_size)
        self.hidden_dim = int(hidden_dim)
        self.noise_level = float(noise_level)
        self.fc1 = nn.Linear(self.input_size, self.hidden_dim)
        self.fc2 = nn.Linear(self.hidden_dim, self.input_size)

    def encoder(self, x):
        return F.relu(self.fc1(x))

    def mask(self, x):
        if self.noise_level <= 0.0 or not self.training:
            return x
        return x + self.noise_level * torch.randn_like(x)

    def decoder(self, x):
        return self.fc2(x)

    def forward(self, x):
        corrupted = self.mask(x)
        encode = self.encoder(corrupted)
        decode = self.decoder(encode)
        return encode, decode


class PositionalEncoding(nn.Module):
    """正弦/余弦位置编码（对齐 XiuzeZhou/RUL）。"""

    def __init__(self, feature_len, feature_size, dropout=0.0):
        super().__init__()
        pe = torch.zeros(feature_len, feature_size)
        position = torch.arange(0, feature_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(
            torch.arange(0, feature_size, 2).float()
            * (-math.log(10000.0) / max(1, feature_size))
        )
        pe[:, 0::2] = torch.sin(position * div_term)
        if feature_size > 1:
            pe[:, 1::2] = torch.cos(position * div_term[:feature_size // 2])
        pe = pe.unsqueeze(0)
        self.register_buffer('pe', pe)
        self.drop = nn.Dropout(dropout) if dropout > 0.0 else None

    def forward(self, x):
        x = x + self.pe
        return self.drop(x) if self.drop is not None else x


class DeTransformer(nn.Module):
    """降噪自编码器 + Transformer 编码器网络（对齐 XiuzeZhou/RUL）。

    输入支持 ``(B, W, F)``（本工程标准格式）、``(B, W)`` 或 ``(B, K, W)``；
    训练时传 ``return_decode=True`` 返回 ``(pred, decode, x_rep)`` 用于计算
    预测 MSE 与重构损失的加权和，推理时默认仅返回 ``pred`` ``(B, 1)``。
    """

    def __init__(self, feature_size=64, hidden_dim=16, feature_num=16,
                 num_layers=3, nhead=1, dropout=0.0, noise_level=0.0,
                 input_size=1):
        super().__init__()
        if feature_size < 1:
            raise ValueError('窗口大小 feature_size 必须为正整数')
        if hidden_dim < 1 or num_layers < 1 or nhead < 1:
            raise ValueError('hidden_dim、num_layers 与 nhead 必须为正整数')
        if input_size < 1 or feature_num < 1:
            raise ValueError('特征维度与通道复制系数必须为正整数')

        self.feature_size = int(feature_size)
        self.hidden_dim = int(hidden_dim)
        self.input_size = int(input_size)
        # 单变量序列按 K 倍复制（参考仓库默认 K=16）；多变量输入则保持实际特征数 F
        effective_num = int(feature_num) if self.input_size == 1 else self.input_size
        self.feature_num = effective_num
        self.num_layers = int(num_layers)
        self.nhead = int(nhead)
        self.dropout = float(dropout)
        self.noise_level = float(noise_level)
        self.auto_hidden = max(1, self.feature_size // 2)

        if effective_num == 1:
            d_model = self.auto_hidden
            effective_nhead = self.nhead if d_model % self.nhead == 0 else 1
            self.pos = PositionalEncoding(
                feature_len=1, feature_size=self.auto_hidden, dropout=0.0)
        else:
            d_model = effective_num
            effective_nhead = self.nhead if d_model % self.nhead == 0 else 1
            self.pos = PositionalEncoding(
                feature_len=self.auto_hidden, feature_size=effective_num,
                dropout=0.0)

        encoder_layers = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=effective_nhead,
            dim_feedforward=self.hidden_dim,
            dropout=self.dropout,
            batch_first=True,
        )
        self.cell = nn.TransformerEncoder(encoder_layers, num_layers=self.num_layers)
        self.linear = nn.Linear(effective_num * self.auto_hidden, 1)
        self.autoencoder = Autoencoder(
            input_size=self.feature_size,
            hidden_dim=self.auto_hidden,
            noise_level=self.noise_level,
        )

    def _prepare_input(self, x):
        if x.ndim == 2:
            x_in = x.unsqueeze(1)
        elif (x.ndim == 3 and x.shape[2] == self.input_size
              and x.shape[1] == self.feature_size):
            x_in = x.transpose(1, 2)
        elif x.ndim == 3:
            x_in = x
        else:
            raise ValueError('DeTransformer 输入必须是二维或三维张量')

        if x_in.shape[1] == 1 and self.feature_num > 1:
            return x_in.repeat(1, self.feature_num, 1)
        return x_in

    def forward(self, x, return_decode=False):
        x_rep = self._prepare_input(x)
        batch_size = x_rep.shape[0]
        out, decode = self.autoencoder(x_rep)
        if self.feature_num > 1:
            out = out.reshape(batch_size, -1, self.feature_num)
        out = self.pos(out)
        out = self.cell(out)
        out = out.reshape(batch_size, -1)
        out = self.linear(out)
        if return_decode:
            return out, decode, x_rep
        return out


class Net(nn.Module):
    """深度学习主干网络：支持 RNN / GRU / LSTM 以及 DeTransformer（Transformer）。

    ``input_size`` 是特征数：单变量容量序列为 1，多特征（capacity / dq_v /
    CCCT / CVCT / resistance）时为 F。
    """

    CELLS = {'RNN': nn.RNN, 'GRU': nn.GRU, 'LSTM': nn.LSTM}
    TRANSFORMER_MODES = {'transformer': 'Transformer', 'detransformer': 'DeTransformer'}

    def __init__(self, hidden_dim=8, num_layers=1, mode='LSTM',
                 input_size=1, dropout=0.0, window_size=64,
                 nhead=1, feature_num=16, noise_level=0.0):
        super(Net, self).__init__()
        if isinstance(input_size, bool) or not isinstance(input_size, int) or input_size < 1:
            raise ValueError('输入特征数必须是正整数')
        raw_key = str(mode).strip().lower()
        if raw_key in self.TRANSFORMER_MODES:
            canon = self.TRANSFORMER_MODES[raw_key]
            self.hidden_dim = hidden_dim
            self.input_size = input_size
            self.num_layers = num_layers
            self.mode = canon
            self._transformer = DeTransformer(
                feature_size=window_size,
                hidden_dim=hidden_dim,
                feature_num=feature_num,
                num_layers=num_layers,
                nhead=nhead,
                dropout=dropout,
                noise_level=noise_level,
                input_size=input_size,
            )
            return

        mode = normalize_model_name(mode)
        if mode not in self.CELLS:
            raise ValueError(f'{mode} 不是循环神经网络模型')
        self.hidden_dim = hidden_dim
        self.input_size = input_size
        self.num_layers = num_layers
        self.mode = mode
        self._transformer = None
        self.cell = self.CELLS[mode](
            input_size=input_size,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.drop = nn.Dropout(dropout)
        self.linear = nn.Linear(hidden_dim, 1)

    def forward(self, x, return_decode=False):
        if self._transformer is not None:
            return self._transformer(x, return_decode=return_decode)
        out, _ = self.cell(x)
        return self.linear(self.drop(out[:, -1, :]))
