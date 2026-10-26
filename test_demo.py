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
        demo, "call_llm", lambda prompt, system="": '{"persona": "专家", "voice": "犀利"}'
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
