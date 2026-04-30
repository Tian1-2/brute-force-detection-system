import torch

WINDOW_SIZE = 5

class DetectionEngine:
    def __init__(self, model, threshold=0.5):
        self.model = model
        self.threshold = threshold
        self.user_state = {}

    def reset(self):
        """清空状态（重新跑一轮）"""
        self.user_state = {}

    def _init_user(self, user, ip, timestamp):
        self.user_state[user] = {
            "seq": [],
            "fail_count": 0,
            "state": "NORMAL",
            "attack_count": 0,
            "max_prob": 0,
            "last_ip": ip,
            "last_time": timestamp
        }

    def _extract_feature(self, u, status, ip, timestamp):
        # 连续失败
        if status == "fail":
            u["fail_count"] += 1
        else:
            u["fail_count"] = 0

        # IP变化
        ip_change = 1 if ip != u["last_ip"] else 0
        u["last_ip"] = ip

        # 时间间隔（分钟）
        time_diff = (timestamp - u["last_time"]).total_seconds() / 60
        u["last_time"] = timestamp

        feature = [
            1 if status == "fail" else 0,
            min(u["fail_count"], 10) / 10,
            min(time_diff, 60) / 60,
            ip_change
        ]

        return feature

    def _update_state(self, u, prob):
        # 状态机 ⭐
        if prob > 0.85:
            u["state"] = "BLOCKED"
        elif prob > 0.7:
            u["state"] = "ATTACK"
        elif prob > 0.5:
            u["state"] = "SUSPICIOUS"
        else:
            if u["state"] != "BLOCKED":
                u["state"] = "NORMAL"

    def process_log(self, user, status, ip, timestamp):
        """处理单条日志（核心函数）"""

        if user not in self.user_state:
            self._init_user(user, ip, timestamp)

        u = self.user_state[user]

        # 1️⃣ 特征
        feature = self._extract_feature(u, status, ip, timestamp)

        # 2️⃣ 滑动窗口
        u["seq"].append(feature)
        if len(u["seq"]) > WINDOW_SIZE:
            u["seq"].pop(0)

        # 不够窗口不预测
        if len(u["seq"]) < WINDOW_SIZE:
            return None

        # 3️⃣ 模型预测
        seq_tensor = torch.tensor(u["seq"]).unsqueeze(0)
        prob = float(self.model(seq_tensor).item())

        u["max_prob"] = max(u["max_prob"], prob)

        # 4️⃣ 状态机
        self._update_state(u, prob)

        # 5️⃣ 攻击计数
        if prob > self.threshold:
            u["attack_count"] += 1

        return {
            "user": user,
            "prob": prob,
            "state": u["state"],
            "attack_count": u["attack_count"],
            "max_prob": u["max_prob"]
        }

    def process_dataframe(self, df):
        """处理整个数据（模拟流）"""
        df = df.sort_values("timestamp")

        self.reset()

        alerts = []

        for _, row in df.iterrows():
            result = self.process_log(
                user=row["user"],
                status=row["status"],
                ip=row["ip"],
                timestamp=row["timestamp"]
            )

            if result and result["state"] in ["ATTACK", "BLOCKED"]:
                alerts.append({
                    "user": result["user"],
                    "time": str(row["timestamp"]),
                    "attack_count": result["attack_count"],
                    "max_prob": result["max_prob"],
                    "status": result["state"]
                })

        # 去重（保留最后状态）
        latest = {}
        for a in alerts:
            latest[a["user"]] = a

        return list(latest.values())