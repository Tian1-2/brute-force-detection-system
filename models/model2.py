import torch
import torch.nn as nn

class LSTMClassifier(nn.Module):
    def __init__(self, input_dim, hidden_dim, num_layers=1):
        super(LSTMClassifier, self).__init__()

        # LSTM 输入维度 = feature_dim（现在是3）
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True
        )

        # 分类层
        self.fc = nn.Linear(hidden_dim, 1)

        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        # x: [batch_size, seq_len, feature_dim]

        out, (h_n, c_n) = self.lstm(x)

        # 取最后一层的 hidden state
        out = h_n[-1]   # [batch_size, hidden_dim]

        out = self.fc(out)
        out = self.sigmoid(out)

        return out