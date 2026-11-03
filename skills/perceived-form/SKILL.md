---
name: perceived-form
description: Diagnose and correct visual form so it matches how human eyes actually see, not how geometry measures. Covers negative space, visual weight, proximity grammar, default-vs-compat states, golden-family rulers, Mach bands, and optical correction. Use when a UI, icon, logo, layout, type, or image prompt looks off despite aligned geometry; when the user mentions 视觉重量, 负空间, 邻近原则, 光学校正, 马赫带, 几何中心, 黄金分割, Fibonacci circles, 发飘, 头重脚轻, Apple status UI, or "看起来像圆其实不是正圆". Do not use for landing-page taste, CSS stack choice, or dashboard theming.
---

# Perceived Form

设计真正面对的，不是几何本身，而是人最终怎么「看见」它。

本 Skill 把图形拆成可诊断维度：先查空间语法和状态策略，再用黄金家族当尺子，最后做人眼 Optical Correction。黄金比是尺子，不是病因。

邻近 Skill：落地页口味 / 栈 / anti-slop 用 `design-taste-frontend`。读浏览器、截图转需求用 `browser-ui-reader`。本 Skill 不选框架、不写 CSS 架构。

## Resource Guide

按需加载，不要一次读完：

- 维度词典、信号词、处方：`references/dimensions.md`
- 马赫带、侧抑制、几何中心 ≠ 视觉中心、校正手法：`references/optical-correction.md`
- Golden Ratio / Circles / Angle，以及过拟合禁令：`references/golden-family.md`
- 锚点案例（苹果状态 UI、YouTube 三角、Retina 字体、Logo 重构、锤子反例）：`references/cases.md`
- 行为回归 prompt：`examples/behavior-prompts.md`

## 工作流程

### 0. 读物

先用一两句锁定对象，再诊断：

```text
Reading this as: <icon | status chip | logo | type | layout | image prompt>
states: <default / numbered / compact / dark / ...>
complaint: <发飘 | 挤 | 散 | 假圆 | 头重脚轻 | 对齐了仍别扭 | unset>
```

用户没说别扭点时，不要问清单。默认按「几何已齐、观感未齐」扫描。只有默认态 vs 兼容态会导向完全相反的处方时，才问一个问题。

### 1. 状态图

列出这个图形会经历的状态。至少标：

- 主路径 / 默认态（出现最多、品牌最先被看到的那个）
- 兼容态（有数字、有角标、小尺寸、高对比、深色）
- 每个状态谁在占空间、谁在丢重量

规则：**主路径极致，兼容路径补偿**。不要为所有状态做平均方案。

### 2. 按层扫描，不要按灵感扫描

固定顺序。每层最多记 2 个负载问题。没有证据的层写 `n/a`，不要编黄金分割。

| 层 | 维度 | 先问 |
|---|---|---|
| A 空间语法 | 负空间、视觉重量、邻近、几何中心 vs 视觉中心 | 哪块黑/白在发飘？谁和谁该是一组？ |
| B 状态策略 | 默认态优先级、小尺寸可读、侵入/内缩补偿 | 默认态漂亮是否牺牲了兼容态？ |
| C 约束尺子 | Ratio / Circles / Angle、同一套曲线语言 vs 装饰网格 | 反复出现的比例，还是一次拟合？ |
| D 人眼最后一公里 | 马赫带、侧抑制、光学校正、介质 bug | 物理齐了，视锥细胞会怎么改写？ |
| E 诚实性 | 后验重构、过拟合、名字数学原理不数学 | 有没有施工证据？ |

A/B 未查完，禁止用 φ 解释问题。C 只在同一套关系反复出现时升级为「设计语言」。D 是收尾，不是可选项。

需要处方或原理时再读对应 reference。

### 3. 归因

每个问题写成一条因果，不要写感受词：

```text
[dim] <dimension>
[see] <人眼看到什么>
[geo] <几何上实际如何>
[fix] <最小校正>
[cost] <这条校正牺牲了什么>
```

好的归因指向可改的量：面积、间距、线宽、内缩、偏移、曲率族、默认态优先级。坏的归因停在「不够高级」「再加点黄金分割」。

### 4. 开处方

按任务类型输出，不要混：

- **审图 / 拆 UI**：诊断报告。指出 2–4 个最高杠杆问题，按 A→D 排序。
- **改 UI / 图标 / 字标**：给出具体几何调整（内缩、加重量、拉开组距、光学偏移），并声明默认态优先还是兼容态优先。
- **生图 / 改 prompt**：在提示词里写入人眼最后一公里，而不是只写 `golden ratio, Fibonacci, 8k, perfect circle`。
- **Logo / 品牌曲线**：先查是否同一套圆族；再警告后验网格。装饰辅助线没有节律就判无效。

### 5. 停

满足以下任一即停：

- 已给出默认态可执行的校正，兼容态有补偿策略
- 用户只要解释，不要求改
- 证据只够到「拟合」，已标明不是官方施工
- 任务其实是落地页口味或读页面，应转邻近 Skill

## 输出协议

审图默认用这个骨架，短任务可砍掉空段：

```md
## Read
<object>, <states>, <complaint>

## State map
- default:
- compat:
- priority:

## Findings
| Layer | Dim | Geo | Seen | Fix |
|---|---|---|---|---|

## Prescription
1.
2.

## Prompt / spec patch
- add:
- remove:
- keep:

## Honesty
- constructed / fitted / unknown
- unused golden claims: none | listed
```

生图任务把 Prescription 压成可粘贴的 prompt 增量，不写长文。

## 全维度索引

完整定义、信号、反例见 `references/dimensions.md`。运行时按层取，不要当百科背诵。

**A 空间语法**

1. 负空间（Negative Space）
2. 视觉重量（Visual Weight Balance）
3. 邻近原则（间距即语法）
4. 几何中心 ≠ 视觉中心

**B 状态策略**

5. 主路径极致，兼容路径补偿
6. 小尺寸可读 vs 数学整齐
7. 侵入 / 内缩 / 线宽差作为补重量

**C 约束尺子**

8. Golden Ratio（尺度关系）
9. Golden / Fibonacci Circles（曲率家族）
10. Golden Angle 137.5°（分布 / 旋转）
11. 同一套几何语言 vs 装饰网格

**D 人眼最后一公里**

12. 人眼不物理（侧抑制、马赫带、同时对比）
13. Optical Correction（偏移、过冲、重量补偿）
14. 介质 bug（Retina 小字、高对比边缘、icon 像素格）
15. 变量爆炸 → 训练直觉是压缩计算，不是玄学

**E 诚实性**

16. 后验拟合 ≠ 原始施工
17. 名字数学、机制不数学（含股市斐波那契回撤这类误用）

## 边界

- 不把 φ、137.5°、Fibonacci 圆写成因果，除非同一关系在多个位置重复出现。
- 不把民间 Logo 拆解图当官方原稿。Rob Janoff 没按那些网格画苹果标。本 Skill 自己的拆解默认也是拟合。
- 不把锤子式装饰辅助线当成「有设计」。没有节律 = 纯装饰。
- 不给股市、指标、玄学比例提供有效性背书。
- 不复制受版权保护的苹果像素资产；只讨论可复用的感知原则。
- 不做无障碍全量审计、品牌策略、前端栈选型。对比度/触控面积只在影响「看见」时点一句。
- 不因为「全维度」就十六维全写。没证据的维写 `n/a`。

## 质量标准

一次合格输出必须：

- 先有对象和状态图，再有黄金比
- 至少动到 A 或 B 中的一个可改量
- 每个处方能改面积、间距、偏移、线宽、曲率族或状态优先级之一
- 明确 constructed / fitted / unknown
- 生图时删除空洞的 `perfect symmetry, golden ratio, ultra detailed` 堆砌，换成重量、邻近、光学偏移
- 能指出若只做几何对齐，人眼仍会感到什么

自检失败信号：通篇 φ；没提默认态；把「发飘」当成品味问题；给 YouTube 三角一个固定像素偏移当万能值。
