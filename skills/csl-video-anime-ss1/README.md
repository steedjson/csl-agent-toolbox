# csl-video-anime-ss1 · 简体中文动漫分镜技能

基于 `csl-video-ss1` v3.2 的独立派生技能。面向 15–60 秒、最多 6 段、单主角的动漫短视频，产出文本企划与提示词，默认 2D 赛璐璐。技能正文与默认产出全部使用简体中文。

输入示例：

> 做一支动漫短片：年轻信使在站台收到会发光的信；3 段 × 5 秒；9:16；方式 2；2D 赛璐璐；语音：无语音，不要旁白。

输出包括脚本、正背侧角色设定图提示词、角色与画风双锚点、分镜、剧名、封面封底、BGM、投喂指引和逐项自检。每份提示词独立包含双锚点，并约束动作起止、朝向、持物手和道具来源；提供直出、首帧和首尾帧三种流程。

缺少参数一次问齐。画风省略时默认 2D 赛璐璐；说“随你”可采用完整默认参数。无旁白、无语音和纯环境音分别处理。

完整期望产出见 [examples/regression.md](examples/regression.md)，共 11 份独立提示词：3 份角色设定图、6 份分镜、2 份包装。

实际出片默认保存到 `~/Downloads/csl-video-projects/<项目名>/`，固定四个目录：`frames/` 放设定图、首尾帧和输入图；`qa/` 放抽帧、探针、清单及验证报告；`script/` 放脚本和提示词；`video/` 放分段、重试、成片及音轨。每支影片独立归档，产物不散放项目根目录。

## 安装与边界

仓库维护源文件，安装时明确选择宿主，在仓库根目录执行，例如：

```bash
python3 scripts/install_skills.py link --skill csl-video-anime-ss1 --host claude
```

上面是按需安装命令，本次创建不执行宿主安装。无运行时技能依赖，无新增第三方代码或外部来源；来源为本仓库自有 `csl-video-ss1`。不继承原技能的生成器实测结论或冷跑证据。

默认生成文本；实际出图、出片需要用户提出执行需求及可用生成器。生成器只支持首帧时明确降级，不能把尾帧参考描述成实际双帧输入。锚点减少漂移，不承诺生成结果必然一致。

## 验证与证据

结构校验（仓库根目录）：

```bash
python3 skills/dao-skill/scripts/quality_check.py skills/csl-video-anime-ss1
python3 scripts/validate_repo.py
jq empty skills.json
git diff --check
```

示例逐份锚点核验，不依赖原技能的聚合计数脚本：

```bash
python3 - <<'PY'
from pathlib import Path
import re
p = Path('skills/csl-video-anime-ss1/examples/regression.md')
t = p.read_text(encoding='utf-8')
anchors = re.findall(r'^> (.+)$', t, re.M)
prompts = re.findall(r'```text\n(.*?)\n```', t, re.S)
assert len(anchors) == 2 and len(prompts) == 11
for i, prompt in enumerate(prompts, 1):
    assert all(prompt.count(anchor) == 1 for anchor in anchors), f'prompt {i}'
assert 'BGM 总时长：15 秒' in t
print('PASS: 11 份提示词逐份包含完整双锚点；BGM 声明为 15 秒')
PY
```

结构与作者示例文本已核验；另完成一次真实 15 秒动漫出片及 15 帧视觉抽样，主动作成立，胸章细节、严格硬边阴影与固定机位仅部分通过。音轨存在但未听觉审听。首次 grok-4.7 冷跑机械检查通过、眼部高光语义冲突漏检；v1.1 增加约束相容性后，两组全新上下文复测的原高光回归与白手套/色板目标冲突均通过，11 份双锚点和原有结构保持完整。迁移组发现的高光/辉光范围歧义已在 v1.2 中按镜面、光源辉光和表面受光分别定义；两组 gpt-6.1-sol 独立文本冷跑目标检查通过。原失败模型 grok-4.7 的 C4 补测发现跨段信封位置不接续；后续修订增加分镜原文对照及冻结画风块关光条款，C6 的关光落点、11 份副本和接续目标均通过。随后 C7 四场短约束冷跑通过，区分画外光源继续照明、单面全遮挡、部分遮挡与关灯；仅覆盖预定直达光路文本场景。P2 已完成四场真实视频与两次重试：A 画外照明目标抽样通过，B 全挡和 C 半挡失败，D 关灯部分通过；提供精确 20 秒静音对照合集，原生音频未听审，生成器及全文语义可靠性未全面通过。原始产出、调用记录和检查边界见 [EVIDENCE.md](EVIDENCE.md)，不能以出片成功或机械检查通过代替全部质量通过。

v1.2（2026-11-16）：在 v1.1 双锚点相容性基础上明确镜面高光、光源辉光和表面受光的范围，自检给出光源与现象分类证据；禁止靠更名绕过用户限制。独立复测记录于证据台账。修订前文本快照保存在出片项目 `qa/lighting-clarity-before.md`，可回滚本修订；撤回整个技能时仅撤回本目录及 `skills.json`、根 README 对应条目，原技能不受影响。
