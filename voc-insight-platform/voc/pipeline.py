"""Dependency-light VOC analysis pipeline for Chinese and English feedback."""

from __future__ import annotations

import math
import random
import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Iterable


POSITIVE_WORDS = {
    "好", "很好", "方便", "稳定", "准确", "快速", "流畅", "喜欢", "满意", "清晰",
    "实用", "智能", "省时", "推荐", "优秀", "友好", "及时", "有效", "顺畅", "专业",
    "good", "great", "fast", "helpful", "accurate", "easy", "useful", "love", "stable",
}
NEGATIVE_WORDS = {
    "慢", "卡", "卡顿", "崩溃", "错误", "失败", "难用", "复杂", "不准", "幻觉", "贵",
    "延迟", "丢失", "闪退", "重复", "失效", "模糊", "麻烦", "无法", "不支持", "泄露",
    "slow", "crash", "wrong", "failed", "difficult", "expensive", "delay", "bug", "hallucination",
}
NEGATIONS = {"不", "没", "没有", "未", "并非", "不是", "not", "never", "no"}
INTENSIFIERS = {"很": 1.3, "非常": 1.6, "特别": 1.5, "太": 1.4, "极其": 1.7, "really": 1.4, "very": 1.4}
STOPWORDS = {
    "的", "了", "是", "在", "和", "也", "就", "都", "我", "有", "很", "但", "还", "能", "用",
    "一个", "这个", "希望", "感觉", "目前", "产品", "功能", "用户", "时候", "一下", "可以", "比较",
    "the", "a", "an", "is", "are", "and", "to", "of", "it", "this", "that", "for", "with", "very",
}
THEME_RULES = {
    "性能与稳定性": {"慢", "卡顿", "延迟", "崩溃", "闪退", "响应", "加载", "速度", "稳定", "slow", "crash"},
    "回答质量": {"回答", "准确", "不准", "错误", "幻觉", "引用", "答案", "召回", "检索", "hallucination"},
    "知识库管理": {"知识库", "文档", "上传", "解析", "切分", "同步", "更新", "格式", "文件"},
    "交互与易用性": {"界面", "按钮", "入口", "操作", "流程", "导航", "提示", "移动端", "易用", "UI"},
    "权限与安全": {"权限", "账号", "登录", "隐私", "安全", "成员", "团队", "访问", "泄露"},
    "数据与导出": {"导出", "报表", "Excel", "数据", "统计", "下载", "筛选", "图表", "CSV"},
    "价格与服务": {"价格", "套餐", "额度", "客服", "售后", "付费", "贵", "发票", "订阅"},
}


def normalize_text(text: Any) -> str:
    value = str(text or "").strip()
    value = re.sub(r"https?://\S+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value


def tokenize(text: str) -> list[str]:
    text = normalize_text(text).lower()
    english = re.findall(r"[a-z][a-z0-9_-]{1,}", text)
    chinese_runs = re.findall(r"[\u4e00-\u9fff]+", text)
    chinese: list[str] = []
    for run in chinese_runs:
        chinese.extend(ch for ch in run if ch not in STOPWORDS and len(ch.strip()) > 0)
        chinese.extend(run[i : i + 2] for i in range(len(run) - 1))
    return [token for token in english + chinese if token not in STOPWORDS and len(token) > 1]


def sentiment_score(text: str, rating: Any = None) -> tuple[str, float, float]:
    lowered = normalize_text(text).lower()
    score = 0.0
    hits = 0
    occupied: list[tuple[int, int]] = []
    lexicon = sorted(POSITIVE_WORDS | NEGATIVE_WORDS, key=len, reverse=True)
    for term in lexicon:
        for match in re.finditer(re.escape(term), lowered):
            span = match.span()
            if any(span[0] < end and span[1] > start for start, end in occupied):
                continue
            occupied.append(span)
            hits += 1
            polarity = 1 if term in POSITIVE_WORDS else -1
            previous = lowered[max(0, span[0] - 8) : span[0]]
            previous_tokens = re.findall(r"[a-z]+|[\u4e00-\u9fff]", previous)
            if any(previous.rstrip().endswith(item) for item in NEGATIONS):
                polarity *= -1
            multiplier = 1.0
            for item, factor in INTENSIFIERS.items():
                if previous.rstrip().endswith(item) or item in previous_tokens[-3:]:
                    multiplier = max(multiplier, factor)
            score += polarity * multiplier

    text_score = math.tanh(score / max(1.2, hits * 0.8)) if hits else 0.0
    try:
        rating_score = (float(rating) - 3.0) / 2.0
        combined = 0.75 * text_score + 0.25 * max(-1.0, min(1.0, rating_score))
    except (TypeError, ValueError):
        combined = text_score
    label = "正向" if combined >= 0.18 else "负向" if combined <= -0.18 else "中性"
    confidence = min(0.98, 0.55 + abs(combined) * 0.42)
    return label, round(combined, 4), round(confidence, 4)


def _tfidf_vectors(token_lists: list[list[str]], max_features: int = 180) -> tuple[list[dict[str, float]], list[str]]:
    document_frequency: Counter[str] = Counter()
    term_frequency: Counter[str] = Counter()
    for tokens in token_lists:
        document_frequency.update(set(tokens))
        term_frequency.update(tokens)
    vocabulary = [term for term, _ in term_frequency.most_common(max_features) if document_frequency[term] >= 2]
    total = len(token_lists)
    vectors: list[dict[str, float]] = []
    for tokens in token_lists:
        counts = Counter(token for token in tokens if token in vocabulary)
        length = max(1, sum(counts.values()))
        vector = {
            term: (count / length) * (math.log((1 + total) / (1 + document_frequency[term])) + 1)
            for term, count in counts.items()
        }
        norm = math.sqrt(sum(value * value for value in vector.values())) or 1.0
        vectors.append({term: value / norm for term, value in vector.items()})
    return vectors, vocabulary


def _cosine(left: dict[str, float], right: dict[str, float]) -> float:
    if len(left) > len(right):
        left, right = right, left
    return sum(value * right.get(term, 0.0) for term, value in left.items())


def _mean_vector(vectors: Iterable[dict[str, float]]) -> dict[str, float]:
    vectors = list(vectors)
    if not vectors:
        return {}
    totals: defaultdict[str, float] = defaultdict(float)
    for vector in vectors:
        for term, value in vector.items():
            totals[term] += value
    result = {term: value / len(vectors) for term, value in totals.items()}
    norm = math.sqrt(sum(value * value for value in result.values())) or 1.0
    return {term: value / norm for term, value in result.items()}


def cluster_documents(vectors: list[dict[str, float]], cluster_count: int) -> list[int]:
    if not vectors:
        return []
    cluster_count = max(1, min(cluster_count, len(vectors)))
    rng = random.Random(42)
    non_empty = [index for index, vector in enumerate(vectors) if vector]
    seeds = rng.sample(non_empty or list(range(len(vectors))), min(cluster_count, len(non_empty or vectors)))
    while len(seeds) < cluster_count:
        seeds.append(len(seeds) % len(vectors))
    centroids = [dict(vectors[index]) for index in seeds]
    labels = [0] * len(vectors)
    for _ in range(20):
        new_labels = [max(range(cluster_count), key=lambda idx: _cosine(vector, centroids[idx])) for vector in vectors]
        if new_labels == labels:
            break
        labels = new_labels
        for cluster in range(cluster_count):
            members = [vector for vector, label in zip(vectors, labels) if label == cluster]
            if members:
                centroids[cluster] = _mean_vector(members)
    return labels


def _theme_name(texts: list[str], keywords: list[str], cluster_index: int) -> str:
    combined = " ".join(texts + keywords)
    scores = {theme: sum(combined.lower().count(term.lower()) for term in terms) for theme, terms in THEME_RULES.items()}
    best_theme, best_score = max(scores.items(), key=lambda item: item[1])
    return best_theme if best_score else f"其他主题 {cluster_index + 1}"


def _parse_date(value: Any) -> str:
    raw = normalize_text(value)
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m", "%Y/%m"):
        try:
            return datetime.strptime(raw[:10], fmt).strftime("%Y-%m")
        except ValueError:
            pass
    return "日期未知"


def analyze_feedback(records: list[dict[str, Any]], config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or {}
    text_field = config.get("text_field", "text")
    rating_field = config.get("rating_field", "rating")
    date_field = config.get("date_field", "date")
    channel_field = config.get("channel_field", "channel")
    cluster_count = int(config.get("cluster_count", 6))
    weights = config.get("weights", {"volume": 0.35, "negative": 0.45, "severity": 0.20})

    prepared: list[dict[str, Any]] = []
    seen: set[str] = set()
    for source in records:
        text = normalize_text(source.get(text_field))
        fingerprint = re.sub(r"\W+", "", text.lower())
        if len(text) < 4 or not fingerprint or fingerprint in seen:
            continue
        seen.add(fingerprint)
        label, score, confidence = sentiment_score(text, source.get(rating_field))
        row = dict(source)
        row.update({"_text": text, "sentiment": label, "sentiment_score": score, "confidence": confidence})
        prepared.append(row)

    if not prepared:
        return {"summary": {"total": 0}, "records": [], "topics": [], "keywords": [], "trends": [], "channels": []}

    token_lists = [tokenize(row["_text"]) for row in prepared]
    vectors, _ = _tfidf_vectors(token_lists)
    labels = cluster_documents(vectors, cluster_count)
    global_keywords = Counter(token for tokens in token_lists for token in tokens).most_common(18)

    grouped: defaultdict[int, list[int]] = defaultdict(list)
    for index, cluster in enumerate(labels):
        grouped[cluster].append(index)

    topics: list[dict[str, Any]] = []
    max_volume = max(len(indices) for indices in grouped.values())
    for cluster, indices in grouped.items():
        tokens = Counter(token for index in indices for token in token_lists[index])
        keywords = [term for term, _ in tokens.most_common(5)]
        texts = [prepared[index]["_text"] for index in indices]
        negative_count = sum(prepared[index]["sentiment"] == "负向" for index in indices)
        negative_rate = negative_count / len(indices)
        ratings = []
        for index in indices:
            try:
                ratings.append(float(prepared[index].get(rating_field)))
            except (TypeError, ValueError):
                pass
        avg_rating = sum(ratings) / len(ratings) if ratings else None
        severity = 1 - ((avg_rating - 1) / 4) if avg_rating is not None else negative_rate
        score = 100 * (
            float(weights.get("volume", 0.35)) * (len(indices) / max_volume)
            + float(weights.get("negative", 0.45)) * negative_rate
            + float(weights.get("severity", 0.20)) * severity
        )
        topic_name = _theme_name(texts, keywords, cluster)
        topics.append({
            "id": cluster,
            "name": topic_name,
            "volume": len(indices),
            "negative_count": negative_count,
            "negative_rate": round(negative_rate, 4),
            "avg_rating": round(avg_rating, 2) if avg_rating is not None else None,
            "opportunity_score": round(score, 1),
            "priority": "P0" if score >= 72 else "P1" if score >= 48 else "P2",
            "keywords": keywords,
            "examples": sorted(
                (prepared[index] for index in indices),
                key=lambda row: row["sentiment_score"],
            )[:3],
        })
        for index in indices:
            prepared[index]["topic"] = topic_name
    # Several statistical clusters can represent the same business theme. Merge
    # them before prioritization so the opportunity backlog stays actionable.
    merged_by_name: dict[str, dict[str, Any]] = {}
    for topic in topics:
        current = merged_by_name.setdefault(topic["name"], {
            "id": topic["id"],
            "name": topic["name"],
            "volume": 0,
            "negative_count": 0,
            "rating_total": 0.0,
            "rating_count": 0,
            "keywords": [],
            "examples": [],
        })
        current["volume"] += topic["volume"]
        current["negative_count"] += topic["negative_count"]
        if topic["avg_rating"] is not None:
            current["rating_total"] += topic["avg_rating"] * topic["volume"]
            current["rating_count"] += topic["volume"]
        current["keywords"].extend(topic["keywords"])
        current["examples"].extend(topic["examples"])

    max_theme_volume = max(item["volume"] for item in merged_by_name.values())
    topics = []
    for item in merged_by_name.values():
        negative_rate = item["negative_count"] / item["volume"]
        avg_rating = item["rating_total"] / item["rating_count"] if item["rating_count"] else None
        severity = 1 - ((avg_rating - 1) / 4) if avg_rating is not None else negative_rate
        score = 100 * (
            float(weights.get("volume", 0.35)) * (item["volume"] / max_theme_volume)
            + float(weights.get("negative", 0.45)) * negative_rate
            + float(weights.get("severity", 0.20)) * severity
        )
        keyword_counts = Counter(item["keywords"])
        topics.append({
            "id": item["id"],
            "name": item["name"],
            "volume": item["volume"],
            "negative_count": item["negative_count"],
            "negative_rate": round(negative_rate, 4),
            "avg_rating": round(avg_rating, 2) if avg_rating is not None else None,
            "opportunity_score": round(score, 1),
            "priority": "P0" if score >= 65 else "P1" if score >= 48 else "P2",
            "keywords": [term for term, _ in keyword_counts.most_common(5)],
            "examples": sorted(item["examples"], key=lambda row: row["sentiment_score"])[:3],
        })
    topics.sort(key=lambda topic: topic["opportunity_score"], reverse=True)

    sentiments = Counter(row["sentiment"] for row in prepared)
    trend_counter: defaultdict[str, Counter[str]] = defaultdict(Counter)
    channel_counter: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for row in prepared:
        trend_counter[_parse_date(row.get(date_field))][row["sentiment"]] += 1
        channel = normalize_text(row.get(channel_field)) or "渠道未知"
        channel_counter[channel][row["sentiment"]] += 1

    return {
        "summary": {
            "total": len(prepared),
            "duplicates_removed": len(records) - len(prepared),
            "positive": sentiments["正向"],
            "neutral": sentiments["中性"],
            "negative": sentiments["负向"],
            "negative_rate": round(sentiments["负向"] / len(prepared), 4),
            "top_opportunity": topics[0]["name"] if topics else "暂无",
        },
        "records": prepared,
        "topics": topics,
        "keywords": [{"term": term, "count": count} for term, count in global_keywords],
        "trends": [dict(month=month, **counts) for month, counts in sorted(trend_counter.items())],
        "channels": [dict(channel=channel, **counts) for channel, counts in channel_counter.items()],
        "method": {
            "sentiment": "可解释的中英双语词典规则，支持评分融合与否定词修正",
            "topics": "字符/词元 TF-IDF + 余弦距离 K-Means，随机种子固定为 42",
            "priority": "反馈量、负向率、严重度的可调权重综合评分",
        },
    }
