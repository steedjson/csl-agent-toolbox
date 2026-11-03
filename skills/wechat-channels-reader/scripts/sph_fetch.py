#!/usr/bin/env python3
"""微信视频号分享链接 -> 元数据 + 封面 + MP4 + 转写 + summary_input.md

用法:
  sph_fetch.py <分享链接或整段分享文案> [--out DIR] [--model small|medium] [--no-asr]
               [--backend auto|ffmpegtool|yuanbao] [--frames N] [--cookie FILE]
               [--asr whisper|funasr] [--model-dir PATH] [--model-source auto|hf|hf-mirror|modelscope]
  sph_fetch.py --download-model small [--model-source modelscope]    # 只预下载 Whisper 模型
  sph_fetch.py --download-model funasr                               # 只预下载 FunASR 中文模型

主路线: 公开 preview 接口(元数据) + ffmpegtool.com(无界面浏览器取直链)
备用:   腾讯元宝解析接口(需要元宝登录 Cookie)，参考 QinGeneral/wx-downloader 实现
"""
from __future__ import annotations

import argparse, contextlib, json, os, re, secrets, shutil, subprocess, sys, tempfile, time, wave
import fcntl
import hashlib, urllib.request, urllib.error
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")  # Xet 在国内网络常卡住，统一禁用
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlencode, urlsplit, parse_qs, quote
from html.parser import HTMLParser

TOOL_DIR = Path(__file__).resolve().parent
DEFAULT_COOKIE = Path(os.environ.get("XDG_CONFIG_HOME", "~/.config")).expanduser() / "wechat-channels-reader/yuanbao_cookie.json"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")
PREVIEW = "https://channels.weixin.qq.com/finder-preview"
YB = "https://yuanbao.tencent.com"
FFTOOL = "https://ffmpegtool.com/parse/wechat-channels"
CST = timezone(timedelta(hours=8))
MODELS_DIR = Path(os.environ.get("WCR_MODELS_DIR") or Path(os.environ.get("XDG_CACHE_HOME", "~/.cache")).expanduser() / "wechat-channels-reader/models").expanduser()
DEFAULT_OUT_ROOT = Path(os.environ.get("WCR_OUT") or Path.cwd() / "wechat-channels").expanduser()

# Expected faster-whisper CTranslate2 files supplied with this package. Every source must match these hashes.
WHISPER_REPOS = {"modelscope": ["Systran/faster-whisper-{}", "gpustack/faster-whisper-{}", "pengzhendong/faster-whisper-{}"],
                 "hf": ["Systran/faster-whisper-{}"]}
WHISPER_FILES = {
    "tiny": {"config.json": (2249, "a73a28cdfe1c43ccc7202fa333d1f89c202477271407ae9a7f19afa52039cac8"), "model.bin": (75538270, "dcb76c6586fc06cbdac6dd21f14cfd129cc4cdd9dce19bf4ffa62e59cbe6e6d1"), "tokenizer.json": (2203239, "fb7b63191e9bb045082c79fd742a3106a12c99513ab30df4a0d47fa6cb6fd0ab"), "vocabulary.txt": (459861, "34ce3fe1c5041027b3f8d42912270993f986dbc4bb34cf27f951e34a1e453913")},
    "base": {"config.json": (2309, "56a6d8110d311f19c8f0471e562832c7527f146b567275bfca59fcf7c184da9a"), "model.bin": (145217532, "d01c3014881c9c6f3133c182f3d2887eb6ca1c789a7538c5c007196857a0a6a9"), "tokenizer.json": (2203239, "fb7b63191e9bb045082c79fd742a3106a12c99513ab30df4a0d47fa6cb6fd0ab"), "vocabulary.txt": (459861, "34ce3fe1c5041027b3f8d42912270993f986dbc4bb34cf27f951e34a1e453913")},
    "small": {"config.json": (2370, "b55496ac7940a7ae47d2c01eab40edfd8701feec1229d9cce3b40014383fb828"), "model.bin": (483546902, "3e305921506d8872816023e4c273e75d2419fb89b24da97b4fe7bce14170d671"), "tokenizer.json": (2203239, "fb7b63191e9bb045082c79fd742a3106a12c99513ab30df4a0d47fa6cb6fd0ab"), "vocabulary.txt": (459861, "34ce3fe1c5041027b3f8d42912270993f986dbc4bb34cf27f951e34a1e453913")},
    "medium": {"config.json": (2257, "3622a2ddc41ec0e0fd4e68c13c6830f03b90c38d89aaad184de02c8c642cf807"), "model.bin": (1527906378, "9b45e1009dcc4ab601eff815b61d80e60ce3fd8c74c1a14f4a282258286b51ae"), "tokenizer.json": (2203239, "fb7b63191e9bb045082c79fd742a3106a12c99513ab30df4a0d47fa6cb6fd0ab"), "vocabulary.txt": (459861, "34ce3fe1c5041027b3f8d42912270993f986dbc4bb34cf27f951e34a1e453913")},
}
# FunASR 中文模型（ModelScope，阿里达摩院 iic 官方仓库）
FUNASR_REPOS = {
    "asr": "iic/speech_seaco_paraformer_large_asr_nat-zh-cn-16k-common-vocab8404-pytorch",
    "vad": "iic/speech_fsmn_vad_zh-cn-16k-common-pytorch",
    "punc": "iic/punc_ct-transformer_zh-cn-common-vocab272727-pytorch",
}


class Fail(Exception):
    pass


def log(*a):
    print("[sph]", *a, file=sys.stderr, flush=True)


# ---------------- 输入解析 ----------------
def extract_link(text: str) -> dict:
    for raw in re.findall(r"https?://[^\s\"'<>]+", text):
        url = raw.rstrip("，。；！？）】)]}")
        p = urlsplit(url)
        if p.hostname not in ("weixin.qq.com", "channels.weixin.qq.com"):
            continue
        if p.scheme != "https" or p.username or p.password or p.port not in (None, 443):
            raise Fail("视频号链接必须使用 HTTPS，且不得包含用户名、密码或其他端口")
        if p.hostname == "weixin.qq.com":
            m = re.fullmatch(r"/sph/([A-Za-z0-9_-]{1,128})/?", p.path)
            if not m:
                raise Fail("无效的视频号短链接")
            return {"url": f"https://weixin.qq.com/sph/{m[1]}", "code": m[1], "kind": "sph"}
        q = parse_qs(p.query, keep_blank_values=True)
        if "id" in q:
            if len(q["id"]) != 1 or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", q["id"][0]):
                raise Fail("无效的视频号 id")
            sid = q["id"][0]
            return {"url": f"https://weixin.qq.com/sph/{sid}", "code": sid, "kind": "sph"}
        code = "feed-" + hashlib.sha256(url.encode()).hexdigest()[:16]
        return {"url": url, "code": code, "kind": "channels", "eid": (q.get("eid") or [None])[0]}
    raise Fail("没有在输入中找到视频号链接（需要 weixin.qq.com/sph/xxx 或 channels.weixin.qq.com/...）")


def checked_https(url):
    p = urlsplit(url)
    if any(ord(c) <= 32 or ord(c) == 127 for c in url) or p.scheme != "https" or not p.hostname or p.username or p.password or p.port not in (None, 443):
        raise Fail("远端地址必须是无凭据的 HTTPS URL")
    return url

class SafeRedirect(urllib.request.HTTPRedirectHandler):
    max_redirections = 5

    def __init__(self, allowed_hosts=None):
        self.allowed_hosts = None if allowed_hosts is None else frozenset(allowed_hosts)

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        checked_https(newurl)
        if self.allowed_hosts is not None and urlsplit(newurl).hostname not in self.allowed_hosts:
            raise Fail("拒绝将视频下载重定向到未允许的主机")
        sensitive = any(k.lower() in ("cookie", "authorization") for k, _ in req.header_items())
        if sensitive and urlsplit(req.full_url).netloc != urlsplit(newurl).netloc:
            raise Fail("拒绝将登录凭据转发到其他主机")
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def open_response(request, timeout, allowed_hosts=None):
    checked_https(request.full_url)
    if allowed_hosts is not None and urlsplit(request.full_url).hostname not in allowed_hosts:
        raise Fail("视频下载地址不属于允许的主机")
    return urllib.request.build_opener(SafeRedirect(allowed_hosts)).open(request, timeout=timeout)

def response_chunks(response, limit, deadline):
    size = 0
    length = response.headers.get("Content-Length")
    if length and int(length) > limit:
        raise Fail("响应超过大小上限")
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise Fail("请求超过总时限")
        sock = getattr(getattr(getattr(response, "fp", None), "raw", None), "_sock", None)
        if sock is not None:
            sock.settimeout(min(10, remaining))
        # read1 returns available data so the deadline is checked between reads.
        chunk = response.read1(1 << 16)
        if time.monotonic() > deadline:
            raise Fail("请求超过总时限")
        if not chunk:
            return
        size += len(chunk)
        if size > limit:
            raise Fail("响应超过大小上限")
        yield chunk

def save_auth(path, data):
    """Write credentials with restrictive permissions before exposing the file."""
    path = Path(path).expanduser()
    if path.is_symlink():
        raise Fail("凭据文件不能是符号链接")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(prefix=".yuanbao-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)

def make_output(root, code):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", code):
        raise Fail("无效的输出标识")
    root = Path(root).expanduser().resolve()
    parent = (root / code).resolve()
    if not parent.is_relative_to(root):
        raise Fail("输出路径超出指定目录")
    parent.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=datetime.now(CST).strftime("%Y%m%d-%H%M%S-"), dir=parent))

# ---------------- HTTP ----------------
def http(url, data=None, headers=None, timeout=30):
    h = {"User-Agent": UA}
    h.update(headers or {})
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        h.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=body, headers=h, method="POST" if body else "GET")
    deadline = time.monotonic() + timeout
    with open_response(req, min(10, timeout)) as r:
        return r.status, dict(r.headers), b"".join(response_chunks(r, 2 << 20, deadline))


def post_json(url, data, headers=None, timeout=30):
    status, _, raw = http(url, data, headers, timeout=timeout)
    try:
        value = json.loads(raw)
    except ValueError:
        raise Fail(f"接口返回非 JSON（HTTP {status}）")
    if not isinstance(value, dict):
        raise Fail("接口返回非对象 JSON")
    return value


def feed_info(body, referer, timeout=30):
    params = {"_rid": f"{int(time.time()):x}-{secrets.token_hex(4)}", "_pageUrl": PREVIEW + "/pages/sph"}
    return post_json(PREVIEW + "/api/feed/get_feed_info?" + urlencode(params), body,
                     {"Origin": "https://channels.weixin.qq.com", "Referer": referer}, timeout=timeout)


def download(url: str, dest: Path, expect_mp4=False, referer=None, max_bytes=512 << 20, timeout=300, allowed_hosts=None):
    tmp = dest.with_suffix(dest.suffix + ".part")
    h = {"User-Agent": UA, "Accept-Encoding": "identity"}
    if referer:
        h["Referer"] = referer
    req = urllib.request.Request(url, headers=h)
    deadline = time.monotonic() + timeout
    try:
        kwargs = {} if allowed_hosts is None else {"allowed_hosts": allowed_hosts}
        with open_response(req, min(10, timeout), **kwargs) as r, open(tmp, "xb") as f:
            ctype = r.headers.get("Content-Type", "").lower()
            if expect_mp4 and any(k in ctype for k in ("text/", "json", "xml")):
                raise Fail(f"直链返回的不是视频（content-type={ctype}），可能已过期")
            for chunk in response_chunks(r, max_bytes, deadline):
                f.write(chunk)
        if tmp.stat().st_size == 0:
            raise Fail("下载为空文件")
        if expect_mp4:
            with tmp.open("rb") as f:
                head = f.read(12)
            if head[4:8] not in (b"ftyp", b"moov", b"mdat", b"free", b"wide"):
                raise Fail("下载内容不是 MP4（可能是加密流或错误页）")
        tmp.replace(dest)
    finally:
        tmp.unlink(missing_ok=True)


# ---------------- 元数据（公开接口，免登录） ----------------
def public_metadata(link: dict) -> dict:
    if link["kind"] == "sph":
        body = {"baseReq": {"generalToken": ""}, "shortUri": link["code"]}
        ref = f"{PREVIEW}/pages/sph?id={link['code']}"
    elif link.get("eid"):
        body = {"baseReq": {"generalToken": ""}, "exportId": link["eid"]}
        ref = link["url"]
    else:
        return {}
    try:
        d = feed_info(body, ref)
    except Exception as e:
        log("公开 preview 接口失败:", e)
        return {"_error": str(e)}
    data = d.get("data") or {}
    err = data.get("errMsg") or {}
    if d.get("errCode") or any(err.get(k) for k in ("type", "title", "content")) or not data.get("feedInfo"):
        log("公开 preview 接口未给出元数据:", json.dumps(err or d, ensure_ascii=False)[:200])
        return {"_error": err or d}
    return normalize_meta(data)


def normalize_meta(data: dict) -> dict:
    fi = data.get("feedInfo") or {}
    au = data.get("authorInfo") or {}
    sc = data.get("sceneInfo") or {}
    ct = fi.get("createtime")
    return {
        "author": au.get("nickname"),
        "author_avatar": au.get("headImgUrl"),
        "description": fi.get("description"),
        "createtime": ct,
        "createtime_cst": datetime.fromtimestamp(ct, CST).strftime("%Y-%m-%d %H:%M:%S UTC+8") if ct else None,
        "likes": fi.get("likeCountFmt"), "forwards": fi.get("forwardCountFmt"),
        "comments": fi.get("commentCountFmt"), "favs": fi.get("favCountFmt"),
        "cover_url": fi.get("coverUrl"),
        "export_id": sc.get("dynamicExportId"),
        "media_type": fi.get("mediaType"),
    }


# ---------------- 主路线：ffmpegtool.com ----------------
def chrome_path():
    env = os.environ.get("WCR_CHROME")
    if env and Path(env).is_file() and os.access(env, os.X_OK):
        return env
    for c in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        p = shutil.which(c)
        if p:
            return p
    for p in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              "/Applications/Chromium.app/Contents/MacOS/Chromium",
              str(Path.home() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome")):
        if Path(p).is_file() and os.access(p, os.X_OK):
            return p
    return None  # 用 playwright 自带 chromium


_FFT_DIALOG_JS = "() => {\n  // ffmpegtool 把结果弹窗常驻在 DOM 里（aria-hidden + opacity-0），只认真正打开的那一个\n  const shown = el => { for (let p = el; p; p = p.parentElement) {\n      if (p.getAttribute && p.getAttribute('aria-hidden') === 'true') return false;\n      const cs = getComputedStyle(p);\n      if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) < 0.5) return false; }\n    return true; };\n  for (const d of document.querySelectorAll('[role=alertdialog],[role=dialog]')) {\n    const h = d.querySelector('h1,h2,h3,[id]');\n    const title = (d.querySelector('h3') || h || {}).innerText || '';\n    if (!/^(解析失败|需要刷新页面|Parse failed|Page refresh needed)$/.test(title.trim())) continue;  // 跳过反馈框、帮助框\n    if (!shown(d)) continue;\n    const id = d.getAttribute('aria-describedby');\n    const msg = ((id && document.getElementById(id)) || {}).innerText || '';\n    return (title.trim() + (msg.trim() ? '：' + msg.trim() : '')).slice(0, 300);\n  }\n  for (const t of document.querySelectorAll('[role=alert],[role=status],[class*=toast]')) {\n    const s = (t.innerText || '').trim();\n    if (s && shown(t) && /失败|错误|稍后|盹|翻车|频繁/.test(s)) return s.slice(0, 200);\n  }\n  return '';\n}"

class ResolverBlocked(Fail):
    """This backend requires user action or has exhausted its quota; do not retry it."""


def _resolve_left(deadline, cap=None):
    left = deadline - time.monotonic()
    if left <= 0:
        raise Fail("视频解析超过总时限")
    return min(left, cap) if cap is not None else left


def _resolve_ms(deadline, cap=30):
    return max(1, int(_resolve_left(deadline, cap) * 1000))


def _blocked_message(message):
    return bool(re.search(r"额度|次数|登录|会员|验证码|人机|频繁|\b(?:quota|captcha|login|premium|pro)\b|\brate[ -]?limit|\bsign[ -]?in\b", str(message), re.I))


def _fft_backoff():
    raw = os.environ.get("WCR_FFT_BACKOFF", "5,15")
    try:
        parts = [float(x.strip()) for x in raw.split(",")] if raw.strip() else []
    except ValueError:
        raise Fail("WCR_FFT_BACKOFF 必须是逗号分隔的 0–30 秒退避值")
    if len(parts) > 3 or any(not 0 <= x <= 30 for x in parts):
        raise Fail("WCR_FFT_BACKOFF 最多 3 个值，每个 0–30 秒")
    return parts


def _fft_api_error(responses):
    for response in reversed(responses):
        data = response.get("json")
        data = data if isinstance(data, dict) else {}
        code = data.get("code")
        status = response.get("status", 200)
        if status >= 400 or code not in (0, "0", None):
            fields = [re.sub(r"\s+", " ", str(data[k]))[:160]
                      for k in ("message", "msg", "errorCode", "detail")
                      if isinstance(data.get(k), (str, int, float)) and data[k] != ""]
            code_text = str(code)[:80] if isinstance(code, (str, int, float)) or code is None else "invalid"
            fields.append(f"code={code_text} HTTP {status}")
            # Never persist gate tokens, full request query strings or backend trace objects.
            return "；".join(fields)[:600]
    return ""


def _fft_dialog_error(page):
    try:
        return re.sub(r"\s+", " ", page.evaluate(_FFT_DIALOG_JS) or "").strip()
    except Exception:
        return ""


_FFT_SHOWN_JS = r"""el => {
  for (let p=el;p;p=p.parentElement) {
    if (p.getAttribute('aria-hidden')==='true') return false;
    const s=getComputedStyle(p);
    if (s.display==='none'||s.visibility==='hidden'||parseFloat(s.opacity)<0.5) return false;
  }
  const r=el.getBoundingClientRect();return r.width>0&&r.height>0;
}"""


def _fft_once(playwright, text, timeout_s):
    from playwright.sync_api import TimeoutError as PWTimeout
    deadline = time.monotonic() + timeout_s
    executable = chrome_path()
    browser = playwright.chromium.launch(headless=True, timeout=_resolve_ms(deadline),
                                         **({"executable_path": executable} if executable else {}))
    responses, submitted = [], []

    def parse_request(request):
        url = urlsplit(request.url)
        return url.scheme == "https" and url.hostname == "ffmpegtool.com" and url.path.startswith("/api/parse")

    def on_request(request):
        if parse_request(request) and request.method == "POST" and not urlsplit(request.url).path.endswith("/gate"):
            submitted.append(True)

    def on_finished(request):
        if not parse_request(request):
            return
        response = request.response()
        if response is None:
            return
        try:
            raw = response.body()  # requestfinished means the body has already finished downloading.
            data = json.loads(raw) if len(raw) <= 2 << 20 else None
        except Exception:
            data = None
        responses.append({"status": response.status, "json": data})

    try:
        context = browser.new_context(permissions=["clipboard-read", "clipboard-write"], locale="zh-CN")
        page = context.new_page()
        page.set_default_timeout(_resolve_ms(deadline, 3))
        page.on("request", on_request)
        page.on("requestfinished", on_finished)
        page.goto(FFTOOL, timeout=_resolve_ms(deadline, 60), wait_until="load")
        input_box = page.locator("input[type=text], input:not([type]), textarea").first
        input_box.wait_for(timeout=_resolve_ms(deadline, 30))
        copies = page.get_by_text("复制链接", exact=True)

        def submit():
            input_box.fill(text, timeout=_resolve_ms(deadline, 3))
            button = page.get_by_text("开始解析", exact=True)
            if button.count() and button.first.is_visible():
                button.first.click(timeout=_resolve_ms(deadline, 3))
            else:
                input_box.press("Enter", timeout=_resolve_ms(deadline, 3))

        submit()
        resubmitted = False
        retry_at = time.monotonic() + min(5, _resolve_left(deadline) / 2)
        visible_copies = []
        while _resolve_left(deadline) > 0:
            for i in range(copies.count()):
                item = copies.nth(i)
                if item.evaluate(_FFT_SHOWN_JS):
                    visible_copies.append(item)
            if visible_copies:
                break
            api_error = _fft_api_error(responses)
            ui_error = _fft_dialog_error(page)
            if api_error or ui_error:
                error = api_error or ui_error
                if _blocked_message(error) or any(r["status"] in (401, 403, 429) for r in responses):
                    raise ResolverBlocked("ffmpegtool 请求受限：" + error)
                raise Fail("ffmpegtool 解析失败：" + error)
            if not submitted and not resubmitted and time.monotonic() >= retry_at:
                submit()
                resubmitted = True
            page.wait_for_timeout(min(250, _resolve_ms(deadline, 0.25)))
        found = {}
        for item in visible_copies:
            label = item.evaluate("e=>{let p=e;for(let i=0;i<6&&p.parentElement;i++){p=p.parentElement;if(/H\\.26[45]|无水印/.test(p.innerText))break;}return p.innerText}")
            kind = "h264" if "H.264" in label else "h265" if "H.265" in label else "video" if "视频" in label else None
            if not kind or kind in found:
                continue
            page.evaluate("navigator.clipboard.writeText('')")
            item.click(timeout=_resolve_ms(deadline, 3))
            page.wait_for_timeout(min(400, _resolve_ms(deadline, 0.4)))
            url = page.evaluate("navigator.clipboard.readText()").strip()
            try:
                checked_https(url)
            except (Fail, ValueError):
                continue
            found[kind] = url
        if not found:
            raise Fail("ffmpegtool 没有可用的 HTTPS 视频直链")
        return found
    finally:
        browser.close()


def ffmpegtool_resolve(text, timeout_s=60):
    waits = [0] + _fft_backoff()
    deadline = time.monotonic() + timeout_s
    from playwright.sync_api import sync_playwright
    errors = []
    with sync_playwright() as playwright:
        for attempt, wait in enumerate(waits):
            if wait:
                if wait >= _resolve_left(deadline):
                    raise Fail("视频解析预算不足以继续退避重试")
                time.sleep(wait)
            try:
                return _fft_once(playwright, text, _resolve_left(deadline))
            except ResolverBlocked:
                raise
            except Exception as error:
                errors.append(re.sub(r"\s+", " ", str(error))[:400])
                log(f"ffmpegtool 尝试 {attempt+1}/{len(waits)}:", errors[-1])
    raise Fail(f"ffmpegtool {len(waits)} 次尝试未成功；{errors[-1]}")


P2V = "https://paste2vid.com"
P2V_MEDIA_HOSTS = frozenset({"finder.video.qq.com"})


def _p2v_media_url(value):
    if not isinstance(value, str):
        return None
    try:
        checked_https(value)
        if urlsplit(value).hostname in P2V_MEDIA_HOSTS:
            return value
    except (Fail, ValueError):
        pass
    return None


class _PasteHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.urls, self.metadata = {}, {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("data-parse-meta"):
            try:
                data = json.loads(attrs["data-parse-meta"])
            except ValueError:
                data = {}
            if isinstance(data, dict):
                title = data.get("title")
                if isinstance(title, str):
                    self.metadata["description"] = title
                cover = data.get("cover")
                if isinstance(cover, str):
                    try:
                        checked_https(cover)
                        host = urlsplit(cover).hostname
                        if any(host == base or host.endswith("." + base) for base in ("qpic.cn", "qlogo.cn", "qq.com")):
                            self.metadata["cover_url"] = cover
                    except (Fail, ValueError):
                        pass
                formats = data.get("formats")
                for item in formats if isinstance(formats, list) else []:
                    if not isinstance(item, dict):
                        continue
                    url = _p2v_media_url(item.get("download_url") or item.get("url"))
                    name = str(item.get("id") or "").lower()
                    kind = "h264" if "264" in name else "h265" if "265" in name else "video"
                    if url:
                        self.urls.setdefault(kind, url)
        url = _p2v_media_url(attrs.get("data-download-url"))
        if url:
            self.urls.setdefault("video", url)


def paste2vid_resolve(url, tries=2, timeout_s=90):
    if not isinstance(tries, int) or not 1 <= tries <= 3:
        raise Fail("paste2vid 尝试次数必须为 1–3")
    deadline = time.monotonic() + timeout_s
    last = "未取得视频直链"
    for attempt in range(tries):
        if attempt:
            if _resolve_left(deadline) <= 2:
                break
            time.sleep(2)
        status = 200
        try:
            status, _, raw = http(P2V + "/api/parse2?p=channels&lang=zh", {"url": url},
                                 {"Origin": P2V, "Referer": P2V + "/channels", "Accept": "application/json"},
                                 timeout=_resolve_left(deadline, 30))
        except urllib.error.HTTPError as error:
            status = error.code
            try:
                raw = b"".join(response_chunks(error, 65536, deadline))
            except (Fail, OSError):
                raw = b"{}"
            finally:
                error.close()
        except (OSError, Fail) as error:
            last = type(error).__name__
            continue
        try:
            data = json.loads(raw)
        except ValueError:
            data = {}
        if not isinstance(data, dict):
            data = {}
        if status >= 400 or data.get("code") not in (0, "0"):
            message = data.get("message") or data.get("msg") or f"HTTP {status} 或无效响应"
            message = re.sub(r"\s+", " ", str(message))[:300]
            if status in (401, 403, 429) or _blocked_message(message):
                raise ResolverBlocked("paste2vid 请求受限：" + message)
            last = message
            continue
        content = data.get("data")
        html = content.get("html") if isinstance(content, dict) else None
        if not isinstance(html, str):
            last = "返回结果缺少 HTML"
            continue
        parsed = _PasteHTML()
        parsed.feed(html)
        if parsed.urls:
            return parsed.urls, parsed.metadata
        last = "返回结果中没有有效的 HTTPS finder.video.qq.com 直链"
    raise Fail("paste2vid 解析失败：" + last)



# ---------------- 备用：腾讯元宝 ----------------
def load_yuanbao_auth(cookie_file: Path | None) -> dict:
    """支持: 1) 纯 Cookie 串  2) 浏览器 DevTools 'Copy as cURL' 整段  3) JSON {cookie, headers}
       4) wx-downloader 的 ~/.config/wx-channels/auth.json"""
    cands = [cookie_file] if cookie_file else [DEFAULT_COOKIE]
    for f in cands:
        if not f or not f.exists() or not f.read_text(encoding="utf-8-sig").strip():
            continue
        raw = f.read_text(encoding="utf-8-sig").strip()
        auth = {"cookie": "", "headers": {}, "source": str(f)}
        if raw.startswith("{"):
            j = json.loads(raw)
            if isinstance(j.get("cookies"), list):
                def usable(cookie):
                    if not isinstance(cookie, dict):
                        return False
                    domain = str(cookie.get("domain") or "").lstrip(".").lower()
                    try:
                        expires = cookie.get("expires", -1)
                        expires = -1 if expires is None else float(expires)
                    except (TypeError, ValueError):
                        return False
                    return (domain in ("yuanbao.tencent.com", "tencent.com")
                            and isinstance(cookie.get("name"), str) and isinstance(cookie.get("value"), str)
                            and bool(cookie["value"]) and (expires == -1 or expires > time.time()))
                auth["cookie"] = "; ".join(f"{c['name']}={c['value']}" for c in j["cookies"] if usable(c))
            else:
                auth["cookie"] = j.get("cookie", "")
            auth["headers"] = j.get("headers", {}) or {}
            auth["user_agent"] = j.get("user_agent")
        elif raw.startswith("curl "):
            for k, v in re.findall(r"-H\s+[$]?'([^:']+):\s*([^']*)'", raw):
                if k.lower() == "cookie":
                    auth["cookie"] = v
                else:
                    auth["headers"][k.lower()] = v
            m = re.search(r"(?:-b|--cookie)\s+[$]?'([^']*)'", raw)
            if m:
                auth["cookie"] = m.group(1)
        else:
            auth["cookie"] = re.sub(r"^cookie:\s*", "", raw, flags=re.I).replace("\n", "").strip()
        if not isinstance(auth["cookie"], str):
            raise Fail("凭据 Cookie 必须是字符串")
        names = {p.split("=", 1)[0].strip() for p in auth["cookie"].split(";")}
        if not {"hy_user", "hy_token"} <= names:
            raise Fail(f"{f} 中的 Cookie 缺少 hy_user / hy_token（未登录状态的 Cookie 无效），请重新扫码登录元宝后再复制")
        values = [auth["cookie"], auth.get("user_agent") or UA]
        if not isinstance(auth["headers"], dict):
            raise Fail("凭据 headers 必须是对象")
        keep = {"authorization", "t-userid", "x-id", "x-device-id", "x-hy92", "x-hy93"}
        auth["headers"] = {str(k).lower(): v for k, v in auth["headers"].items() if str(k).lower() in keep}
        values.extend(auth["headers"].values())
        if any(not isinstance(v, str) or any(ord(c) < 32 or ord(c) > 126 for c in v) for v in values):
            raise Fail("凭据请求头包含不支持的字符；请重新导出，不要在聊天中粘贴凭据")
        return auth
    raise Fail("元宝备用路线需要登录凭据，但未找到："
               f"{cookie_file or DEFAULT_COOKIE}。请在有图形界面的浏览器打开 https://yuanbao.tencent.com 扫码登录，"
               "再按 SKILL 说明把 Cookie 保存到上述文件（或运行 yuanbao_login.py）。")


def yuanbao_resolve(link: dict, auth: dict, timeout_s=60) -> tuple[dict, dict]:
    deadline = time.monotonic() + timeout_s
    if link["kind"] != "sph":
        raise Fail("元宝备用路线只支持 https://weixin.qq.com/sph/xxx 链接")
    headers = {"User-Agent": auth.get("user_agent") or UA, "Origin": YB, "Referer": YB + "/",
               "Accept": "application/json", "x-source": "web", "Cookie": auth["cookie"]}
    for k, v in auth.get("headers", {}).items():
        if k in ("authorization", "t-userid", "x-id", "x-device-id", "x-hy92", "x-hy93"):
            headers[k] = v
    try:
        r = post_json(YB + "/api/weixin/get_parse_result",
                      {"type": "video_channel_url", "url": link["url"], "scene": 1}, headers, timeout=_resolve_left(deadline, 30))
    except urllib.error.HTTPError as e:
        raise Fail(f"元宝解析接口 HTTP {e.code}" + ("，Cookie 可能已过期，请重新扫码" if e.code in (401, 403) else ""))
    if r.get("code") != 0:
        raise Fail(f"元宝解析失败 code={r.get('code')} msg={r.get('msg') or r.get('message')}；Cookie 可能失效")
    pu = (r.get("data") or {}).get("playable_url") or ""
    q = parse_qs(urlsplit(pu).query)
    if not (q.get("token") and q.get("eid")):
        raise Fail("元宝未返回带 token/eid 的预览地址")
    d = feed_info({"baseReq": {"generalToken": q["token"][0]}, "exportId": q["eid"][0]}, pu, timeout=_resolve_left(deadline, 30))
    data = d.get("data") or {}
    fi = data.get("feedInfo") or {}
    if d.get("errCode") or not fi:
        raise Fail("视频号预览失败：视频可能已删除/不可见，或预览 token 失效")
    if fi.get("mediaType") not in (None, 4):
        raise Fail("该链接不是普通视频（可能是图集/直播），暂不支持")
    urls = {}
    for k in ("h264", "h265"):
        u = (fi.get(k + "VideoInfo") or {}).get("videoUrl")
        if u:
            urls[k] = u
    if fi.get("videoUrl"):
        urls.setdefault("video", fi["videoUrl"])
    if not urls:
        raise Fail("元宝路线拿到详情但缺少视频地址")
    return urls, normalize_meta(data)


# ---------------- 媒体处理 ----------------
def probe(path: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "format=duration:stream=codec_type,codec_name,width,height",
                          "-of", "json", str(path)], capture_output=True, text=True,
                         check=True, timeout=30).stdout
    j = json.loads(out or "{}")
    v = next((s for s in j.get("streams", []) if s.get("codec_type") == "video"), {})
    a = next((s for s in j.get("streams", []) if s.get("codec_type") == "audio"), {})
    duration = float(j.get("format", {}).get("duration", 0) or 0)
    if not v or duration <= 0 or not v.get("width") or not v.get("height"):
        raise Fail("ffprobe 未识别到有效的视频流、时长或分辨率")
    return {"duration": duration,
            "video_codec": v.get("codec_name"), "width": v.get("width"), "height": v.get("height"),
            "audio_codec": a.get("codec_name")}


def extract_frames(video: Path, outdir: Path, n: int, duration: float):
    outdir.mkdir(exist_ok=True)
    paths = []
    for i in range(n):
        t = duration * (i + 0.5) / n
        p = outdir / f"frame_{i + 1:02d}_{t:06.1f}s.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(video),
                        "-frames:v", "1", "-vf", "scale='min(720,iw)':-2", str(p)], check=True, timeout=30)
        if p.is_file() and p.stat().st_size:
            paths.append(str(p))
        else:
            raise Fail("ffmpeg 未生成有效的抽帧图片")
    return paths


# ---------------- 模型获取（本地目录 / 缓存 / ModelScope / hf-mirror / HF） ----------------
class ModelError(Exception):
    pass


MODEL_HINT = "可换 --model-source，或用 --model-dir 指定本地模型；--no-asr 可只取视频。断点会保留供下次续传。"


def _sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def _file_ok(p, size, sha):
    return (isinstance(size, int) and size >= 0 and isinstance(sha, str)
            and re.fullmatch(r"[0-9a-f]{64}", sha) is not None
            and p.is_file() and p.stat().st_size == size and _sha256(p) == sha)


def _time_left(deadline, limit=10):
    left = deadline - time.monotonic()
    if left <= 0:
        raise ModelError("模型准备超过总时限；已保留可续传的断点")
    return min(limit, left)


def _model_relative(name):
    if not isinstance(name, str) or not name or "\\" in name or ":" in name or any(ord(c) < 32 for c in name):
        raise ModelError("模型清单含非法路径")
    rel = Path(name)
    if rel.is_absolute() or ".." in rel.parts or rel.as_posix() != name or name == ".":
        raise ModelError("模型清单路径必须是规范相对路径")
    return rel


def _model_file(root, name):
    rel = _model_relative(name)
    root = Path(root)
    target = root / rel
    if root.is_symlink() or not target.resolve().is_relative_to(root.resolve()):
        raise ModelError("模型路径越出缓存目录")
    for part in (target, *target.parents):
        if part == root:
            break
        if part.is_symlink():
            raise ModelError("模型写入路径不能包含符号链接")
    return target


@contextlib.contextmanager
def _model_lock(directory):
    directory = Path(directory)
    if directory.is_symlink():
        raise ModelError("模型缓存目录不能是符号链接")
    directory.mkdir(parents=True, exist_ok=True)
    fd = os.open(directory / ".download.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ModelError("该模型正在由另一个进程准备，请稍后重试")
        yield
    finally:
        os.close(fd)


def fetch_file(urls, dest, size=None, sha=None, tries=None, deadline=None):
    """Resume only validated ranges; publish only after exact size and SHA-256 match."""
    dest = Path(dest)
    if not isinstance(size, int) or size < 0 or not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{64}", sha):
        raise ModelError("下载模型必须提供有效大小和 SHA-256")
    try:
        tries = int(tries if tries is not None else os.environ.get("WCR_DL_TRIES", "3"))
    except ValueError:
        raise ModelError("WCR_DL_TRIES 必须为 1–6 的整数")
    if not 1 <= tries <= 6:
        raise ModelError("WCR_DL_TRIES 必须为 1–6 的整数")
    deadline = deadline if deadline is not None else time.monotonic() + 300
    if dest.is_symlink():
        raise ModelError("模型目标文件不能是符号链接")
    if _file_ok(dest, size, sha):
        return "cached"
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    if part.is_symlink():
        raise ModelError("模型断点文件不能是符号链接")
    for url in urls:
        checked_https(url)
        for attempt in range(tries):
            _time_left(deadline)
            have = part.stat().st_size if part.exists() else 0
            if part.exists() and have >= size:
                if _file_ok(part, size, sha):
                    part.replace(dest)
                    return url
                part.unlink()
                have = 0
            headers = {"User-Agent": "wechat-channels-reader/2", "Accept-Encoding": "identity"}
            if have:
                headers["Range"] = f"bytes={have}-"
            try:
                request = urllib.request.Request(url, headers=headers)
                with open_response(request, _time_left(deadline)) as response:
                    body_limit = size
                    if response.status == 206:
                        match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", response.headers.get("Content-Range", ""))
                        if (not match or int(match[1]) != have or int(match[3]) != size
                                or not have <= int(match[2]) < size):
                            raise ModelError("续传响应 Content-Range 不匹配")
                        body_limit = int(match[2]) - have + 1
                    elif response.status == 200:
                        have = 0  # Server ignored Range: truncate rather than append.
                    else:
                        raise ModelError("模型服务返回异常状态")
                    next_log = time.monotonic() + 5
                    with part.open("ab" if have else "wb") as f:
                        for chunk in response_chunks(response, body_limit, deadline):
                            f.write(chunk)
                            if time.monotonic() >= next_log:
                                log(f"模型 {dest.name}: {f.tell() / 1e6:.1f}/{size / 1e6:.1f} MB")
                                next_log = time.monotonic() + 5
                if _file_ok(part, size, sha):
                    part.replace(dest)
                    return url
                if part.stat().st_size >= size:
                    part.unlink()  # A complete but corrupt part must not poison future retries.
            except urllib.error.HTTPError as e:
                if e.code in (400, 401, 403, 404):
                    break
            except (OSError, Fail, ModelError, ValueError):
                pass
            if attempt + 1 < tries:
                time.sleep(min(2, _time_left(deadline)))
    _time_left(deadline)
    raise ModelError(f"{dest.name} 下载或大小/SHA-256 校验失败；" + MODEL_HINT)


def _sources(source):
    source = (source or os.environ.get("WCR_MODEL_SOURCE") or "auto").lower()
    custom = (os.environ.get("HF_ENDPOINT") or "").rstrip("/")
    if custom:
        checked_https(custom)
        if urlsplit(custom).query or urlsplit(custom).fragment:
            raise ModelError("HF_ENDPOINT 不能包含查询参数或片段")
    table = {"modelscope": ("modelscope", "https://modelscope.cn"),
             "hf-mirror": ("hf", custom or "https://hf-mirror.com"),
             "hf": ("hf", "https://huggingface.co")}
    if source == "auto":
        order = ["hf-mirror", "modelscope", "hf"] if custom else ["modelscope", "hf-mirror", "hf"]
    elif source in table:
        order = [source]
    else:
        raise ModelError("未知模型源，可选 auto|modelscope|hf-mirror|hf")
    result, seen = [], set()
    for label in order:
        kind, endpoint = table[label]
        if (kind, endpoint) not in seen:
            result.append((label, kind, endpoint))
            seen.add((kind, endpoint))
    return result


def _file_url(kind, endpoint, repo, name):
    revision = "master" if kind == "modelscope" else "main"
    prefix = "/models" if kind == "modelscope" else ""
    return f"{endpoint}{prefix}/{repo}/resolve/{revision}/{quote(name, safe='/')}"


def _manifest_files(files):
    checked = {}
    for name, value in files.items():
        _model_relative(name)
        if (not isinstance(value, (list, tuple)) or len(value) != 2
                or not isinstance(value[0], int) or value[0] < 0
                or not isinstance(value[1], str) or not re.fullmatch(r"[0-9a-f]{64}", value[1])):
            raise ModelError("模型清单缺少有效大小或 SHA-256")
        checked[name] = tuple(value)
    if not checked:
        raise ModelError("模型清单为空")
    return checked


def ms_manifest(repo, deadline=None):
    deadline = deadline if deadline is not None else time.monotonic() + 30
    data = json.loads(http(f"https://modelscope.cn/api/v1/models/{repo}/repo/files?Revision=master&Recursive=true",
                           timeout=_time_left(deadline, 30))[2])
    if data.get("Code") != 200:
        raise ModelError("ModelScope 未返回有效清单")
    files = {}
    for item in data["Data"]["Files"]:
        if item.get("Type") != "blob":
            continue
        name = item["Path"]
        if name in files:
            raise ModelError("模型清单存在重复路径")
        files[name] = (item["Size"], item.get("Sha256"))
    return _manifest_files(files)


def _complete(directory, files):
    return all(_file_ok(directory / name, size, sha) for name, (size, sha) in files.items())


def _hf_cache_dir(name):
    root = Path(os.environ.get("HF_HUB_CACHE") or Path(os.environ.get("HF_HOME", "~/.cache/huggingface")).expanduser() / "hub").expanduser()
    for snapshot in sorted((root / f"models--Systran--faster-whisper-{name}" / "snapshots").glob("*")):
        if _complete(snapshot, WHISPER_FILES[name]):
            return snapshot
    return None


def whisper_model_path(name, model_dir=None, source=None, timeout=300):
    if name not in WHISPER_FILES or timeout <= 0:
        raise ModelError("无效的模型名或模型准备时限")
    files = WHISPER_FILES[name]
    if model_dir:
        directory = Path(model_dir).expanduser()
        if not all((directory / n).is_file() and (directory / n).stat().st_size > 0 for n in files):
            raise ModelError("本地模型目录缺少非空的 model.bin/config.json/tokenizer.json/vocabulary.txt")
        # Explicit custom model directories may be differently quantized: validate shape, not standard hashes.
        for n in ("config.json", "tokenizer.json"):
            if not isinstance(json.loads((directory / n).read_text()), dict):
                raise ModelError("本地模型 JSON 格式无效")
        return directory
    directory = MODELS_DIR / f"faster-whisper-{name}"
    if _complete(directory, files):
        return directory
    snapshot = _hf_cache_dir(name)
    if snapshot:
        return snapshot
    deadline = time.monotonic() + timeout
    with _model_lock(directory):
        if _complete(directory, files):
            return directory
        for label, kind, endpoint in _sources(source):
            for repo_pattern in WHISPER_REPOS[kind]:
                _time_left(deadline)
                repo = repo_pattern.format(name)
                try:
                    for fn, (size, sha) in sorted(files.items(), key=lambda x: x[1][0]):
                        fetch_file([_file_url(kind, endpoint, repo, fn)], _model_file(directory, fn), size, sha, deadline=deadline)
                    (directory / ".complete").write_text(json.dumps({"source": label, "repo": repo, "files": files}), encoding="utf-8")
                    return directory
                except (OSError, Fail, ModelError, ValueError):
                    continue
    raise ModelError("Whisper 模型未就绪；" + MODEL_HINT)


def funasr_model_paths(source=None, timeout=300):
    if source not in (None, "auto", "modelscope"):
        raise ModelError("FunASR 目前仅支持 ModelScope，不支持该模型源")
    if timeout <= 0:
        raise ModelError("模型准备时限必须为正数")
    deadline = time.monotonic() + timeout
    out = {}
    for role, repo in FUNASR_REPOS.items():
        directory = MODELS_DIR / "funasr" / repo.split("/")[-1]
        marker = directory / ".complete"
        with _model_lock(directory):
            try:
                saved = json.loads(marker.read_text())
                files = _manifest_files(saved["files"]) if saved.get("repo") == repo else {}
            except (OSError, ValueError, KeyError, TypeError, ModelError):
                files = {}
            if files and _complete(directory, files):
                out[role] = directory
                continue
            manifest = ms_manifest(repo, deadline)
            files = {fn: value for fn, value in manifest.items()
                     if not fn.startswith((".", "example/", "fig/"))
                     and not fn.endswith((".png", ".jpg", ".wav", ".md", ".py", ".sh", ".so", ".dll"))}
            _manifest_files(files)
            if not any(fn.endswith((".pt", ".pth", ".onnx", ".bin")) and value[0] > 0 for fn, value in files.items()):
                raise ModelError("FunASR 清单缺少模型权重文件")
            for fn, (size, sha) in files.items():
                fetch_file([_file_url("modelscope", "https://modelscope.cn", repo, fn)],
                           _model_file(directory, fn), size, sha, deadline=deadline)
            marker.write_text(json.dumps({"source": "modelscope", "repo": repo, "files": files}), encoding="utf-8")
            out[role] = directory
    return out


def _load_wav(wav: Path):
    import numpy as np
    with wave.open(str(wav)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768


def transcribe(wav: Path, model_name: str, model_dir=None, source=None, model_timeout=300) -> tuple[list, dict]:
    from faster_whisper import WhisperModel
    audio = _load_wav(wav)
    if audio.size == 0:
        return [], {"language": None}
    path = whisper_model_path(model_name, model_dir, source, model_timeout)
    model = WhisperModel(str(path), device="cpu", compute_type="int8",
                         cpu_threads=max(1, (os.cpu_count() or 2) - 1))
    lang, prob = None, 0.0
    try:
        lang, prob, _ = model.detect_language(audio)
    except Exception:
        pass
    kw = {"language": lang, "vad_filter": True, "beam_size": 5}
    if lang == "zh":
        kw["initial_prompt"] = "以下是普通话的句子，使用简体中文。"
    def run(**extra):
        it, inf = model.transcribe(audio, **{**kw, **extra})
        return [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()} for s in it], inf
    segs, info = run()
    dur = audio.size / 16000
    if segs and dur > 5 and sum(len(s["text"]) for s in segs) < dur:   # 有人声但字数异常少：可能是解码提前终止，换参数再跑一次取较长者
        log("转写字数偏少，换参数重试一次…")
        segs2, info2 = run(vad_filter=False, condition_on_previous_text=False)
        if sum(len(s["text"]) for s in segs2) > sum(len(s["text"]) for s in segs):
            segs, info = segs2, info2
    return segs, {"engine": "faster-whisper", "model": model_name, "model_path": str(path), "language": info.language,
                  "language_probability": round(info.language_probability, 3)}


def transcribe_funasr(wav: Path, source=None, model_timeout=300) -> tuple[list, dict]:
    try:
        from funasr import AutoModel
    except ImportError:
        raise ModelError("未安装 FunASR：运行 setup.sh --with-funasr，或改用默认 --asr whisper")
    p = funasr_model_paths(source, model_timeout)
    m = AutoModel(model=str(p["asr"]), vad_model=str(p["vad"]), punc_model=str(p["punc"]),
                  device="cpu", disable_update=True, disable_pbar=True, log_level="ERROR")
    res = m.generate(input=str(wav), batch_size_s=300, sentence_timestamp=True)
    segs = []
    for r in res:
        for s in r.get("sentence_info") or []:
            segs.append({"start": round(s["start"] / 1000, 2), "end": round(s["end"] / 1000, 2), "text": s["text"].strip()})
        if not r.get("sentence_info") and r.get("text"):
            segs.append({"start": 0.0, "end": 0.0, "text": r["text"].strip()})
    return segs, {"engine": "funasr", "model": FUNASR_REPOS["asr"], "language": "zh"}


def ts(x):
    return f"{int(x // 60):02d}:{x % 60:05.2f}"


# ---------------- 主流程 ----------------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("text", nargs="*", help="分享链接或整段分享文案")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT_ROOT,
                    help="输出根目录；每次运行创建 <短码>/<独立运行目录>")
    ap.add_argument("--model", default="small", choices=["tiny", "base", "small", "medium"])
    ap.add_argument("--no-asr", action="store_true")
    ap.add_argument("--backend", default="auto", choices=["auto", "ffmpegtool", "paste2vid", "yuanbao"])
    ap.add_argument("--allow-third-party", action="store_true", help="允许把规范化链接交给 ffmpegtool.com")
    ap.add_argument("--allow-paste2vid", action="store_true", help="允许把规范化链接交给 paste2vid.com")
    ap.add_argument("--resolve-timeout", type=int, default=180, help="所有取链路线共享预算（秒），不含公开元数据请求")
    ap.add_argument("--allow-saved-auth", action="store_true", help="允许使用本工具配置目录的元宝凭据")
    ap.add_argument("--frames", type=int, default=None, help="强制抽 0–32 帧（默认无人声/字少时抽 4 帧）")
    ap.add_argument("--cookie", type=Path, help="显式选用元宝凭据文件；不自动读取其他应用的凭据")
    ap.add_argument("--max-download-mb", type=int, default=512)
    ap.add_argument("--max-duration", type=int, default=7200, help="最大视频时长（秒）")
    ap.add_argument("--download-timeout", type=int, default=300, help="单次下载时限（秒）")
    ap.add_argument("--asr", default="whisper", choices=["whisper", "funasr"])
    ap.add_argument("--model-dir", type=Path, help="显式本地 Whisper 模型目录，不下载")
    ap.add_argument("--model-source", choices=["auto", "modelscope", "hf-mirror", "hf"])
    ap.add_argument("--model-timeout", type=int, default=300, help="本次模型准备的总预算（秒）")
    ap.add_argument("--download-model", choices=["tiny", "base", "small", "medium", "funasr"])
    a = ap.parse_args()
    out, meta, stage = None, {}, "input"
    try:
        if a.model_timeout <= 0:
            raise Fail("--model-timeout 必须为正整数")
        if a.model_dir and (a.asr == "funasr" or a.download_model == "funasr"):
            raise Fail("--model-dir 仅适用于 Whisper")
        if a.download_model:
            stage = "model"
            if a.download_model == "funasr":
                paths = {k: str(v) for k, v in funasr_model_paths(a.model_source, a.model_timeout).items()}
            else:
                paths = str(whisper_model_path(a.download_model, a.model_dir, a.model_source, a.model_timeout))
            print(json.dumps({"ok": True, "model": a.download_model, "paths": paths}, ensure_ascii=False))
            return 0
        link = extract_link(" ".join(a.text))
        if a.frames is not None and not 0 <= a.frames <= 32:
            raise Fail("--frames 必须在 0–32 之间")
        if a.max_download_mb <= 0 or a.download_timeout <= 0 or a.max_duration <= 0 or a.resolve_timeout <= 0:
            raise Fail("下载上限与时限必须为正整数")
        use_ff = a.backend in ("auto", "ffmpegtool") and a.allow_third_party
        use_p2v = a.backend in ("auto", "paste2vid") and a.allow_paste2vid
        use_yb = a.backend in ("auto", "yuanbao") and (a.cookie is not None or a.allow_saved_auth)
        if a.backend == "ffmpegtool" and not use_ff:
            raise Fail("第三方解析需显式传入 --allow-third-party")
        if a.backend == "paste2vid" and not use_p2v:
            raise Fail("paste2vid 解析需显式传入 --allow-paste2vid")
        if a.backend == "yuanbao" and not use_yb:
            raise Fail("元宝解析需显式传入 --cookie FILE 或 --allow-saved-auth")
        if not use_ff and not use_p2v and not use_yb:
            raise Fail("请显式启用解析路线：--allow-third-party、--allow-paste2vid 或元宝凭据选项")
        stage = "prepare"
        out = make_output(a.out, link["code"])
        meta = {"source_url": link["url"], "short_code": link["code"], "errors": [],
                "fetched_at": datetime.now(CST).strftime("%Y-%m-%d %H:%M:%S UTC+8"), "steps": {}}
        log("链接:", link["url"], "输出:", out)
        stage = "resolve"
        public = public_metadata(link)
        meta.update({k: v for k, v in public.items() if k != "_error"})
        meta["steps"]["public_preview"] = "ok" if public and "_error" not in public else "unavailable"
        urls, backend_used = {}, None
        resolve_deadline = time.monotonic() + a.resolve_timeout
        if use_ff:
            try:
                log("主路线：ffmpegtool.com 解析中…")
                urls = ffmpegtool_resolve(link["url"], timeout_s=_resolve_left(resolve_deadline, 60))
                backend_used = "ffmpegtool"
            except Exception as e:
                meta["errors"].append(f"ffmpegtool: {e}")
        if not urls and use_p2v:
            try:
                urls, parsed_meta = paste2vid_resolve(link["url"], timeout_s=_resolve_left(resolve_deadline, 90))
                backend_used = "paste2vid"
                if not public or "_error" in public:
                    meta.update(parsed_meta)
            except Exception as error:
                meta["errors"].append(f"paste2vid: {error}")
        if not urls and use_yb:
            try:
                _resolve_left(resolve_deadline)
                auth = load_yuanbao_auth(a.cookie)
                urls, ymeta = yuanbao_resolve(link, auth, timeout_s=_resolve_left(resolve_deadline, 60))
                backend_used = "yuanbao"
                if not public or "_error" in public:
                    meta.update(ymeta)
            except Exception as e:
                # Auth/network exceptions can echo header values. Never persist their raw text.
                meta["errors"].append(f"yuanbao: {type(e).__name__}；请检查凭据、网络或接口兼容性")
        meta["backend"] = backend_used
        if not urls:
            raise Fail("未解析到视频地址；" + "; ".join(meta["errors"]))
        if meta.get("cover_url"):
            try:
                download(meta["cover_url"], out / "cover.jpg", max_bytes=20 << 20, timeout=30,
                         allowed_hosts={urlsplit(meta["cover_url"]).hostname} if backend_used == "paste2vid" else None)
                meta["steps"]["cover"] = "ok"
            except Exception as e:
                meta["steps"]["cover"] = f"fail: {e}"
        stage = "download"
        video, downloaded = out / "video.mp4", False
        for kind in ("h264", "video", "h265"):
            if not urls.get(kind):
                continue
            try:
                download(urls[kind], video, expect_mp4=True,
                         max_bytes=a.max_download_mb << 20, timeout=a.download_timeout,
                         allowed_hosts=P2V_MEDIA_HOSTS if backend_used == "paste2vid" else None)
                downloaded = True
                meta["video_variant"] = kind
                break
            except Exception as e:
                meta["errors"].append(f"download {kind}: {e}")
        if not downloaded:
            raise Fail("本次运行未下载到视频")
        safe_urls = {k: checked_https(u) for k, u in urls.items() if k in ("h264", "video", "h265")}
        (out / "video_url.txt").write_text("\n".join(f"{k}\t{u}" for k, u in safe_urls.items()) + "\n", encoding="utf-8")
        stage = "probe"
        meta.update(probe(video))
        if meta["duration"] > a.max_duration:
            raise Fail("视频超过最大时长限制")
        segs, asr = [], {"status": "skipped", "reason": "--no-asr"}
        stage = "asr"
        if not a.no_asr and meta.get("audio_codec"):
            wav = out / "audio.wav"
            started = time.monotonic()
            try:
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", str(wav)], check=True, timeout=300)
                if a.asr == "funasr":
                    segs, asr = transcribe_funasr(wav, a.model_source, a.model_timeout)
                else:
                    segs, asr = transcribe(wav, a.model, a.model_dir, a.model_source, a.model_timeout)
                asr.update({"status": "ok", "seconds": round(time.monotonic() - started, 1)})
                asr.setdefault("model", a.model if a.asr == "whisper" else FUNASR_REPOS["asr"])
                lines = [f"[{ts(s['start'])} - {ts(s['end'])}] {s['text']}" for s in segs]
                text = "\n".join(lines) + ("\n" if lines else "（未检测到人声）\n")
            except Exception as e:
                # Preserve useful video/frame output, but never report failed ASR as success or silence.
                asr = {"status": "failed", "engine": a.asr, "error": f"{type(e).__name__}: {e}"}
                meta["errors"].append("asr: " + asr["error"])
                segs = []
                text = "（转写失败：" + asr["error"] + "）\n"
            (out / "transcript.txt").write_text(text, encoding="utf-8")
        elif not meta.get("audio_codec"):
            asr = {"status": "skipped", "reason": "视频无音轨"}
        meta["asr"] = asr
        stage = "frames"
        chars = sum(len(s["text"]) for s in segs)
        n = a.frames if a.frames is not None else (4 if chars < max(10, meta["duration"]) else 0)
        frames = extract_frames(video, out / "frames", n, meta["duration"]) if n else []
        meta["frames"] = frames
        stage = "save"
        title = (meta.get("description") or link["code"]).splitlines()[0][:60]
        md = [f"# 视频号内容：{title}", "", f"- 来源：{link['url']}",
              f"- 作者：{meta.get('author') or '未取得'}", f"- 发布时间：{meta.get('createtime_cst') or '未取得'}",
              f"- 时长：{meta['duration']:.1f}s，分辨率 {meta.get('width')}x{meta.get('height')}，取链路线 {backend_used}",
              f"- 转写状态：{asr['status']}；{asr.get('error') or asr.get('reason') or asr.get('language') or '未知语言'}", "",
              "## 描述", "", meta.get("description") or "（无）", "", "## 转写全文（带时间戳）", ""]
        md += [f"[{ts(s['start'])}] {s['text']}" for s in segs] or ["（转写失败，未取得转写正文）" if asr["status"] == "failed" else "（无人声或未转写；需结合抽帧理解）"]
        if frames:
            md += ["", "## 抽帧", ""] + [f"- {p}" for p in frames]
        (out / "summary_input.md").write_text("\n".join(md) + "\n", encoding="utf-8")
        ok = asr["status"] != "failed"
        meta.update({"ok": ok, "video_ok": True, "status": "success" if ok else "partial"})
        (out / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"ok": ok, "video_ok": True, "status": meta["status"], "out": str(out), "backend": backend_used, "duration": meta["duration"],
                          "resolution": f"{meta.get('width')}x{meta.get('height')}", "segments": len(segs),
                          "asr": asr["status"], "frames": len(frames)}, ensure_ascii=False))
        return 0 if ok else 5
    except Exception as e:
        code = 2 if stage == "input" else 3 if stage in ("resolve", "download") else 4
        message = f"{type(e).__name__}: {e}"
        meta.update({"ok": False, "failed_stage": stage})
        meta.setdefault("errors", []).append(message)
        if out is not None:
            try:
                (out / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
            except OSError:
                log("无法保存失败元数据")
        log("失败阶段:", stage, message)
        print(json.dumps({"ok": False, "stage": stage, "error": message,
                          "out": str(out) if out else None}, ensure_ascii=False))
        return code


if __name__ == "__main__":
    sys.exit(main())
