import os
import pandas as pd
from scipy.sparse import csr_matrix
from implicit.als import AlternatingLeastSquares

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")


DATA_PATH = "filtered_anime.csv"


def load_anime_data(path: str) -> pd.DataFrame:
    """读取 filtered_anime.csv，并使用其中的想看/在看/看过字段构造隐式反馈。"""
    if not os.path.exists(path):
        raise FileNotFoundError(f"找不到数据文件: {path}")

    df = pd.read_csv(path, encoding="gbk")
    df.columns = df.columns.str.strip()
    print(f"读取动漫数据: {path}, 共 {len(df)} 条")
    return df


def build_interactions(df: pd.DataFrame, top_n_per_user: int = 50) -> pd.DataFrame:
    """把 filtered_anime.csv 中的字段转成 ALS 需要的三列: user_id, anime_title, rating。"""
    def title_of(row: pd.Series) -> str:
        for col in ["中文标题", "标题"]:
            if col in df.columns and pd.notna(row[col]):
                return str(row[col]).strip()
        return str(row.get("subject", ""))

    records = []
    for _, row in df.iterrows():
        item_title = title_of(row)
        item_id = str(row.get("subject", item_title))
        item_label = f"{item_id} | {item_title}"

        want = pd.to_numeric(row.get("想", 0), errors="coerce")
        doing = pd.to_numeric(row.get("在", 0), errors="coerce")
        done = pd.to_numeric(row.get("已", 0), errors="coerce")
        vib = pd.to_numeric(row.get("VIB评分", 0), errors="coerce")

        want = 0 if pd.isna(want) else float(want)
        doing = 0 if pd.isna(doing) else float(doing)
        done = 0 if pd.isna(done) else float(done)
        vib = 0 if pd.isna(vib) else float(vib)

        if want > 0:
            records.append(("want", item_label, want * 0.8 + vib * 0.1))
        if doing > 0:
            records.append(("doing", item_label, doing * 1.0 + vib * 0.1))
        if done > 0:
            records.append(("done", item_label, done * 1.2 + vib * 0.1))

    interactions = pd.DataFrame(records, columns=["user_id", "anime_title", "rating"])
    interactions = interactions[interactions["rating"] > 0]

    interactions = (
        interactions.sort_values(["user_id", "rating"], ascending=[True, False])
        .groupby("user_id", group_keys=False)
        .head(top_n_per_user)
    )

    print(f"构造出 {len(interactions)} 条隐式交互记录（每个伪用户保留前 {top_n_per_user} 条）")
    return interactions


def build_sparse_matrix(df: pd.DataFrame):
    """把 pandas 数据转成 ALS 需要的稀疏矩阵。"""
    user_ids = df["user_id"].astype(str).unique()
    item_ids = df["anime_title"].astype(str).unique()

    user_to_idx = {u: i for i, u in enumerate(user_ids)}
    item_to_idx = {i: j for j, i in enumerate(item_ids)}

    rows = df["user_id"].astype(str).map(user_to_idx).to_numpy()
    cols = df["anime_title"].astype(str).map(item_to_idx).to_numpy()
    data = df["rating"].astype(float).to_numpy()

    sparse_user_item = csr_matrix((data, (rows, cols)), shape=(len(user_ids), len(item_ids)))
    return sparse_user_item.tocsr(), user_ids, item_ids, user_to_idx, item_to_idx


def train_model(sparse_user_item, factors: int = 32, iterations: int = 20):
    """训练 ALS 模型。"""
    model = AlternatingLeastSquares(
        factors=factors,
        regularization=0.1,
        iterations=iterations,
        random_state=42,
        use_native=True,
        use_cg=True,
    )
    model.fit(sparse_user_item.T.tocsr(), show_progress=False)
    return model


def recommend_for_user(model, sparse_user_item, user_idx, item_ids, top_n=10):
    """为指定用户生成推荐。"""
    user_interactions = sparse_user_item[user_idx]
    liked_item_indices = set(user_interactions.nonzero()[1].tolist())

    recs, scores = model.recommend(
        userid=user_idx,
        user_items=user_interactions,
        N=max(top_n * 5, 20),
        filter_already_liked_items=False,
    )

    results = []
    for item_idx, score in zip(recs, scores):
        if item_idx < len(item_ids) and item_idx not in liked_item_indices:
            results.append((item_ids[item_idx], float(score)))
        if len(results) >= top_n:
            break

    return results


if __name__ == "__main__":
    print("开始加载 filtered_anime.csv...")
    raw_df = load_anime_data(DATA_PATH)

    print("构造隐式交互数据...")
    interactions_df = build_interactions(raw_df)

    print("构建用户-物品稀疏矩阵...")
    sparse_user_item, user_ids, item_ids, user_to_idx, item_to_idx = build_sparse_matrix(interactions_df)

    print("训练 ALS 模型...")
    model = train_model(sparse_user_item)

    print("\n推荐结果示例:")
    for target_user in ["want", "doing", "done"]:
        if target_user in user_to_idx:
            user_idx = user_to_idx[target_user]
            recommendations = recommend_for_user(model, sparse_user_item, user_idx, item_ids, top_n=5)
            print(f"\n[{target_user}] 推荐：")
            for anime_title, score in recommendations:
                print(f"{anime_title}: {score:.3f}")

    print("\n训练完成。注意：filtered_anime.csv 不是标准的 user-item 交互表，因此这里使用“想/在/已”字段做了一个隐式反馈代理。")
