import pandas as pd

df = pd.read_csv("dataset.csv")

# 按时间排序
df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.sort_values(by="timestamp")

# 划分（前80%训练，后20%测试）
split_index = int(len(df) * 0.8)

train_df = df.iloc[:split_index]
test_df = df.iloc[split_index:]

train_df.to_csv("train.csv", index=False)
test_df.to_csv("test.csv", index=False)

print("划分完成！")