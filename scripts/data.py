import csv
import random
from datetime import datetime, timedelta

# ======================
# 用户定义
# ======================
users = ["user1", "user2", "user3", "admin", "guest"]

user_profiles = {
    "user1": {"activity": 2.0, "ip_stability": 0.9},
    "user2": {"activity": 1.5, "ip_stability": 0.8},
    "user3": {"activity": 1.0, "ip_stability": 0.7},
    "admin": {"activity": 0.5, "ip_stability": 0.95},
    "guest": {"activity": 0.3, "ip_stability": 0.5}
}

user_ip_map = {}

def get_user_ip(user):
    if user not in user_ip_map:
        user_ip_map[user] = random_ip()
    return user_ip_map[user]

def random_ip():
    return ".".join(str(random.randint(1, 255)) for _ in range(4))


# ======================
# 时间间隔函数（模拟真实时间分布）
# ======================
def get_time_delta(current_time):
    hour = current_time.hour
    if 0 <= hour <= 6:
        return random.randint(60, 600)
    elif 8 <= hour <= 22:
        return random.randint(5, 120)
    else:
        return random.randint(30, 300)


# ======================
# 正常行为生成
# ======================
def generate_normal_behavior(writer, current_time):
    user = random.choices(
        users,
        weights=[user_profiles[u]["activity"] for u in users]
    )[0]

    profile = user_profiles[user]

    # IP行为
    if random.random() < profile["ip_stability"]:
        ip = get_user_ip(user)
    else:
        ip = random_ip()

    # 是否出现短时间多次失败（灰色行为）
    if random.random() < 0.1:
        fail_streak = random.randint(2, 5)
        for _ in range(fail_streak):
            timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S")
            writer.writerow([timestamp, user, "login", "fail", ip, 0])
            current_time += timedelta(seconds=random.randint(2, 10))

    # 正常登录
    status = random.choices(["success", "fail"], weights=[0.9, 0.1])[0]

    timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S")
    writer.writerow([timestamp, user, "login", status, ip, 0])

    return current_time


# ======================
# 攻击行为生成
# ======================
def generate_attack_behavior(writer, current_time):
    attack_mode = random.choice([
        "high_freq",
        "ip_pool",
        "slow_attack",
        "fixed_ip"
    ])

    target_user = random.choices(
        users,
        weights=[2, 2, 1.5, 6, 1]  # admin 权重最高
    )[0]

    attacker_ips = ["6.6.6.6", "7.7.7.7", "8.8.8.8", "9.9.9.9"]

    # 攻击长度收敛（避免数据爆炸）
    phase_length = random.randint(5, 15)

    count = 0  # 记录实际生成条数

    for i in range(phase_length):

        # ========= IP策略 =========
        if attack_mode == "fixed_ip":
            ip = attacker_ips[0]
        elif attack_mode == "ip_pool":
            ip = random.choice(attacker_ips)
        else:
            ip = random_ip()

        # ========= 时间策略 =========
        if attack_mode == "high_freq":
            delta = random.randint(1, 3)
        else :
            delta = random.randint(10, 60)
        #else:
            #delta = random.randint(2, 8)

        current_time += timedelta(seconds=delta)

        # ========= 状态策略 =========
        # 前期失败多，后期成功率上升（模拟撞库成功）
        if i > phase_length * 0.7:
            status = random.choices(["fail", "success"], weights=[0.8, 0.2])[0]
        else:
            status = random.choices(["fail", "success"], weights=[0.95, 0.05])[0]

        # 少量很快就攻击成功
        if random.random() < 0.1:
            status = "success"

        timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S")

        writer.writerow([timestamp, target_user, "login", status, ip, 1])

        count += 1

    return current_time, count


# ======================
# 主生成函数
# ======================
def generate_dataset(
    total_logs=20000,
    target_attack_ratio=0.3,
    output_file="D:/Projects/Python/demo/data/dataset.csv"
):
    current_time = datetime.now()

    attack_count = 0
    normal_count = 0

    with open(output_file, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["timestamp", "user", "action", "status", "ip", "label"])

        while (attack_count + normal_count) < total_logs:

            total_count = attack_count + normal_count
            current_ratio = attack_count / (total_count + 1)

            # ========= 是否触发攻击块 =========
            trigger_attack_block = random.random() < 0.1

            if trigger_attack_block and current_ratio < target_attack_ratio:
                # ======== 攻击阶段（连续一段）========
                current_time, added = generate_attack_behavior(writer, current_time)

                attack_count += added

            else:
                # ======== 正常行为 ========
                current_time = generate_normal_behavior(writer, current_time)

                normal_count += 1

            # ========= 时间推进 =========
            delta = get_time_delta(current_time)
            current_time += timedelta(seconds=delta)

    total = attack_count + normal_count

    print(f"Dataset generated: {output_file}")
    print(f"Normal: {normal_count}, Attack: {attack_count}")
    print(f"Attack ratio: {attack_count / total:.2f}")


if __name__ == "__main__":
    generate_dataset()