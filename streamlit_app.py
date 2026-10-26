"""voice-dna demo（Streamlit）：风格模仿内容生产管线。

数据源前置：预设案例（零网络） / 接真实数据（B站热榜 + 贴样本）。
轻量文字版：文本 → 表达 DNA → 文本；ASR/视觉识别在完整项目 voice-dna。
"""
import streamlit as st

import demo

st.set_page_config(page_title="voice-dna", page_icon="🎙️", layout="wide")

st.title("voice-dna")
st.caption("风格模仿内容生产管线 · 输入账号画像 + 文案样本 → 抽表达 DNA → 按目标生成定制内容")

st.warning(
    "**轻量文字版演示**：输入文案样本（文本），输出可直接发布 / 阅读的文本内容。"
    "语音转写（ASR，音视频转文字）与视觉识别**不在本 demo**——在完整项目 "
    "[`voice-dna`](https://github.com/v11061373-hue/voice-dna) 里："
    "`src/tools/video_download.py` 拉视频素材、`transcribe.py` 语音转文字、`video_vision.py` 视觉识别。"
    "本 demo 只演示「文本 → 表达 DNA → 文本」这一段。"
)

st.divider()

st.subheader("① 数据源")
source = st.radio(
    "选择数据源",
    ["预设案例：标书代写账号（零网络可跑）", "接真实数据：B站热榜 + 贴样本"],
    horizontal=True,
)

st.subheader("② 模仿目标")
target = st.radio("生成目标", ["社媒", "电商"], horizontal=True)

hot_topics: list[str] = []
if source.startswith("预设案例"):
    profile = st.text_input("账号画像", value=demo.PRESET_BIDWRITER["profile"])
    samples = st.text_area("文案样本", value=demo.PRESET_BIDWRITER["samples"], height=160)
else:
    profile = st.text_input("账号画像（填赛道关键词，如：美妆 / 数码 / 美食 / 健身）", value="")
    st.markdown("**实时选题：B站热榜（keyless，赛道命中走分区热榜原生聚类）**")
    if st.button("拉 B站热榜", key="hot"):
        with st.spinner("拉取热榜..."):
            st.session_state["hot"] = demo.fetch_bilibili_hot(profile=profile, limit=20)
    hot = st.session_state.get("hot") or []
    if hot:
        opts = [f"{h['title']}（{h['tname']}·{h['view']}播放）" for h in hot]
        picked = st.multiselect("选中要用的选题", opts, default=opts[:3])
        hot_topics = [p.split("（")[0] for p in picked]
    else:
        st.caption("无命中：赛道不在词表或网络失败。可贴样本 + 手动填选题。")
    samples = st.text_area("贴文案样本 / 转录逐字稿（文本，喂表达 DNA）", value="", height=140)

topics = st.text_input(
    "目标选题（逗号分隔，可留空用热榜）",
    value="" if source.startswith("接") else "技术标,废标避坑",
)

st.subheader("③ 跑管线")
st.caption("LLM 已配，真调 DeepSeek" if demo.has_key() else "未配 key，确定性降级演示")
if st.button("抽表达 DNA → 生成内容", type="primary"):
    topic_list = [t.strip() for t in topics.split(",") if t.strip()] + hot_topics
    with st.spinner("抽表达 DNA..."):
        card = demo.build_style_card(profile=profile, samples=samples, topics=topic_list)
    st.markdown("**① 表达 DNA（7 字段风格卡）**")
    st.json(card)
    with st.spinner("生成内容..."):
        content = demo.generate_content(card, target, profile=profile, topics=topic_list)
    st.markdown(f"**② 定制内容（{target}）**")
    for k, v in content.items():
        st.markdown(f"**{k}**")
        st.write(v)

st.divider()
st.caption("完整项目：[voice-dna](https://github.com/v11061373-hue/voice-dna)")
