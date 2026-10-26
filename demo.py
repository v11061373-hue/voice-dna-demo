"""voice-dna demo 核心：风格模仿内容生产管线（表达DNA → 定制内容），httpx-only。

Stage1 表达DNA = 主仓库 src/tools/style_mimic.py 的 7 字段风格卡抽取（同 prompt + schema）。
Stage2 定制内容 = 按目标生成：社媒=自媒体内容(笔记/脚本)+配套策略；电商=宣传策略+文案。
无 VOICEDNA_API_KEY 走确定性降级；有 key 真调 DeepSeek（OpenAI 兼容）。
"""
import json
import os

import httpx

STYLE_CARD_FIELDS = (
    "persona",
    "voice",
    "catchphrases",
    "sentence_patterns",
    "pacing",
    "narrative_structure",
    "visual_style",
)

FALLBACK_STYLE_CARD = {
    "persona": "内容创作者（未配置 DeepSeek，降级通用风格）",
    "voice": "口语化、直白",
    "catchphrases": [],
    "sentence_patterns": ["短句", "反问"],
    "pacing": "快节奏",
    "narrative_structure": "问题-分析-结论",
    "visual_style": "简洁字幕",
}

PRESET_BIDWRITER = {
    "profile": "招投标代写服务号：10 年标书经验，专治废标，技术标/商务标，3-5 天交付",
    "samples": (
        "【技术标怎么写才不废标】\n"
        "第一步：先啃评分标准，逐条响应，别自嗨。\n"
        "第二步：废标条款单独列清单，一条条销号。\n"
        "【商务标避坑】\n"
        "资质证书别过期，业绩证明要原件扫描。\n"
        "报价别拍脑袋，先算成本再留利润。"
    ),
}

STYLE_CARD_PROMPT_TEMPLATE = """\
# Role: 内容风格抽取器
## 任务
读入博主的文案样本，抽取其表达 DNA，输出结构化风格卡（JSON）。
## 输入
- 账号画像: {profile}
- 目标选题: {topics}
- 文案样本: {samples}
- 转录逐字稿: {transcripts}
## 抽取维度（缺样本就标注「未知」，不编造）
1. persona 人设/语气
2. voice 说话腔调
3. catchphrases 口癖/口头禅（原样摘录词表）
4. sentence_patterns 句式（开头句式/长短句/反问）
5. pacing 节奏（段落长度/停顿）
6. narrative_structure 叙事结构
7. visual_style 视觉风格
## 输出 schema（只输出 JSON）
{{"persona": "...", "voice": "...", "catchphrases": ["..."], "sentence_patterns": ["..."], "pacing": "...", "narrative_structure": "...", "visual_style": "..."}}
"""

SOCIAL_PROMPT_TEMPLATE = """\
# Role: 自媒体内容生产者
按给定表达 DNA 风格卡，为「{profile}」生成一篇可直接发布的自媒体内容，并配策略。
## 表达 DNA
{style_card}
## 目标选题
{topics}
## 输出 schema（只输出 JSON）
{{"自媒体内容": "模仿该风格的完整笔记/脚本正文", "话术": "评论区引导/抢单话术", "导流": "私信导流路径", "节奏": "发布节奏建议"}}
"""

ECOMMERCE_PROMPT_TEMPLATE = """\
# Role: 电商宣传策略师
按给定表达 DNA 风格卡，为「{profile}」生成电商宣传策略与文案。
## 表达 DNA
{style_card}
## 目标选题
{topics}
## 输出 schema（只输出 JSON）
{{"宣传策略": "整体宣传打法", "标题": "商品标题", "详情": "详情页文案", "客服话术": "客服应答话术"}}
"""

_SOCIAL_KEYS = ("自媒体内容", "话术", "导流", "节奏")
_ECOMMERCE_KEYS = ("宣传策略", "标题", "详情", "客服话术")


def _strip_markdown(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text


def parse_style_card(text: str) -> dict:
    data = json.loads(_strip_markdown(text))
    card: dict = {}
    for field in STYLE_CARD_FIELDS:
        if field in data:
            card[field] = data[field]
        elif field in ("catchphrases", "sentence_patterns"):
            card[field] = []
        else:
            card[field] = "未知"
    return card


def has_key() -> bool:
    return bool(os.environ.get("VOICEDNA_API_KEY"))


def call_llm(prompt: str, system: str = "") -> str:
    base_url = os.environ.get("VOICEDNA_BASE_URL") or "https://api.deepseek.com"
    model = os.environ.get("VOICEDNA_MODEL") or "deepseek-chat"
    key = os.environ.get("VOICEDNA_API_KEY", "")
    if not key:
        raise ValueError("未配置 VOICEDNA_API_KEY")
    messages = ([{"role": "system", "content": system}] if system else []) + [
        {"role": "user", "content": prompt}
    ]
    resp = httpx.post(
        base_url.rstrip("/") + "/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={"model": model, "messages": messages, "temperature": 0.3},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


BILIBILI_REGION_URL = "https://api.bilibili.com/x/web-interface/ranking/region"
BILIBILI_POPULAR_URL = "https://api.bilibili.com/x/web-interface/popular"
_BILI_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

# 赛道 → B站分区 rid（keyless 分区热榜 = 原生聚类，优于客户端关键词过滤）。
TRACK_RID = {
    "美妆": 157, "数码": 188, "美食": 211, "健身": 234, "宠物": 217,
    "游戏": 4, "汽车": 223, "旅游": 160, "母婴": 160, "职场": 36,
}


def _track(profile: str) -> str | None:
    """profile 命中赛道 → 返回赛道名；未命中返回 None。"""
    for track in TRACK_RID:
        if track in (profile or ""):
            return track
    return None


def fetch_bilibili_hot(profile: str = "", limit: int = 20) -> list[dict]:
    """keyless 拉 B站热榜：赛道命中 → 分区热榜（原生聚类）；未命中 → 综合热门。失败返回 []。"""
    track = _track(profile)
    try:
        if track is not None:
            resp = httpx.get(
                BILIBILI_REGION_URL,
                params={"rid": TRACK_RID[track], "day": 3},
                headers={"User-Agent": _BILI_UA},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            items = [
                {
                    "title": str(v.get("title", "")),
                    "desc": str(v.get("description", "") or "")[:100],
                    "tname": str(v.get("typename", "")),
                    "view": int(v.get("play") or 0),
                    "url": f"https://www.bilibili.com/video/{v.get('bvid', '')}",
                }
                for v in (data.get("data") or [])
            ]
        else:
            resp = httpx.get(
                BILIBILI_POPULAR_URL,
                params={"ps": limit, "pn": 1},
                headers={"User-Agent": _BILI_UA},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            items = [
                {
                    "title": str(v.get("title", "")),
                    "desc": str(v.get("desc", "") or "")[:100],
                    "tname": str(v.get("tname", "")),
                    "view": int((v.get("stat") or {}).get("view") or 0),
                    "url": (
                        f"https://www.bilibili.com/video/{v.get('bvid', '')}"
                        if v.get("bvid")
                        else f"https://www.bilibili.com/video/av{v.get('aid', '')}"
                    ),
                }
                for v in (data.get("data") or {}).get("list") or []
            ]
    except Exception:  # noqa: BLE001 — 网络/风控失败优雅降级为空
        return []
    return items[:limit]


def _fmt_transcripts(transcripts: dict | None) -> str:
    if not transcripts:
        return "（无）"
    return "\n".join(f"{u}：{t[:200]}" for u, t in transcripts.items())


def build_style_card(
    profile: str = "", topics: list | None = None, samples: str = "",
    transcripts: dict | None = None,
) -> dict:
    if not has_key():
        return dict(FALLBACK_STYLE_CARD)
    prompt = STYLE_CARD_PROMPT_TEMPLATE.format(
        profile=profile,
        topics=topics or [],
        samples=samples,
        transcripts=_fmt_transcripts(transcripts),
    )
    return parse_style_card(call_llm(prompt))


def generate_content(
    style_card: dict, target: str, profile: str = "", topics: list | None = None
) -> dict:
    """target: 社媒 → 自媒体内容+策略；电商 → 宣传策略+文案。"""
    topics = topics or []
    if has_key():
        return _generate_llm(style_card, target, profile, topics)
    if target == "社媒":
        return _generate_social_fallback(style_card, profile, topics)
    return _generate_ecommerce_fallback(style_card, profile, topics)


def _generate_llm(style_card: dict, target: str, profile: str, topics: list) -> dict:
    if target == "社媒":
        prompt = SOCIAL_PROMPT_TEMPLATE.format(
            profile=profile, style_card=json.dumps(style_card, ensure_ascii=False), topics=topics
        )
        keys = _SOCIAL_KEYS
    else:
        prompt = ECOMMERCE_PROMPT_TEMPLATE.format(
            profile=profile, style_card=json.dumps(style_card, ensure_ascii=False), topics=topics
        )
        keys = _ECOMMERCE_KEYS
    data = json.loads(_strip_markdown(call_llm(prompt)))
    return {k: data.get(k, "未知") for k in keys}


def _generate_social_fallback(style_card: dict, profile: str, topics: list) -> dict:
    topic = (topics or ["干货分享"])[0]
    phrases = "、".join(style_card["catchphrases"]) or "（无固定口癖）"
    body = (
        f"{topic}｜一篇讲清楚\n\n"
        f"人设：{profile or style_card['persona']}，{style_card['voice']}。\n"
        f"句式：{'、'.join(style_card['sentence_patterns'])}。口头禅：{phrases}。\n"
        f"结构：{style_card['narrative_structure']}；节奏：{style_card['pacing']}。\n"
        f"视觉：{style_card['visual_style']}。"
    )
    return {
        "自媒体内容": body,
        "话术": f"评论区引导：{style_card['voice']} 提问式互动，抛一个钩子",
        "导流": "主页简介放钩子 → 私信关键词领资料 → 转私域",
        "节奏": "周二/周四晚 8 点发布，T+1 复盘数据再调",
    }


def _generate_ecommerce_fallback(style_card: dict, profile: str, topics: list) -> dict:
    topic = (topics or ["核心单品"])[0]
    return {
        "宣传策略": f"用「{style_card['narrative_structure']}」结构讲卖点，主打{style_card['voice']}",
        "标题": f"{topic}｜{profile or style_card['persona']} 推荐",
        "详情": f"痛点 → 方案 → 效果，语气{style_card['voice']}，节奏{style_card['pacing']}",
        "客服话术": f"按{style_card['voice']}应答，先问需求再推方案，不硬广",
    }
