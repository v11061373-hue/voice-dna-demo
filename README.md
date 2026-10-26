# voice-dna demo

`voice-dna`（[仓库](https://github.com/v11061373-hue/voice-dna)）的在线 demo：
风格模仿内容生产管线——输入账号画像 + 文案样本，抽表达 DNA，再按目标生成定制内容。

## 管线

```
输入（画像 + 样本 + 选题） → ① 表达 DNA（7 字段风格卡） → ② 定制内容
```

| 目标 | ② 产出 |
|---|---|
| 社媒 | 自媒体内容（笔记/脚本，可直接发）+ 话术 / 导流 / 节奏 |
| 电商 | 宣传策略 + 标题 / 详情 / 客服话术 |

Stage ① 与主仓库 `src/tools/style_mimic.py` 同 prompt + 同 7 字段 schema
（persona / voice / catchphrases / sentence_patterns / pacing / narrative_structure / visual_style）。

## 数据源

- **预置例子**：标书代写账号（默认，零网络可跑）。
- **贴样本**：手动贴参考文案。
- **实时选题**：B站综合热门 keyless（`/x/web-interface/popular`），客户端按赛道关键词过滤（不聚类→聚类）。只喂选题，喂不了文案样本（样本需转录，主仓库 P5-E）。
- **实时搜索**（B站/小红书/抖音/微博）走主仓库 `trend_hunter` 的 cn-scraper（需登录），demo 不接。

## 本地跑

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

### 接 DeepSeek（可选）

不配 key 时走确定性降级卡；配 key 则真调 LLM：

```bash
$env:VOICEDNA_API_KEY = "sk-..."
# 可选：VOICEDNA_BASE_URL / VOICEDNA_MODEL（默认 deepseek-chat）
streamlit run streamlit_app.py
```

## 测试

```bash
python -m pytest -q
```

## 部署到 Streamlit Cloud

1. push 本仓库到 GitHub。
2. streamlit.io/cloud 用 GitHub 登录，New app 选本仓库，主文件 `streamlit_app.py`。
3. Secrets 里加 `VOICEDNA_API_KEY`（可选，不配则降级演示）。

---

> 作品集展示文本（叙事、截图、指标）后续另行设计。
