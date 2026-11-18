---
name: csl-ace-step-music
description: 用本机 ACE-Step 1.5 生成音乐。先把功能、风格、人声、乐器、时长、格式等可选项一次摆给用户选，选完再调用本地 API 出 MP3。覆盖文生曲、翻唱、局部重绘、音轨提取、叠轨、补全和纯音乐。使用时机：用户要做歌、写曲、配乐、翻唱、改一段音频、提取或补音轨。
---

# ACE-Step 1.5 本机音乐生成

## 边界

- 只调用本机 ACE-Step 1.5，地址 `http://127.0.0.1:8001`。安装目录默认 `~/BDSYNC/self/AI/tools/ACE-Step-1.5`。
- 当前已下载主模型是 `acestep-v15-turbo`。turbo 可用：文生曲、翻唱、局部重绘。音轨提取、叠轨、补全需要 base 模型，未下载时直接说明，不降级冒充。
- 不操作 Gradio 页面。生成走 REST。
- 不改用户给出的歌词。不翻译、不润色、不补句。
- 一次只生成 1 首。用户要多版本时明确说数量，最多 4。
- 生成一次约 1–3 分钟。提交后等待，不重复提交。

## 服务

先查健康：

```bash
curl -sS --max-time 5 http://127.0.0.1:8001/health
```

不通时启动，模型源固定 ModelScope，不走 Hugging Face：

```bash
cd ~/BDSYNC/self/AI/tools/ACE-Step-1.5
DOWNLOAD_SOURCE=modelscope CHECK_UPDATE=false ./start_api_server_macos.sh
```

Apple Silicon 启动脚本强制 MLX。`/health` 返回模型未初始化时再 `POST /v1/init`。启动后轮询 `/health`，最多等 10 分钟。

## 先选择，后生成

任何一次生成前，先用一条消息把下面的选项摆出来，让用户选。用户已经明确说过的项，标成「已定」，不再问。

用户说「你定」「随便」「直接做」时，才对没说的项套用各项里标「推荐」的值，并在回复里逐条写明用了什么。

一次问完，不逐项追问。

### 功能

| 选项 | 要什么 | 模型 |
|---|---|---|
| 文生曲 `text2music`（推荐） | 歌词或主题 | turbo |
| 翻唱 `cover` | 源音频；歌词可空 | turbo |
| 局部重绘 `repaint` | 源音频、起止秒 | turbo |
| 纯音乐 | 无 | turbo |
| 音轨提取 `extract` | 源音频、音轨名 | 仅 base |
| 叠轨 `lego` | 源音频、要加的音轨 | 仅 base |
| 补全 `complete` | 源音频、要补的音轨 | 仅 base |

当前只装了 turbo。用户选后三种时说明需要 base 模型，不降级冒充，不开始生成。

### 风格

可多选。推荐：流行。

- 歌曲：流行、抒情歌、民谣、唱作人、独立、城市流行、K-Pop、J-Pop。
- 乐队：摇滚、朋克、金属、布鲁斯、放克、灵魂乐、迪斯科。
- 节奏：嘻哈、说唱、陷阱、R&B、雷鬼、拉丁、波萨诺瓦。
- 电子：电子、EDM、浩室、techno、合成波、Lo-fi、鼓打贝斯、氛围、新世纪。
- 管弦与地区：爵士、古典、歌剧、管弦、史诗、世界音乐、国风、福音、乡村、华尔兹、进行曲。

用户要列表外的风格时，原样写进 `prompt`。

### 情绪

抒情、励志、欢快、忧伤、忧郁、平静、紧张、暗黑、浪漫、热血、梦幻、怀旧、史诗、温柔、强势、温暖、冷冽、苦甜、俏皮、神秘、庄重、孤独。推荐：抒情。可多选。

### 人声

性别与组合：女声（推荐）、男声、童声、合唱、二重唱、无人声。

唱法：清亮有力（推荐）、温柔、气声、耳语、沙哑、假声、说唱、念白。

音域：女高音、女中音、男高音、男中音、男低音，或不指定（推荐不指定）。

语言：`zh` 普通话（推荐）、`yue` 粤语、`en`、`ja`、`ko`。其余可用值：ar、az、bg、bn、ca、cs、da、de、el、es、fa、fi、fr、he、hi、hr、ht、hu、id、is、it、la、lt、ms、ne、nl、no、pa、pl、pt、ro、ru、sa、sk、sr、sv、sw、ta、te、th、tl、tr、uk、ur、vi、unknown。

### 乐器

可多选，按类别选。推荐：钢琴、木吉他、弦乐。

- 键盘：钢琴、电钢琴、风琴、手风琴、合成器。
- 弹拨：木吉他、电吉他、尤克里里、曼陀林、班卓、古筝、琵琶、古琴。
- 弓弦：弦乐、小提琴、中提琴、大提琴、低音提琴、二胡。
- 管乐：长笛、单簧管、双簧管、萨克斯、小号、长号、圆号、笛子、唢呐、口琴。
- 节奏：鼓、套鼓、贝斯、电贝斯、太鼓、康加、邦戈、木箱鼓、定音鼓。
- 色彩：竖琴、马林巴、钟琴、木琴、西塔琴、塔布拉、卡林巴、乌德。

用户要列表外的乐器时，原样写进 `prompt`。

### 结构与节奏

- 时长：10–600 秒。推荐 120。
- BPM：30–300，或不填交给模型（推荐不填）。
- 拍号：2/4、3/4、4/4（推荐）、6/8，或不填。
- 调式：`C major` 这种写法，70 种组合，或不填（推荐不填）。
- 数量：1–4。推荐 1。

### 输出

格式：mp3（推荐）、flac、wav、wav32、opus、aac。

mp3 码率：128k（推荐）、192k、256k、320k。采样率：44100、48000（推荐）。

### 翻唱与重绘专属

- 翻唱贴源程度 `cover_noise_strength`：0 最贴源，1 偏离最大。推荐 0.3。
- 重绘模式：conservative、balanced（推荐）、aggressive。
- 重绘强度：0 最保源，1 重写最多。推荐 0.5。只在 balanced 生效。

### 音轨名

`vocals`、`backing_vocals`、`drums`、`bass`、`guitar`、`keyboard`、`strings`、`brass`、`woodwinds`、`synth`、`percussion`、`fx`。

提取推荐 `vocals`。叠轨推荐 `strings`。补全推荐 `drums`、`bass`、`guitar`、`strings`。

## 模板

公共请求字段，所有模板都带：

```json
{
  "thinking": true,
  "use_format": false,
  "batch_size": 1,
  "inference_steps": 8,
  "audio_format": "mp3",
  "mp3_bitrate": "128k",
  "mp3_sample_rate": 48000,
  "use_random_seed": true,
  "lm_temperature": 0.85,
  "lm_cfg_scale": 2.0,
  "lm_top_p": 0.9
}
```

`thinking: true` 让 5Hz LM 先写音频语义码，再由 DiT 出声。这是出人声的路径，不要关。

### 1. 文生曲 `text2music`

`prompt` 用英文，按用户选的风格、情绪、人声、乐器拼，不另加用户没选的内容。

```json
{
  "task_type": "text2music",
  "prompt": "<风格>, <情绪>, <人声>, <乐器>",
  "lyrics": "<用户原文，原样>",
  "vocal_language": "zh",
  "audio_duration": 120
}
```

纯音乐：`lyrics` 传空字符串，`vocal_language` 改 `unknown`，`prompt` 用模板 7。

### 2. 翻唱 `cover`

源音频放进请求的 `src_audio_path`。保留旋律和结构，换风格与人声。

```json
{
  "task_type": "cover",
  "src_audio_path": "<源音频绝对路径>",
  "prompt": "<风格>, <情绪>, <人声>, <乐器>",
  "lyrics": "<用户原文；没有就传空字符串>",
  "vocal_language": "zh",
  "audio_cover_strength": 1.0,
  "cover_noise_strength": 0.3
}
```

`cover_noise_strength`：0 最贴源曲，1 偏离最大。默认 0.3。不传 `audio_duration`，跟随源曲。

### 3. 局部重绘 `repaint`

只重生成一段，其余保持。`repainting_start`、`repainting_end` 单位秒，用户必须给区间。

```json
{
  "task_type": "repaint",
  "src_audio_path": "<源音频绝对路径>",
  "repainting_start": 30,
  "repainting_end": 60,
  "repaint_mode": "balanced",
  "repaint_strength": 0.5,
  "prompt": "<风格>, <情绪>, <人声>, <乐器>, same mood as the source",
  "lyrics": "<该区间对应的歌词原文；没有就传空字符串>",
  "vocal_language": "zh"
}
```

`repaint_strength` 只在 `balanced` 生效：0 最保源，1 重写最多。

### 4. 音轨提取 `extract`

需要 base 模型。`track_name` 取其一：`vocals`、`backing_vocals`、`drums`、`bass`、`guitar`、`keyboard`、`strings`、`brass`、`woodwinds`、`synth`、`percussion`、`fx`。

```json
{
  "task_type": "extract",
  "src_audio_path": "<源音频绝对路径>",
  "track_name": "vocals"
}
```

### 5. 叠轨 `lego`

需要 base 模型。在已有歌曲上加一条音轨。

```json
{
  "task_type": "lego",
  "src_audio_path": "<已有歌曲绝对路径>",
  "track_name": "strings",
  "prompt": "<要加的音轨>, <风格>, supportive, not overpowering"
}
```

### 6. 补全 `complete`

需要 base 模型。`track_classes` 是要补上的音轨列表。

```json
{
  "task_type": "complete",
  "src_audio_path": "<不完整音频绝对路径>",
  "track_classes": ["drums", "bass", "guitar", "strings"],
  "prompt": "<风格>, <情绪>, <乐器>",
}
```

### 7. 纯音乐

文生曲的无人声形式。

```json
{
  "task_type": "text2music",
  "prompt": "instrumental, no vocals, <风格>, <情绪>, <乐器>",
  "lyrics": "",
  "vocal_language": "unknown",
  "audio_duration": 120
}
```

## 生成

`POST /release_task`，`Content-Type: application/json`，body 是公共字段加模板字段。

返回 `data.task_id`。接口是同步生成后再返回，一次调用会阻塞到完成。超时设 15 分钟。

然后 `POST /query_result`，body `{"task_id": "<id>"}`。从 `data` 里取每首的 `file`。

## 校验

对每个 `file`：

```bash
ffprobe -v error -show_entries format=duration,format_name -of json "<file>"
ffmpeg -v error -i "<file>" -f null -
```

通过标准：`format_name` 含 `mp3`，`ffmpeg` 无错误。设了 `audio_duration` 时，时长与目标相差不超过 1 秒。

不通过就报告文件路径和具体偏差，不静默重跑。

## 回复

给文件绝对路径、功能名、时长、格式。说明未人工试听。用户没给歌词时，回复里附上实际使用的 `prompt`。
