# Optical Correction

Load when geometry already looks correct on a grid, or when the user mentions 马赫带、侧抑制、视觉中心、Retina 字体、播放按钮不居中。

## Principle

人眼不是光度计。视锥细胞有侧抑制：一个感光单元被强光刺激后，相邻单元被压低。边缘会被大脑重新计算，于是出现：

- **马赫带**：连续灰阶上的假边缘、假十字星
- **同时对比**：同一灰，邻域不同就看成不同
- **阿德尔森棋盘阴影**：物理等明度，人眼读成不等

美感 = 图形匹配这套有 bug 的算法，大脑处理变轻。Optical Correction 是将错就错，不是把物理值再调准一次。

## What to correct

| 现象 | 典型几何正确 | 人眼要的 |
|---|---|---|
| 正圆 icon 发飘 | 圆心、半径、线宽一致 | 底部重量、点内缩 |
| 播放三角偏左 | bounding box 居中 | 视觉质量中心右移 |
| 箭头/chevron 偏轻 | 路径对齐像素格 | 杆更粗或头更前 |
| 大写字母光学偏矮 | 帽高对齐 | overshoot 穿出基线/帽线 |
| 小字发灰 | 矢量轮廓正确 | 加墨、简化、针对小尺寸的脏补偿 |
| 高对比描边辉光 | 1px 居中描边 | 内缩、不对称描边、降同时对比 |
| 深色底白线更粗 | 同一 stroke | 暗底减线宽或减对比 |

没有万能偏移。外框形状、颜色、明暗、边距、负空间都会改「往右多少刚好」。

## Procedure

1. 在真实尺寸、真实背景上看，不在放大网格上看。
2. 标出几何中心和目测质量中心。两者不重合就进入校正，不要先找 φ。
3. 一次只改一个量：偏移、线宽、内缩、面积、对比。改完立刻在目标尺寸复核。
4. 记录介质：1x 状态栏、桌面 2x、打印、视频 16:9 安全区，校正不可互拷。
5. 变量仍打架时，用 A/B 小步进，不发明新公式。

## Prompt language

生图 / 改图时，用可执行的感知指令替换空洞比例词：

```text
optical alignment over geometric centering;
bottom-heavy visual weight; grouped marks tighter than their gap to the rim;
slight inset of small status dots; avoid mathematically perfect circles if they feel top-light;
compensate Mach-band glow on high-contrast edges; true size legibility over construction grid
```

禁止只写：`golden ratio, perfect symmetry, mathematically precise, ultra sharp`.

## AI boundary

黄金分割、φ、137.5°、Fibonacci Circles 是规则，模型学得快。Optical Correction 依赖当前外框和对比，平均解容易，极端最后一公里仍要看图。不要宣称本 Skill 能算出唯一正确偏移。
