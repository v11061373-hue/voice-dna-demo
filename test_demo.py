"""voice-dna-demo 核心逻辑测试（无 key 走确定性降级；LLM 路径 monkeypatch）。"""
import demo


def test_parse_style_card_strips_markdown_and_fills_defaults():
    raw = '```json\n{"persona": "专家", "voice": "犀利"}\n```'
    card = demo.parse_style_card(raw)
    assert card["persona"] == "专家"
    assert card["voice"] == "犀利"
    assert card["catchphrases"] == []
    assert card["narrative_structure"] == "未知"


def test_build_style_card_fallback_without_key(monkeypatch):
    monkeypatch.delenv("VOICEDNA_API_KEY", raising=False)
    card = demo.build_style_card(profile="标书代写", samples="样本")
    assert set(card) == set(demo.STYLE_CARD_FIELDS)
    assert card["persona"] == demo.FALLBACK_STYLE_CARD["persona"]


def test_build_style_card_llm_path(monkeypatch):
    monkeypatch.setenv("VOICEDNA_API_KEY", "x")
    monkeypatch.setattr(
        demo,
        "call_llm",
        lambda prompt, system="", *, api_key=None, base_url=None, model=None: (
            '{"persona": "专家", "voice": "犀利"}'
        ),
    )
    card = demo.build_style_card(profile="p", samples="s")
    assert card["persona"] == "专家"
    assert card["voice"] == "犀利"


def test_generate_social_fallback(monkeypatch):
    monkeypatch.delenv("VOICEDNA_API_KEY", raising=False)
    out = demo.generate_content(
        dict(demo.FALLBACK_STYLE_CARD), "社媒", profile="标书代写", topics=["技术标"]
    )
    assert set(out) == {"自媒体内容", "话术", "导流", "节奏"}
    assert "技术标" in out["自媒体内容"]


def test_generate_ecommerce_fallback(monkeypatch):
    monkeypatch.delenv("VOICEDNA_API_KEY", raising=False)
    out = demo.generate_content(
        dict(demo.FALLBACK_STYLE_CARD), "电商", profile="标书代写"
    )
    assert set(out) == {"宣传策略", "标题", "详情", "客服话术"}


def test_track_hits_rid():
    assert demo._track("美妆博主") == "美妆"
    assert demo._track("标书代写服务号") is None


def test_fetch_region_hot_parses(monkeypatch):
    def fake_get(url, params=None, headers=None, timeout=None):
        class R:
            def raise_for_status(self):
                pass

            def json(self):
                return {"code": 0, "data": [
                    {"bvid": "BV1", "title": "把彩虹染到头发上", "typename": "美妆护肤", "play": 100, "description": ""},
                    {"bvid": "BV2", "title": "秋冬妆容", "typename": "美妆护肤", "play": 200, "description": ""},
                ]}

        return R()

    monkeypatch.setattr(demo.httpx, "get", fake_get)
    out = demo.fetch_bilibili_hot("美妆", 5)
    assert len(out) == 2
    assert out[0]["url"] == "https://www.bilibili.com/video/BV1"
    assert out[0]["tname"] == "美妆护肤"


def test_fetch_popular_fallback(monkeypatch):
    def fake_get(url, params=None, headers=None, timeout=None):
        class R:
            def raise_for_status(self):
                pass

            def json(self):
                return {"code": 0, "data": {"list": [
                    {"title": "电竞决赛", "desc": "", "tname": "电竞", "bvid": "BV2", "stat": {"view": 200}},
                ]}}

        return R()

    monkeypatch.setattr(demo.httpx, "get", fake_get)
    out = demo.fetch_bilibili_hot("标书代写", 5)
    assert len(out) == 1
    assert out[0]["title"] == "电竞决赛"


def test_has_key_with_explicit_key(monkeypatch):
    monkeypatch.delenv("VOICEDNA_API_KEY", raising=False)
    assert demo.has_key() is False
    assert demo.has_key("sk-user") is True


def test_call_llm_uses_passed_params(monkeypatch):
    monkeypatch.delenv("VOICEDNA_API_KEY", raising=False)
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["auth"] = headers["Authorization"]
        captured["model"] = json["model"]

        class R:
            def raise_for_status(self):
                pass

            def json(self):
                return {"choices": [{"message": {"content": "ok"}}]}

        return R()

    monkeypatch.setattr(demo.httpx, "post", fake_post)
    out = demo.call_llm(
        "p", api_key="sk-user", base_url="http://localhost:11434/v1", model="llama3"
    )
    assert out == "ok"
    assert captured["url"] == "http://localhost:11434/v1/chat/completions"
    assert captured["auth"] == "Bearer sk-user"
    assert captured["model"] == "llama3"


def test_build_style_card_uses_passed_key(monkeypatch):
    monkeypatch.delenv("VOICEDNA_API_KEY", raising=False)
    seen = {}

    def fake_call(prompt, system="", *, api_key=None, base_url=None, model=None):
        seen["api_key"] = api_key
        return '{"persona": "专家"}'

    monkeypatch.setattr(demo, "call_llm", fake_call)
    card = demo.build_style_card(profile="p", samples="s", api_key="sk-user")
    assert seen["api_key"] == "sk-user"
    assert card["persona"] == "专家"


def test_generate_content_uses_passed_key(monkeypatch):
    monkeypatch.delenv("VOICEDNA_API_KEY", raising=False)
    seen = {}

    def fake_llm(style_card, target, profile, topics, api_key):
        seen["api_key"] = api_key
        return {"宣传策略": "x", "标题": "y", "详情": "z", "客服话术": "w"}

    monkeypatch.setattr(demo, "_generate_llm", fake_llm)
    out = demo.generate_content(
        dict(demo.FALLBACK_STYLE_CARD), "电商", api_key="sk-user"
    )
    assert seen["api_key"] == "sk-user"
    assert set(out) == {"宣传策略", "标题", "详情", "客服话术"}
