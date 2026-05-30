# 🚨 暴力破解异常检测平台（Flask + LSTM）

本项目是一个基于 **深度学习（LSTM）+ Web 安全场景** 的登录行为异常检测系统，
 主要用于识别账号暴力破解攻击，并提供告警分析、风险趋势展示与用户行为画像。

系统从原始登录日志出发，通过**滑动窗口序列建模**，对用户行为进行时间维度分析，实现从检测 → 告警 → 可视化 → 取证的完整闭环。

------

## ✨ 项目亮点

- 🔍 **行为序列建模**：基于滑动窗口构造用户登录行为序列
- 🧠 **LSTM 异常检测**：捕捉时间依赖关系，识别暴力破解行为模式
- 📊 **风险演化趋势**：可视化用户风险变化过程（时间序列）
- 🚨 **告警中心**：支持告警分页、状态流转（误报/已处理）
- 👤 **用户风险画像**：展示单用户风险窗口与攻击行为时间线
- 🔎 **窗口级取证分析**：支持攻击行为回溯与日志细粒度分析
- 🔄 **完整检测链路**：从日志接入 → 模型推理 → 告警入库 → 前端展示

------

## 🧱 系统架构

```
日志数据（CSV）
        ↓
日志解析（按用户分组）
        ↓
滑动窗口构造（时间序列特征）
        ↓
LSTM 模型推理（风险概率）
        ↓
窗口聚合（生成告警）
        ↓
MySQL 存储（alerts / windows / logs）
        ↓
Flask Web 展示（趋势 / 告警 / 用户画像）
```

------

![架构图.drawio (1)](https://fajiaoji-blog-picture.oss-cn-beijing.aliyuncs.com/2026/05/e2b02de216ec983c3e838f5672b2ab88.png)

## ⚙️ 核心功能

### 1️⃣ 账号与系统管理

- 用户注册 / 登录 / 会话管理
- 多监测源接入（上传日志 CSV）

### 2️⃣ 告警中心

- 风险告警分页展示
- 告警状态管理：
  - `pending`（未处理）
  - `resolved`（已处理）
  - `false_positive`（误报）

### 3️⃣ 风险分析

- 攻击趋势分析（时间序列）
- 高风险用户排行（Top N）
- 窗口级行为可视化（风险时间线）

### 4️⃣ 用户风险画像

- 单用户风险演化趋势（LSTM输出）
- 攻击时间线取证（滑动窗口）
- 最大风险值 / 攻击窗口统计

### 5️⃣ 数据与模型

- 模拟日志生成（攻击/正常）
- 数据集划分（train/test）
- LSTM 模型训练与评估

------

## 🧠 模型设计

本项目使用 **LSTM（Long Short-Term Memory）** 对用户行为进行建模：

- **输入**：滑动窗口内的行为序列特征
- **输出**：窗口级风险概率（0~1）
- **任务类型**：二分类（正常 / 攻击）

### 特点：

- 捕捉时间依赖（连续失败登录行为）
- 识别暴力破解的阶段性模式（尝试 → 爆发 → 成功）
- 支持窗口级异常定位（可解释性较强）

### 训练配置：

- Loss：Binary Cross Entropy
- Optimizer：Adam
- 框架：PyTorch

------

## 🔄 检测流程

```
1. 上传日志 CSV（/add_system）
2. 日志解析并按用户分组
3. 构造滑动窗口序列（preprocess2.py）
4. 输入 LSTM 模型计算风险概率
5. 按窗口聚合生成告警（alerts）
6. 存储窗口结果（windows）与原始日志（logs）
7. 前端展示风险趋势与用户画像
```

------

## 📁 项目结构

```
demo/
├── app.py                  # Flask 主应用（API + 页面）
├── preprocess2.py          # 滑动窗口特征构造
├── engine/
│   └── detector.py         # 检测引擎
├── models/
│   ├── model2.py           # LSTM 模型
│   └── train2.py           # 训练脚本
├── scripts/
│   ├── data.py             # 模拟数据生成
│   └── show_data.py        # 可视化样本生成
├── data/
│   ├── dataset.csv
│   ├── train.csv
│   ├── test.csv
│   └── distribute.py
├── templates/              # 前端页面
├── static/                 # JS脚本
└── uploads/                # 日志上传目录
```

------

## 🗄️ 数据库设计

- `users`
   用户账号信息
   `(id, username, password_hash, created_at)`
- `systems`
   接入系统信息
   `(id, system_name, log_file, source_type, status, owner, created_at)`
- `alerts`
   聚合告警（用户级）
   `(id, system_name, user, time, attack_count, max_prob, status)`
- `windows`
   滑动窗口检测结果
   `(id, user, start_time, end_time, prob, seq_id, risk_level, raw_seq)`
- `logs`
   窗口内日志明细
   `(id, system_name, user, timestamp, ip, seq_id, prob, status)`

------

## 📄 数据格式（CSV）

```
timestamp,user,action,status,ip,label
2026-04-01 18:38:20,admin,login,fail,8.8.8.8,1
2026-04-01 18:38:27,admin,login,fail,6.6.6.6,1
```

字段说明：

- `status`：success / fail
- `label`：训练标签（线上可忽略）

------

## 🚀 快速启动

### 1️⃣ 安装依赖

```
pip install flask flask-bcrypt pymysql pandas numpy torch scikit-learn matplotlib
```

### 2️⃣ 训练模型

```
python scripts/data.py
python data/distribute.py
python models/train2.py
```

### 3️⃣ 启动系统

```
python app.py
```

访问：

```
http://127.0.0.1:5000/
```

------

## 📊 页面展示

- 监测总览（趋势 + 排行）
- 风险告警列表
- 用户风险画像（趋势 + 时间线）

------

![屏幕截图 2026-05-19 110337](https://img.fajiaoji.xyz/2026/05/4ee01888a2af3b72c3f353e31f6b7f7c.png)

![屏幕截图 2026-04-30 101131](https://img.fajiaoji.xyz/2026/05/00dcb40ce034242f82cc55b682031e2f.png)

![屏幕截图 2026-04-30 101159](https://img.fajiaoji.xyz/2026/05/3a0ddb6bd41614497d8b89943ee58af4.png)

## 🔮 后续优化方向

- 引入 Transformer 提升序列建模能力
- 增加更多行为特征（设备指纹 / 地理位置）
- 支持在线学习（模型动态更新）
- 扩展检测场景（撞库攻击 / 异常登录）

------

## 📌 项目说明

本项目为安全方向与深度学习结合的实践项目，适用于：

- Web 安全 / AI 安全方向学习
- 异常检测 / 用户行为分析场景
- 毕业设计 / 面试项目展示
