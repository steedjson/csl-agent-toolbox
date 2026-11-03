---
name: html-design-draft
description: 用户要"看得见的成品设计稿"——海报、传单、界面 mockup、落地页视觉稿、信息图或示意图——但还不到开发真实应用的时候用：在工作目录建一个设计稿文件夹，每块画板一个自包含 HTML（浏览器双击即看，零依赖零构建），index.html 汇总导航，assets/ 放图片与字体。产出是纯 HTML/CSS 静态稿，不是可运行应用。整体审美方向未定先走 frontend-design 或 design-taste-frontend；要沉淀长期设计系统用 ui-design-system；要写真实前端项目不用本技能。
---

# 设计稿（自包含 HTML）

一份设计稿 = 工作目录下一个文件夹 `<draft>/`（按标题起个简短名字，如 `spring-menu/`，不以点开头）。浏览器直接打开就能看：不依赖服务器、构建或本技能之外的任何东西。同一会话做多份设计稿时各用各的目录，绝不在已有目录旁边另起一份、绝不复用别人的目录。

只把文件写进 `<draft>/`。草稿不是交付物：除非用户要求，绝不 commit、push。

## 目录约定

- `<draft>/boards/<name>.html`：每块画板一个**自包含**文件。`<name>` 小写字母/数字/连字符，stem 不重复；每块画板是独立成品，复制粘贴打开任何一块都完整可看。
- `<draft>/assets/`：图片（png/jpg/webp/svg）与字体文件，画板用相对路径 `../assets/<file>` 引用。不写 base64，不用 `data:` URI。
- `<draft>/index.html`：汇总页，列出全部画板并按比例缩放预览（iframe 包一层固定比例容器 + `transform: scale()`），点击打开画板原文件。**最后**写它。

一份设计稿建议 ≤ 24 块画板、总大小 ≤ 64 MB。

## 画板骨架

```html
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>春季菜单 · 海报</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@600&family=Noto+Sans+SC:wght@400;500&display=swap" rel="stylesheet">
<style>
  html, body { margin: 0; }
  .board {
    width: 880px; height: 560px; box-sizing: border-box;
    padding: 64px; display: flex; flex-direction: column; gap: 24px;
    background: #FAF6EF; color: #2B2118;
  }
  .board h1 { margin: 0; font: 600 56px/1.15 "Noto Serif SC", serif; }
  .board p { margin: 0; font: 400 20px/1.5 "Noto Sans SC", sans-serif; color: #5E594F; }
</style>
</head>
<body>
<div class="board">
  <h1>春季菜单</h1>
  <p>豌豆汤 · 时令沙拉 · 香草烤春鸡</p>
  <img src="../assets/soup.jpg" alt="豌豆汤" style="width: 240px; height: 160px; object-fit: cover">
</div>
</body>
</html>
```

## 踩坑规则（每条违反都是悄悄失效）

- 网络请求只允许 Google Fonts（`fonts.googleapis.com` / `fonts.gstatic.com`）与本地 `assets/`；无其他外链、无 CDN、无统计脚本。画板里**绝不**出现 `<script>`、`<iframe>`、`<object>`、`<embed>`（index.html 的预览 iframe 除外）。
- 根元素规则：海报、社交媒体图、手机 mockup、印刷品的根元素**固定** `w`×`h`（px）；网页、落地页、仪表盘的根元素**流式**——不写 px 宽度，用带左右 padding 的 `max-width` 容器，内部用 `%`/`rem`/`fr`，grid 在手机宽度收成单列（`repeat(auto-fit, minmax(min(<min>px, 100%), 1fr))`）。高度按内容自然生长，`vh` 只用于占满整屏的根元素。
- 成组的兄弟元素（按钮排、卡片、导航项、工具栏）用 `display: flex`/`grid` 加 `gap` 排布，不靠源码空白和逐元素 margin；行内排版只留给成段文字。
- 图标用行内描边 SVG，**绝不用 emoji**；装饰性 SVG 加 `aria-hidden="true"`，表意 SVG 加 `role="img"` 与 `aria-label`。
- 控件画真元素：`<button>`、`<a href>`、`<input>` 配 `<label>`；绝不在 div/span 上堆 `role` 或 `onclick`（Tab 键会跳过）。只有图标的按钮加 `aria-label`。
- 文字对比度 ≥ 4.5:1（24px 及以上 3:1）。最常不达标的是说明文字的灰、白字压彩色填充：两者都加深。需要区分的颜色在明度上也要不同，不能只靠色相；蓝/橙优于红/绿。
- 复刻有源码的界面时从源码抄确切的值（内边距、圆角、字号、行高），不四舍五入、不凭训练记忆；读不到源码就说明，不编造。不复刻他人受版权保护的设计，除非用户显然在该公司工作。
- 常用尺寸档：手机 App mockup 390×844；桌面网页稿宽 1280–1440；A4 海报 794×1123（96dpi，印刷交付正文 ≥12pt）；社交方图 1080 等比做 540×540。
- 触控目标 ≥44px；mockup 里的可点元素同样适用。
- 每块画板的 `<title>` 写「主题 · 板名」，非空。

## 新建流程

1. **扎根上下文**：先读用户给的材料——品牌色、字体、现有产品截图、设计系统文件、代码仓库。用户提了产品却什么都没附？去要（一个链接、一张截图），不闭眼设计。从零 mock 一整个产品是最后手段。
2. **方向未定先定方向**：有人可问时用 AskUserQuestion 问，或先出 2–4 块**真正不同**的低保真方向稿（每块探索一条说得出名字的维度，同一审美的几种深浅不算选择；问法见 `references/questions.md`）。无人可问就自定一个叫得出名字的方向，并用一行声明假设，绝以问题收尾。方向一旦定下就一直算数。
3. **定一套小体系**：1–3 个字体 family、一个底色 + 一个墨色、0–2 个 accent；规则见 `references/color.md` 与 `references/typography.md`。已有品牌或设计系统时精确沿用它的值，优先于上述默认。
4. **逐板写作**：写完一个文件再写下一个；文字内容扎根用户材料，缺的真实信息（价格、日期、地址）放显眼占位 `[待填：价格]`，绝不编造，绝不用 lorem ipsum（纪律全文见 `references/craft.md`）。做示意图先读 `references/craft.md` 的示意图一节。
5. **写 index.html** 汇总全部画板。
6. **自检**：运行 `python3 <本技能目录>/scripts/check_design.py <draft>`，改掉它列出的每个问题，直到零问题；再对照上文「踩坑规则」逐条过一遍。发现问题时先修复再交付。
7. 交付：附 `index.html` 路径，用一行说明做了什么、做了哪些假设、备选之间怎么选。

## 修改流程

改之前**重读**文件，在当前文本上改，绝不用记忆里的副本。定点修改只改那一处：用户要求改某段文字、某个颜色，就只改它，其余 layout、间距、字体原封不动；重新设计或换方向是另一种请求，那时才做大改动。加/删画板同步更新 index.html。在已有设计上添加内容时先理解它的视觉语汇（copy 口吻、配色、密度、圆角、阴影），照着来。

## 调用

- 用文件工具写文件（Write/Edit），不用 shell 拼大段 HTML。
- 校验：`python3 <本技能目录>/scripts/check_design.py <draft>`——检查画板自包含性（禁 script/iframe/外链/data URI）、本地资源存在性、结构必备项（doctype/lang/charset/title）、index 与画板对应关系。校验器查不出美的问题，踩坑规则与 craft.md 仍要人工过。

## 参考页

本技能 `references/` 下：`craft.md`（设计纪律全文，动手前读）、`color.md`、`typography.md`、`questions.md`（何时问、怎么问）。
