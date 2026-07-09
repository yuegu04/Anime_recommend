# ALS 推荐模型使用说明

## 1. 需要的数据格式

推荐模型训练需要一张交互表，至少包含 3 列：

- user_id：用户 ID
- anime_title：番剧标题
- rating：评分或喜欢程度

例如：

```csv
user_id,anime_title,rating
u1,鬼灭之刃,5
u1,咒术回战,4
u2,咒术回战,4
```

## 2. 如果你使用 Bangumi 数据

可以把 Bangumi 的收藏/在看/看过记录整理成如下格式：

- 收藏状态转为评分：
  - 想看 = 1
  - 在看 = 3
  - 看过 = 5
- 也可以直接使用“评分”字段，如果有的话。

然后保存成：

```bash
user_anime_interactions.csv
```

## 3. 运行训练脚本

在 back-api 目录下执行：

```bash
python train_als.py
```

如果当前目录下已经有 user_anime_interactions.csv，就会直接读取；否则会生成一个示例数据集。

## 4. 训练后的结果

脚本会输出每个用户的推荐结果，例如：

```text
鬼灭之刃: 0.812
咒术回战: 0.701
```

## 5. 后续接入到你的项目

你可以把训练后的推荐结果再接到 FastAPI 接口中，例如：

- /recommend/{user_id}
- 返回用户的 Top-N 推荐番剧列表
