#!/usr/bin/env python3
"""Open Yuanbao for user-controlled login; store credentials outside the skill source."""
import argparse
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

from sph_fetch import DEFAULT_COOKIE, chrome_path, save_auth


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_COOKIE)
    ap.add_argument("--timeout", type=int, default=300)
    a = ap.parse_args()
    if a.timeout <= 0:
        ap.error("--timeout must be positive")
    if not os.environ.get("DISPLAY") and sys.platform.startswith("linux"):
        ap.error("需要图形界面 DISPLAY；请在桌面环境运行并由用户本人登录")
    from playwright.sync_api import sync_playwright
    keep = {"authorization", "t-userid", "x-id", "x-device-id", "x-hy92", "x-hy93"}
    with sync_playwright() as p:
        exe = chrome_path()
        browser = p.chromium.launch(headless=False, **({"executable_path": exe} if exe else {}))
        try:
            ctx = browser.new_context(locale="zh-CN")
            headers = {}
            def capture(request):
                url = urlsplit(request.url)
                if url.scheme == "https" and url.hostname == "yuanbao.tencent.com" and url.path.startswith("/api/"):
                    headers.update({k: v for k, v in request.headers.items() if k in keep})
            ctx.on("request", capture)
            page = ctx.new_page()
            page.goto("https://yuanbao.tencent.com", wait_until="domcontentloaded", timeout=60000)
            print("请由用户本人点击登录并扫码；凭据只保存到所选的本机文件。", flush=True)
            end = time.monotonic() + a.timeout
            while time.monotonic() < end:
                cookies = {c["name"]: c["value"] for c in ctx.cookies("https://yuanbao.tencent.com/api/weixin/get_parse_result") if c.get("value")}
                if cookies.get("hy_user") and cookies.get("hy_token"):
                    page.wait_for_timeout(3000)
                    save_auth(a.out, {"cookie": "; ".join(f"{k}={v}" for k, v in cookies.items()),
                                      "headers": headers, "user_agent": page.evaluate("navigator.userAgent"),
                                      "saved_at": time.strftime("%Y-%m-%d %H:%M:%S %z")})
                    print("已保存:", a.out.expanduser())
                    return 0
                page.wait_for_timeout(1000)
            print("超时未检测到登录", file=sys.stderr)
            return 1
        finally:
            browser.close()


if __name__ == "__main__":
    sys.exit(main())
