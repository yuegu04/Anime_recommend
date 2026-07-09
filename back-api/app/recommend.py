import os
import json
import pickle
import re
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.linalg import solve
from implicit.als import AlternatingLeastSquares

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "filtered_anime.csv")

# ---- 题材标签清洗：Bangumi 返回的混合了制作公司/年份/自身标题片段等噪声 ----
_STOP_TAGS = {
    "tv", "番剧", "日本", "原创", "漫画改", "轻小说改", "小说改", "同名",
    "改编", "web", "里番", "ova", "剧场版", "tv动画", "动画", "动漫",
    "日本动画", "动画化", "短篇", "泡面番", "女性向", "男性向", "漫画改编",
}
_YEAR_RE = re.compile(r"^\d{4}$|^\d{4}年|年\d|月新番|^\d+月$|^\d{1,2}月新番")


def _useful_tag(tag: str, name: str) -> bool:
    """过滤掉非题材噪声标签，仅保留可用作内容相似的题材词。"""
    t = (tag or "").strip()
    if len(t) < 2:
        return False
    if t.lower() in _STOP_TAGS:
        return False
    if _YEAR_RE.search(t):  # 年份/月份
        return False
    if name and (t in name or name in t):  # 作品自身标题片段
        return False
    if any(k in t for k in ("动画", "工作室", "production", "studio", "制作公司", "社")):
        return False
    return True


class AnimeRecommender:
    def __init__(self, data_path: str = DATA_PATH):
        self.data_path = data_path
        self.model = None
        self.user_ids = []
        self.item_ids = []
        self.user_to_idx = {}
        self.item_to_idx = {}
        self.sparse_matrix = None
        self.regularization = 0.1
        self.content_weight = 0.65  # 混合推荐中「内容相似度」权重（基于收藏偏好，占比更大）
        self.cf_weight = 0.35        # 混合推荐中「协同过滤」权重
        self.content_driven = True  # True=纯内容驱动（1 个真实用户时 CF 无个性化信号，内容优先）
        self.content_vectors = {}   # 动漫名 -> 单位化内容向量
        self._content_dim = 0
        # 启动兜底：CSV 缺失或训练失败不应导致整个后端崩溃
        try:
            self._load_data()
            self._train()
        except Exception as e:  # noqa: BLE001
            import logging
            logging.getLogger("media_recommend").exception("推荐模型初始化失败：%s", e)
            self.model = None
        # 内容特征独立构建，失败也不影响协同过滤主链路
        try:
            self._build_content_features()
        except Exception:  # noqa: BLE001
            self.content_vectors = {}
            self._content_dim = 0

    def _load_data(self):
        df = pd.read_csv(self.data_path, encoding="gbk")
        df.columns = df.columns.str.strip()

        records = []
        for _, row in df.iterrows():
            title = row.get("中文标题") or row.get("标题") or str(row.get("subject", ""))
            # 只用中文标题做 item_id，与数据库 media.name 保持一致
            item_label = str(title).strip()
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
            .head(50)
        )

        self.user_ids = sorted(interactions["user_id"].astype(str).unique().tolist())
        self.item_ids = sorted(interactions["anime_title"].astype(str).unique().tolist())
        self.user_to_idx = {u: i for i, u in enumerate(self.user_ids)}
        self.item_to_idx = {i: j for j, i in enumerate(self.item_ids)}

        rows = interactions["user_id"].astype(str).map(self.user_to_idx).to_numpy()
        cols = interactions["anime_title"].astype(str).map(self.item_to_idx).to_numpy()
        data = interactions["rating"].astype(float).to_numpy()

        self.sparse_matrix = csr_matrix((data, (rows, cols)), shape=(len(self.user_ids), len(self.item_ids)))

    def _train(self):
        model = AlternatingLeastSquares(
            factors=32,
            regularization=0.1,
            iterations=20,
            random_state=42,
            use_native=True,
            use_cg=True,
        )
        model.fit(self.sparse_matrix.T.tocsr(), show_progress=False)
        self.model = model

    # ---- 内容特征：优先用 DB 中 Bangumi 真实题材标签(genre_tags)做 TF-IDF ----
    def _build_content_features(self):
        """构建内容向量：优先用 DB 的 genre_tags（真实题材标签）做 TF-IDF；
        若尚未回填标签，则回退到 CSV 的「类型/子类型/年份/VIB评分」弱特征，保证不中断。
        """
        self.content_vectors = {}
        self._content_dim = 0
        try:
            self._build_content_features_db()
        except Exception:  # noqa: BLE001
            self.content_vectors = {}
            self._content_dim = 0
        if not self.content_vectors:
            self._build_content_features_csv()

    def _build_content_features_db(self):
        """基于 Media.genre_tags（逗号分隔的中文题材标签）构建 TF-IDF 内容向量。"""
        from app.database import SessionLocal
        from app.models.media import Media

        db = SessionLocal()
        try:
            rows = db.query(Media.name, Media.genre_tags).filter(
                Media.genre_tags.isnot(None)
            ).all()
        finally:
            db.close()

        docs = []
        for name, g in rows:
            name = str(name or "").strip()
            g = str(g or "").strip()
            if not name or not g:
                continue
            tags = [t.strip() for t in g.split(",") if t.strip()]
            tags = [t for t in tags if _useful_tag(t, name)]
            if tags:
                docs.append((name, tags))
        if not docs:
            return

        # 词表与 IDF：标签越稀有、权重越高（抑制「动画」等过泛标签）
        df_cnt = {}
        N = len(docs)
        for _, tags in docs:
            for t in set(tags):
                df_cnt[t] = df_cnt.get(t, 0) + 1
        idf = {t: float(np.log((N + 1) / (c + 1)) + 1.0) for t, c in df_cnt.items()}
        vocab = {t: i for i, t in enumerate(sorted(df_cnt))}
        dim = len(vocab)
        self._content_dim = dim
        for name, tags in docs:
            vec = np.zeros(dim, dtype=np.float32)
            for t in set(tags):
                if t in vocab:
                    vec[vocab[t]] += idf[t]
            norm = np.linalg.norm(vec)
            if norm > 0:
                self.content_vectors[name] = vec / norm

    def _build_content_features_csv(self):
        """回退方案：用 CSV 的「类型/子类型/年份/VIB评分」编码（弱内容特征）。"""
        import pandas as pd

        df = pd.read_csv(self.data_path, encoding="gbk")
        df.columns = df.columns.str.strip()
        type_onehot = {"1": 0, "2": 1, "3": 2, "4": 3, "6": 4}
        form_set = ["TV", "OVA", "剧场版", "WEB", "电影", "日剧", "欧美剧",
                    "华语剧", "漫画", "小说", "动态漫画", "电视剧"]
        dim = 5 + len(form_set) + 2
        self._content_dim = dim
        for _, row in df.iterrows():
            title = row.get("中文标题") or row.get("标题") or str(row.get("subject", ""))
            name = str(title).strip()
            if not name:
                continue
            vec = np.zeros(dim, dtype=np.float32)
            t = str(row.get("类型", "")).strip()
            if t in type_onehot:
                vec[type_onehot[t]] = 1.0
            sub = str(row.get("子类型", "")).strip()
            if sub in form_set:
                vec[5 + form_set.index(sub)] = 1.0
            y = pd.to_numeric(row.get("年份数值"), errors="coerce")
            if not pd.isna(y):
                vec[5 + len(form_set)] = min(max((y - 1990) / 40.0, 0.0), 1.0)
            s = pd.to_numeric(row.get("VIB评分"), errors="coerce")
            if not pd.isna(s):
                vec[5 + len(form_set) + 1] = min(max(s / 10.0, 0.0), 1.0)
            norm = np.linalg.norm(vec)
            if norm > 0:
                self.content_vectors[name] = vec / norm

    def recommend(self, user_id: str, top_n: int = 10):
        """虚拟用户（want/doing/done）推荐：统一用 fold-in 基于动漫因子投影，语义更正确。"""
        if self.model is None:
            return []
        if user_id not in self.user_to_idx:
            return []

        user_idx = self.user_to_idx[user_id]
        user_items = self.sparse_matrix[user_idx]
        liked = set(user_items.nonzero()[1].tolist())

        name_score = {self.item_ids[idx]: float(user_items[0, idx]) for idx in liked}

        if self.content_driven:
            # 纯内容驱动：候选池为全部有内容向量的动漫
            return self._content_recommend(name_score, top_n)

        # 混合：内容(权重更高) + 协同过滤
        n_items = len(self.item_ids)
        user_vec = np.zeros(n_items, dtype=np.float32)
        for idx in liked:
            user_vec[idx] = float(user_items[0, idx])
        return self._hybrid_recommend(name_score, user_vec, liked, top_n)

    def recommend_for_user(self, user_id: int, db, top_n: int = 10):
        """基于真实用户在 Rating 表的行为，用已训练模型的「动漫因子」做 fold-in 即时预测。

        无需重训模型：把该用户对动漫的评分向量投影到隐空间得到用户向量，
        再与所有动漫因子做点积得到预测分，过滤已看过的、去重后取 top_n。
        返回 [] 表示该用户暂无行为（冷启动），调用方应回退到默认推荐。
        """
        if self.model is None:
            return []
        from app.models.rating import Rating
        from app.models.media import Media

        rows = db.query(Rating.media_id, Rating.score).filter(Rating.user_id == user_id).all()
        if not rows:
            return []

        media_ids = [r.media_id for r in rows]
        medias = db.query(Media.id, Media.name).filter(Media.id.in_(media_ids)).all()
        id_to_name = {m.id: m.name for m in medias}

        # 一次性收集：name_score（全部收藏，用于内容驱动）/ user_vec+liked（仅 129 训练集，用于混合）
        name_score = {}
        n_items = len(self.item_ids)
        user_vec = np.zeros(n_items, dtype=np.float32)
        liked = set()
        for media_id, score in rows:
            name = id_to_name.get(media_id)
            if not name or score <= 0:
                continue
            name_score[name] = max(name_score.get(name, 0.0), float(score))
            idx = self.item_to_idx.get(name)
            if idx is not None:
                user_vec[idx] = float(score)
                liked.add(idx)

        if self.content_driven:
            # 纯内容驱动：候选池为全部有内容向量的动漫，不再受限于 CF 训练集
            return self._content_recommend(name_score, top_n)

        # 混合：内容(权重更高) + 协同过滤；CF 训练集无该用户行为时，内容通道仍可兜底
        return self._hybrid_recommend(name_score, user_vec, liked, top_n)

    def _fold_in(self, user_vec: np.ndarray, liked: set, top_n: int = 10):
        """核心：把用户评分向量投影到隐空间，与动漫因子点积排序。

        user_vec: 长度=动漫数，已含正偏好；liked: 已交互的动漫索引集合（过滤掉）。
        """
        # 动漫因子：由于训练时传入 sparse_matrix.T，model.user_factors 对应的是动漫维度
        F = np.asarray(self.model.user_factors, dtype=np.float32)  # (n_items, factors)
        lam = float(self.regularization)
        f = F.shape[1]
        A = F.T @ F + lam * np.eye(f)
        u = solve(A, F.T @ user_vec)        # 用户隐向量 (factors,)
        scores = F @ u                       # 对所有动漫的预测分 (n_items,)

        order = np.argsort(-scores)
        results = []
        seen = set()
        for idx in order:
            if idx in liked:
                continue
            item_name = self.item_ids[idx]
            if item_name in seen:
                continue
            seen.add(item_name)
            results.append({"item": item_name, "score": float(scores[idx])})
            if len(results) >= top_n:
                break
        return results

    def _content_recommend(self, name_score: dict, top_n: int = 10):
        """纯内容驱动：用收藏动漫（按评分加权）的画像，对全部有内容向量的动漫算余弦相似度。"""
        if not self.content_vectors or self._content_dim == 0:
            return []
        prof = np.zeros(self._content_dim, dtype=np.float32)
        wsum = 0.0
        for name, w in name_score.items():
            cv = self.content_vectors.get(name)
            if cv is None:
                continue
            prof += cv * float(w)
            wsum += float(w)
        if wsum <= 0:
            return []
        prof /= wsum
        pnorm = np.linalg.norm(prof)
        if pnorm > 0:
            prof = prof / pnorm
        scored = []
        for name, cv in self.content_vectors.items():
            if name in name_score:
                continue
            scored.append((name, float(prof @ cv)))
        scored.sort(key=lambda x: -x[1])
        return [{"item": n, "score": s} for n, s in scored[:top_n]]


recommender = AnimeRecommender()
