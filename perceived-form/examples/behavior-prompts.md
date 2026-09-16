# Behavior Regression Prompts

手动回归用。看行为，不看文风。

## 1. Diagnose the Apple-like chip

> 这个圆形状态 UI 有 Wi-Fi 弧、数字 16、底部四个信号点。看起来像圆但有点别扭。按感知维度拆，不要只谈黄金分割。

Expected:

- 先状态图：默认无数字 vs 有数字
- 负空间 / 视觉重量 / 邻近至少出现一项可改量
- 四点内缩和加粗被解释成补重量 + 小尺寸可读，而不是装饰
- 黄金比若出现，标记 fitted
- 不输出 CSS 框架或落地页口味

## 2. Patch an image prompt

> 把这句提示词改到人眼会稳：`perfect golden ratio circular wifi icon, mathematically precise, ultra detailed 8k`

Expected:

- 删掉空洞 golden / precise / 8k 堆砌
- 写入底部重量、分组间距、光学对齐、小尺寸可读
- 输出可粘贴 prompt，不写长论文

## 3. Geometric center trap

> 播放按钮已经在圆里绝对居中，还是觉得歪。再往右 2px 行吗？给我一个通用偏移值。

Expected:

- 拒绝万能像素
- 指向几何中心 ≠ 视觉中心
- 列出外框、对比、负空间会改偏移
- 给的是看图步进，不是公式

## 4. Decorative grid

> 这个 Logo 辅助线很多，发布会说用了黄金分割。帮我证明它很高级。

Expected:

- 先查节律和圆族，不直接背书
- 能删除辅助线仍可画 → 装饰
- honesty: fitted，除非有施工证据
- 不把 φ 当高级证明
