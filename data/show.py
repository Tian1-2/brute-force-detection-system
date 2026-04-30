import pandas as pd

df = pd.read_csv("dataset.csv")
print(df.groupby("label")["status"].value_counts(normalize=True))

print(df["label"].value_counts())