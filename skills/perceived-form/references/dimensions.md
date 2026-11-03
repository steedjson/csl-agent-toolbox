# Dimension Dictionary

Load this when diagnosing, or when the user asks 「有哪些维度」. Use the layer order from `SKILL.md`. Quote a dimension only if the artifact actually shows its signal.

Each entry: job, see, geo, fix, fail.

## A. Spatial grammar

### 1. Negative Space

- Job: 黑色/白色块的面积分布，决定图形稳不稳。
- See: 某一扇区空、某一扇区塞；倒三角结构越往下两侧越瘦。
- Geo: 轮廓可能仍对称、仍居中、仍贴网格。
- Fix: 给空的一侧补面积（点、线宽、内缩块、衬底），或减掉过重一侧。
- Fail: 只改描边颜色，不改面积。

### 2. Visual Weight Balance

- Job: 让上下左右的「看起来的质量」够稳，不是让外接圆完美。
- See: 发飘、头重脚轻、上沉下轻、一边被数字/图标吸走。
- Geo: 对折后面积不等；上半有数字，下半只剩细弧。
- Fix: 底部补重量、加厚、内侵、重复小元素成组。功能元素可以同时扛重量。
- Fail: 把所有元素做成一样大以求公平。

### 3. Proximity

- Job: 间距编码分组。同组近，跨级远。
- See: 信号点散成装饰；数字和弧抢同一圈；元素像洒在盘子上。
- Geo: 点与点的间隙 ≤ 点到外圈的间隙，才读成一组。字距/行距/段距是同一语法。
- Fix: 先定组，再定组间空白。空白是句子，不是通风口。
- Fail: 用居中和均分代替分组。

### 4. Geometric center ≠ visual center

- Job: 对齐眼睛的质量中心，不是 bounding box 中心。
- See: 三角、箭头、非对称字标光学偏左/偏上；圆里的字形「沉」。
- Geo: 数学中心已居中。
- Fix: 向视觉轻的一侧做光学偏移。偏移量随外框、对比、留白变，没有万能像素。
- Fail: 给所有播放按钮规定 +2px。

## B. State strategy

### 5. Default-path extreme, compat-path compensation

- Job: 先把出现最多的状态做到最漂亮，其他状态再补。
- See: 无数字时完美，有「16」后头重；为双手/全场景做中性平均后，主路径变平。
- Geo: 兼容态侵占默认态的负空间。
- Fix: 锁定默认态构图；兼容态用更大点、内缩、字重、弧长去补，而不是重做平均构图。
- Fail: 一开始就为所有角标/数字宽度做死对称。

### 6. Small-size readability vs mathematical neatness

- Job: 缩到状态栏尺寸后，结构仍可辨。
- See: 细线点贴在外弧上，缩小后糊成一圈脏边。
- Geo: 点直径 = 线宽、点心落在弧线上，最整齐。
- Fix: 点大于线宽，整体内缩，允许轻微侵入内侧。
- Fail: 以 1x 矢量预览当最终效果。

### 7. Inset / intrusion / stroke mismatch as ballast

- Job: 用「不齐」换稳定和可读。
- See: 点不在轨道上；点比描边粗；弧与点有意错位。
- Geo: 不闭合、不共线、不共宽。
- Fix: 把不齐写成有意补偿，并检查它是否真的补了重量或可读性。
- Fail: 把所有不齐都解释成苹果匠心。无功能的不齐是脏。

## C. Constraint rulers

### 8. Golden Ratio

- Job: 两个主要尺度的关系尺，约 1 : 1.618。
- See: 外弧 vs 外圈、电量弧 vs 被数字占掉的弧，反复接近同一比。
- Geo: 一次接近可能是巧合。
- Fix: 用来约束「哪一段该更长」，不用来解释发飘。
- Fail: 任何好看的东西都标 φ。

### 9. Golden / Fibonacci Circles

- Job: 把 1, 1, 2, 3, 5, 8, 13… 收成一套圆，主要弧从这套圆取。复杂曲线讲同一种语言。
- See: 大小不同的弧仍同族；数字 6/8/2/5 的曲率落在某一号圆上。
- Geo: 你不能想怎么弯就怎么弯。
- Fix: 先定圆族，再裁弧。Logo 尤其有效。
- Fail: 事后把轮廓塞进一堆圆，再宣称设计师就是这么画的。

### 10. Golden Angle 137.5°

- Job: 360° × 0.382 的分布尺。叶序、双螺旋、环形排列的候选约束。
- See: 重复元件绕心的步进接近 137.5°，而不是 90°/45° 网格。
- Geo: 角度漂亮不等于重量平衡。
- Fix: 只在有旋转/分布问题时启用。
- Fail: 在状态栏图标上强行找 137.5°。

### 11. Shared geometric language vs decorative grid

- Job: 约束产生节律。网格必须改变曲线决策，否则是装饰。
- See: Twitter 鸟可拆回圆族；锤子 Logo 辅助线很多但轮廓无共同曲率。
- Geo: 标注线 ≠ 生成规则。
- Fix: 问「删掉这些辅助线，轮廓还能不能画出来」。能 = 装饰。
- Fail: 发布会上的爆炸图当证明。

## D. Perception last mile

### 12. Eyes are not physical

- Job: 视锥侧抑制会改写边缘和明暗。物理连续，人眼可能看见马赫带、十字星、棋盘错觉。
- See: 等宽灰阶出现假边；高对比描边发糊或发亮；A/B 块明度其实相同。
- Geo: 色值/灰阶正确。
- Fix: 进入 Optical Correction。不要再加更多「正确几何」。
- Fail: 用取色器反驳用户的「看着不一样」。

### 13. Optical Correction

- Job: 将错就错，取悦有 bug 的视觉算法。
- See: 仍别扭的正圆、光学偏掉的三角、小字发灰。
- Geo: 已对齐、已均分、已黄金。
- Fix: 过冲、加重量、偏心、拉开对比、改负空间。细节见 `references/optical-correction.md`。
- Fail: 找一个固定公式覆盖所有外框和对比。

### 14. Medium bugs

- Job: 校正依赖介质。Retina 小字、状态栏 1x/3x、深色 OLED、打印、压缩 JPEG 各有各的 bug。
- See: 放大像怪物、缩小才清晰；大图好看、toolbar 里塌。
- Geo: 同一份矢量。
- Fix: 在真实尺寸、真实背景、真实 PPI 上判，不在无限画布上判。
- Fail: 只看 Figma 200% 视图。

### 15. Variable explosion → trained intuition

- Job: 外框、颜色、明暗、负空间、字重同时变，精确计算成本过高。直觉是压缩后的快速计算。
- See: 「再往右一点点刚好」无法从 φ 推出来。
- Geo: 变量组合爆炸。
- Fix: 先用 A–C 把搜索空间缩小，最后用小步进目视。AI 平均美感可用；极端最后一公里仍要看图。
- Fail: 把「看感觉」写成无需训练的天赋，或写成可被 φ 取代。

## E. Honesty

### 16. Fitted ≠ constructed

- Job: 后验能贴上网格，不证明原作按网格施工。
- See: 苹果 Logo 民间几何图版本极多；拆解自己也能对上 2 号圆。
- Geo: 拟合残差被忽略。
- Fix: 标注 `fitted`。只有设计师手稿、官方 construction、或同一语言在多处重复，才升到 `constructed`。
- Fail: 「我量到了，所以苹果就是这么想的」。

### 17. Mathematical name, unmathematical mechanism

- Job: 阻止把设计尺乱用到预测术。
- See: 股市斐波那契回撤、万能神比例、任何领域的 φ 崇拜。
- Geo: 名字来自数学，有效性没有机制。
- Fix: 尺子留在图形约束里。跨域宣称一律切断。
- Fail: 用向日葵证明股价。

## Scan heuristics

用户口语 → 先查哪一维：

| 口语 | 先查 |
|---|---|
| 发飘、不稳、头重脚轻 | 2, 1, 7 |
| 散、花、看不出谁一组 | 3 |
| 居中了仍歪 | 4, 13 |
| 有数字/角标后变丑 | 5 |
| 小了看不清 | 6, 14 |
| 太死、太贴网格 | 7, 13 |
| 想证明苹果用了黄金分割 | 8–11, 然后 16 |
| 边缘发亮/发灰、对比假 | 12, 13 |
| Logo 很匠心，辅助线很多 | 11, 16 |
