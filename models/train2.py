import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import numpy as np

from preprocess2 import preprocess_lstm   # 预处理函数
from model2 import LSTMClassifier         # 模型
from sklearn.metrics import precision_score, recall_score, f1_score
import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt

import random

# =========================
# 1. 自定义Dataset
# =========================
class SequenceDataset(Dataset):
    def __init__(self, X, y):
        self.X = torch.tensor(X, dtype=torch.float32)
        self.y = torch.tensor(y, dtype=torch.float32)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]


# =========================
# 2. 评估函数
# =========================
def evaluate(model, dataloader, device):
    model.eval()

    all_preds = []
    all_labels = []

    with torch.no_grad():
        for X_batch, y_batch in dataloader:
            X_batch = X_batch.to(device)
            y_batch = y_batch.to(device)

            outputs = model(X_batch).squeeze()   # [batch]

            preds = (outputs > 0.3).float()

            # 收集结果（转到CPU + numpy）
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(y_batch.cpu().numpy())

    # ===== 计算指标 =====
    accuracy = np.mean(np.array(all_preds) == np.array(all_labels))

    precision = precision_score(all_labels, all_preds, zero_division=0)
    recall = recall_score(all_labels, all_preds, zero_division=0)
    f1 = f1_score(all_labels, all_preds, zero_division=0)

    return accuracy, precision, recall, f1


# =========================
# 3. 主训练流程
# =========================
def train():

    # ===== 参数 =====
    window_size = 5
    batch_size = 64
    hidden_dim = 64
    epochs = 10
    lr = 0.001
    # =========================
    # 记录训练过程
    # =========================
    train_losses = []
    train_accs = []
    test_accs = []
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("Using device:", device)

    # ===== 加载数据 =====
    X_train, y_train, raw_X, info = preprocess_lstm(
        "D:/Projects/Python/demo/data/train.csv",
        window_size=window_size
    )

    X_test, y_test, raw_X, _ = preprocess_lstm(
        "D:/Projects/Python/demo/data/test.csv",
        window_size=window_size
    )

    print("Train shape:", X_train.shape)
    print("Test shape:", X_test.shape)

    # ===== Dataset & DataLoader =====
    train_dataset = SequenceDataset(X_train, y_train)
    test_dataset = SequenceDataset(X_test, y_test)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=batch_size)

    # ===== 模型 =====
    model = LSTMClassifier(
        input_dim=info["feature_dim"],  # =4
        hidden_dim=hidden_dim
    ).to(device)

    # ===== 损失 & 优化器 =====
    criterion = nn.BCELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    # =========================
    # 训练循环
    # =========================
    for epoch in range(epochs):
        model.train()
        total_loss = 0

        for X_batch, y_batch in train_loader:
            X_batch = X_batch.to(device)
            y_batch = y_batch.to(device)

            outputs = model(X_batch).squeeze()

            loss = criterion(outputs, y_batch)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            total_loss += loss.item()

        # ===== 每轮评估 =====
        train_acc, train_p, train_r, train_f1 = evaluate(model, train_loader, device)
        test_acc, test_p, test_r, test_f1 = evaluate(model, test_loader, device)
        avg_loss = total_loss / len(train_loader)
        train_losses.append(avg_loss)
        train_accs.append(train_acc)
        test_accs.append(test_acc)
        print(f"Epoch [{epoch + 1}/{epochs}] "
              f"Loss: {avg_loss:.4f} "
              f"Train Acc: {train_acc:.4f} "
              f"P: {train_p:.4f} R: {train_r:.4f} F1: {train_f1:.4f} "
              f"Test Acc: {test_acc:.4f} "
              f"P: {test_p:.4f} R: {test_r:.4f} F1: {test_f1:.4f}")

    # ===== 保存模型 =====
    torch.save(model.state_dict(), "lstm_model.pth")
    print("模型已保存")

    epochs_range = range(1, epochs + 1)

    # =========================
    # 1. Loss 曲线
    # =========================
    plt.figure()
    plt.plot(epochs_range, train_losses, marker='o')
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.title("Training Loss Curve")
    plt.grid()

    plt.savefig("loss_curve.png", dpi=300, bbox_inches='tight')
    plt.close()

    # =========================
    # Accuracy曲线
    # =========================
    plt.figure()
    plt.plot(epochs_range, train_accs, marker='o', label="Train Accuracy")
    plt.plot(epochs_range, test_accs, marker='o', label="Test Accuracy")
    plt.xlabel("Epoch")
    plt.ylabel("Accuracy")
    plt.title("Accuracy Curve")
    plt.legend()
    plt.grid()

    plt.savefig("accuracy_curve.png", dpi=300, bbox_inches='tight')
    plt.close()

    seed = 42
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


# =========================
# 入口
# =========================
if __name__ == "__main__":
    train()