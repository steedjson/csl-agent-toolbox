# 字体排印

## 选 family

- 1–3 个 family，各自承担明确角色：display（大标题）、正文、等宽（代码/数据）。最常见的两件套：一款有辨识度的 display 字体 + 一款干净的正文体。
- 避开被用滥的默认（Inter、Roboto、Arial、Fraunces 当首选）；中文场景注意字重覆盖（Noto Serif SC / Noto Sans SC 等有完整字重档）。
- Google Fonts 用一行加载：

```html
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@600&family=Noto+Sans+SC:wght@400;500&display=swap" rel="stylesheet">
```

- 每个 family 配一个 metrics 相近的系统 fallback，字体加载前显示的是它：`"Noto Serif SC", Georgia, serif`；`"Noto Sans SC", system-ui, sans-serif`。
- 本地字体文件放 `assets/`，用 `@font-face` + 相对路径引入；绝不上传到第三方托管。

## 字阶

- 全稿字号层级 ≤ 6 档，例如：display 48–64 / 标题 24–28 / 小标题 18–20 / 正文 14–16 / 辅助 12–13 / 微注 11。档与档之间差距要**看得出来**（相邻档 ≥1.25 倍），拉不开就砍档。
- 行高：标题 1.1–1.3，正文 1.4–1.6，微注 1.3。字重：标题不靠伪粗体；正文字重 400 起。
- 数字（价格、统计、表格）用 `font-variant-numeric: tabular-nums`。
- letter-spacing 不玩花招：默认 0；全大写小标签可加 0.05em–0.1em，仅此而已。
- 印刷品用 pt 思考（正文 ≥12pt），屏上用 px；同一稿内不混用两套单位描述同一角色。
