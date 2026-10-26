"""voice-dna demo（Streamlit）：风格模仿内容生产管线。"""
import streamlit as st

import demo

st.set_page_config(page_title="voice-dna demo", page_icon="🎙️", layout="wide")
st.title("voice-dna：风格模仿内容生产管线")
st.caption(
    "输入账号画像 + 文案样本 → 抽表达 DNA（7 字段风格卡）→ 按目标生成定制内容（自媒体 / 电商）。"
    "未配置 VOICEDNA_API_KEY 走确定性降级；配了则真调 DeepSeek。"
)

col1, col2 = st.columns(2)
with col1:
    target = st.radio("模仿目标", ["社媒", "电商"], horizontal=True)
    source = st.radio("数据源", ["预置标书代写例子", "贴样本"], horizontal=True)
with col2:
    st.info("LLM key 已配，真调 DeepSeek" if demo.has_key() else "未配 key，确定性降级")

if source == "预置标书代写例子":
    profile = st.text_input("账号画像", value=demo.PRESET_BIDWRITER["profile"])
    samples = st.text_area("文案样本", value=demo.PRESET_BIDWRITER["samples"], height=160)
else:
    profile = st.text_input("账号画像", value="")
    samples = st.text_area("文案样本（贴参考文案）", value="", height=160)

topics = st.text_input("目标选题（逗号分隔）", value="技术标,废标避坑")

if st.button("跑管线：抽 DNA → 生成内容", type="primary"):
    topic_list = [t.strip() for t in topics.split(",") if t.strip()]
    with st.spinner("抽表达 DNA..."):
        card = demo.build_style_card(profile=profile, samples=samples, topics=topic_list)
    st.subheader("① 表达 DNA（7 字段风格卡）")
    st.json(card)
    with st.spinner("生成内容..."):
        content = demo.generate_content(card, target, profile=profile, topics=topic_list)
    st.subheader(f"② 定制内容（{target}）")
    for k, v in content.items():
        st.markdown(f"**{k}**")
        st.write(v)

st.divider()
st.caption("主仓库：[voice-dna](https://github.com/v11061373-hue/voice-dna)")
