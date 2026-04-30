import csv
import random
from datetime import datetime, timedelta

# ======================
# 用户 & 攻击模式绑定（核心改动）
# ======================
users = ["user1", "user2", "user3", "admin", "guest"]

user_attack_map = {
    "user1": "high_freq",
    "user2": "ip_pool",
    "user3": "slow_attack",
    "admin": "fixed_ip",
    "guest": "hybrid"
}

user_ip_map = {}

def random_ip():
    return ".".join(str(random.randint(1, 255)) for _ in range(4))

def get_user_ip(user):
    if user not in user_ip_map:
        user_ip_map[user] = random_ip()
    return user_ip_map[user]

# ======================
# 每个用户生成固定行为数
# ======================
def generate_user_sequence(writer, user, start_time, total_len=20):

    attack_mode = user_attack_map[user]

    attacker_ips = ["6.6.6.6", "7.7.7.7", "8.8.8.8"]

    for i in range(total_len):

        # ======================
        # IP策略
        # ======================
        if attack_mode == "fixed_ip":
            ip = attacker_ips[0]

        elif attack_mode == "ip_pool":
            ip = random.choice(attacker_ips)

        elif attack_mode == "high_freq":
            ip = random_ip()

        elif attack_mode == "slow_attack":
            ip = random_ip()

        else:
            ip = random_ip()

        # ======================
        # 时间策略
        # ======================
        if attack_mode == "high_freq":
            delta = random.randint(1, 3)
        elif attack_mode == "slow_attack":
            delta = random.randint(30, 120)
        else:
            delta = random.randint(5, 20)

        start_time += timedelta(seconds=delta)

        # ======================
        # 行为策略（关键）
        # ======================
        if i < total_len * 0.6:
            status = "fail"
            label = 1
        else:
            status = random.choices(
                ["fail", "success"],
                weights=[0.6, 0.4]
            )[0]
            label = 1 if status == "fail" else 0

        # 少量“成功穿透”
        if random.random() < 0.1:
            status = "success"
            label = 1

        timestamp = start_time.strftime("%Y-%m-%d %H:%M:%S")

        writer.writerow([
            timestamp,
            user,
            "login",
            status,
            ip,
            label,
            attack_mode
        ])

    return start_time


# ======================
# 主函数（控制论文数据）
# ======================
def generate_dataset(output_file="D:/Projects/Python/demo/data/show_dataset.csv"):

    current_time = datetime.now()

    with open(output_file, "w", newline="", encoding="utf-8") as f:

        writer = csv.writer(f)

        writer.writerow([
            "timestamp",
            "user",
            "action",
            "status",
            "ip",
            "label",
            "attack_type"
        ])

        for user in users:
            current_time = generate_user_sequence(
                writer,
                user,
                current_time,
                total_len=20
            )

    print("生成完成:", output_file)


if __name__ == "__main__":
    generate_dataset()