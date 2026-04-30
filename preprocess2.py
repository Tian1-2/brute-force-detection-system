import pandas as pd
import numpy as np

def preprocess_lstm(file_path, window_size=5, include_ip_change=True):
    """
    处理原始日志csv，生成LSTM可训练序列

    参数:
        file_path: str, CSV文件路径
        window_size: int, 每个序列长度
        include_ip_change: bool, 是否加入IP变化特征
    返回:
        sequences: list of list, 序列特征
        labels: list, 对应标签
        feature_info: dict, 特征映射信息
    """
    df = pd.read_csv(file_path)

    # 映射用户ID,这个原来是干什么的来着
    #user_map = {u: i for i, u in enumerate(df["user"].unique())}

    sequences = []
    labels = []
    raw_sequences = []

    # 用于存每个用户的状态
    user_data = {}

    for _, row in df.iterrows():
        user = row["user"]
        status = row["status"]
        ip = row["ip"]
        label = int(row["label"])
        timestamp = pd.to_datetime(row["timestamp"])

        if user not in user_data:
            user_data[user] = {
                "fail_count": 0,
                "last_ip": ip,
                "last_time": None,
                "seq": []
            }

        # 连续失败次数
        if status == "fail":
            user_data[user]["fail_count"] += 1
        else:
            user_data[user]["fail_count"] = 0
        fail_count_norm = min(user_data[user]["fail_count"], 10) / 10

        # IP变化特征（0/1）
        ip_change = 0
        if include_ip_change:
            if ip != user_data[user]["last_ip"]:
                ip_change = 1
            user_data[user]["last_ip"] = ip

        last_time = user_data[user]["last_time"]
        if last_time is None:
            time_diff = 0
        else:
            time_diff = (timestamp - last_time).total_seconds()
        user_data[user]["last_time"] = timestamp
        time_diff_norm = min(time_diff, 60) / 60

        # 构建特征向量
        feature = [
            #user_map[user],             # 用户ID
            1 if status == "fail" else 0,  # 登录失败
            fail_count_norm,  # 连续失败次数
            time_diff_norm   #时间差
        ]

        if include_ip_change:
            feature.append(ip_change)

        # 保存序列
        user_data[user]["seq"].append((feature, label,{
            "user": user,
            "timestamp": timestamp,
            "ip": ip,
            "status": status
        }))

    # 构造滑动窗口序列
    for user in user_data:
        seq_data = user_data[user]["seq"]
        for i in range(len(seq_data) - window_size + 1):
            seq = [x[0] for x in seq_data[i:i+window_size]]
            raw_seq = [x[2] for x in seq_data[i:i+window_size]]
            seq_label = seq_data[i + window_size - 1][1]  # 最后一条的label作为label
            sequences.append(seq)
            labels.append(seq_label)
            raw_sequences.append(raw_seq)

    # 转为numpy数组，方便直接输入LSTM
    sequences = np.array(sequences, dtype=np.float32)
    labels = np.array(labels, dtype=np.int64)

    feature_info = {
        #"user_map": user_map,
        "feature_dim": sequences.shape[2]
    }

    return sequences, labels, raw_sequences, feature_info


# =====================
# 测试代码
# =====================
if __name__ == "__main__":
    X, y, raw_X, info = preprocess_lstm("D:/Projects/Python/demo/data/train.csv", window_size=5)
    print("序列示例shape:", X.shape)  # (num_sequences, window_size, feature_dim)
    print(X[:10])
    print("标签示例:", y[:10])
    print("特征维度:", info["feature_dim"])
    print(raw_X[:10])
    #print("用户映射:", info ["user_map"])