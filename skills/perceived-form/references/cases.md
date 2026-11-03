# Cases

Load when diagnosing a similar artifact, or when the user mentions 苹果折叠屏状态 UI、YouTube 播放键、Retina 字体、锤子 Logo、Twitter 鸟。案例用来迁移原则，不用来复制像素。

Source boundary: 西西米修斯 / @Sisymithus, X article *我把苹果这个UI 揭秘了，看看苹果设计师到底在想什么？* (2026-09-15). Treat geometric overlays as the author's fitted reading, not Apple construction documents.

## Apple foldable status chip

Circular-looking chip: Wi-Fi arcs, optional battery numeral (e.g. 16), four signal dots.

| Dim | Observation | Principle |
|---|---|---|
| 假圆 | 看起来像圆，不是正圆，第一眼别扭 | 人眼对微小形状差敏感 |
| 点内缩 | 四点不在外圆弧轨道上，整体往里 | 小尺寸仍可分离 |
| 点更粗 | 点直径 > 外圈线宽，轻微侵入内侧 | 可读 + 底部补重量 |
| 负空间 | Wi-Fi 倒三角越往下两侧黑面积越少 | 下半空，必须补 |
| 重量 | 对折后无点版本发飘；四点稳住下半圆 | 功能点兼压舱物 |
| 默认态 | 无数字是主路径；「16」侵占上方后仍不完全对称 | 主路径极致，兼容路径补偿 |
| 邻近 | 点间距 < 点到外圈距离 | 间距 = 分组语法 |
| 尺子 | 外弧/外圈、电量弧/数字弧可能近 φ；数字曲率或落在 Fibonacci 圆上 | 反复出现才像语言；作者自承拟合 |
| 产品迁移 | 不为左右手/全场景先做中性平均 | 先做一条最漂亮的路 |

迁移口令：状态类图形先定默认态；用小元件给瘦的一侧补重量；分组靠间距，不靠均分。

## YouTube play triangle

Bounding box 居中时三角光学偏左。几何中心不是视觉中心。右移多少取决于圆框、对比、负空间，没有固定像素。用来挡住「我已经居中了为什么还歪」。

## Retina / small-size type

为小字设计的轮廓，放大像畸变，缩小才清晰。这是针对人眼和像素格的过补偿，不是把矢量做脏。判字标、tab 标签、状态栏数字时必须看目标尺寸。

## Logo circle families

Twitter 鸟、百事、苹果等常被拆回 Fibonacci 圆。合法结论：复杂曲线可以共享圆族，所以耐看。非法结论：大品牌都按同一张施工图画。品牌越大图形越简单，越经不起随便画——简单来自约束，不是来自装饰网格。

## Hammer logo (anti-case)

辅助线、爆炸图、发布会叙事都可以很满，只要轮廓没有共同节律，就是纯装饰。辨识度和耐看度上不来。问句：删掉标注，这套曲线还是不是一个系统。

## How to cite in output

写「类似苹果状态 chip 的底部补重量」，不要写「按苹果专利像素重做」。需要黄金家族时标明 `fitted`，除非另有官方 construction。
