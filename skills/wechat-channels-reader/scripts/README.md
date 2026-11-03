# wechat-channels-reader 脚本

完整说明与边界见 [SKILL.md](../SKILL.md)。将 `SKILL_DIR` 设为解压后含 SKILL.md 的目录。

```bash
bash "$SKILL_DIR/scripts/setup.sh" --model none
PY="${WCR_VENV:-${XDG_CACHE_HOME:-$HOME/.cache}/wechat-channels-reader/venv}/bin/python"
"$PY" "$SKILL_DIR/scripts/sph_fetch.py" --download-model small --model-source modelscope --model-timeout 300
"$PY" "$SKILL_DIR/scripts/sph_fetch.py" '<链接>' --backend ffmpegtool --allow-third-party --no-asr
# 新增备用站点需单独允许：
"$PY" "$SKILL_DIR/scripts/sph_fetch.py" '<链接>' --backend auto --allow-third-party --allow-paste2vid --resolve-timeout 180
# 已有 Whisper 目录：加 --model-dir PATH；FunASR：先 setup.sh --with-funasr，再加 --asr funasr。
```

venv/模型放用户缓存，元宝 Cookie 放用户私有配置目录，运行输出每次使用独立目录。没有启用元宝路线时不读取凭据。模型、接口和转写质量需要真实环境另测；离线回归不代表线上全链路通过。

新增解析器的离线浏览器夹具可用 `WCR_BROWSER_FIXTURES=1` 启用；全部页面请求在本地截获。真实站点的可用性和额度需另测。
