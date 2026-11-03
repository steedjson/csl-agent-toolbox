"""Opt-in offline browser fixtures: WCR_BROWSER_FIXTURES=1, Playwright and Chrome required."""
import json
import os
import types
import unittest

from test_sph_fetch import sph, LINK, MEDIA


@unittest.skipUnless(os.environ.get("WCR_BROWSER_FIXTURES") == "1", "opt-in offline browser fixtures")
class BrowserFixtureTests(unittest.TestCase):
    def test_only_open_error_dialog_is_read(self):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as engine:
            browser = engine.chromium.launch(headless=True, executable_path=sph.chrome_path())
            try:
                page = browser.new_page()
                page.set_content('''<div role="dialog" style="opacity:0"><h3>解析失败</h3><p>hidden wrong error</p></div>
                    <div role="dialog"><h3>反馈</h3><p>unrelated feedback</p></div>
                    <div role="alertdialog" aria-describedby="reason"><h3>解析失败</h3><p id="reason">real error</p></div>''')
                self.assertEqual(sph._fft_dialog_error(page), "解析失败：real error")
                page.set_content('''<div role="dialog" aria-hidden="true"><h3>解析失败</h3><p>hidden error</p></div>
                    <div role="dialog"><h3>反馈</h3><p>unrelated feedback</p></div>''')
                self.assertEqual(sph._fft_dialog_error(page), "")
            finally:
                browser.close()

    def run_routed_site(self, fail=False):
        from playwright.sync_api import sync_playwright
        requests = []
        body = '''<!doctype html><meta charset="utf-8"><input id="link" type="text">
            <button onclick="run()">开始解析</button>
            <div role="dialog" style="opacity:0"><h3>反馈</h3><p>unrelated feedback</p></div>
            <div role="alertdialog" id="error" aria-hidden="true" aria-describedby="reason">
              <h3>解析失败</h3><p id="reason"></p></div>
            <section id="result" style="opacity:0"><h3>H.264 视频</h3>
              <button onclick="navigator.clipboard.writeText('MEDIA_URL')">复制链接</button></section>
            <script>async function run(){
              const d=await (await fetch('/api/parse',{method:'POST'})).json();
              if(d.code===0){document.querySelector('#result').style.opacity='1';}
              else{document.querySelector('#error').setAttribute('aria-hidden','false');
                   document.querySelector('#reason').innerText=d.message;}
            }</script>'''.replace("MEDIA_URL", MEDIA)
        def route_handler(route):
            request = route.request
            if request.url == sph.FFTOOL:
                route.fulfill(status=200, content_type="text/html", body=body)
            elif request.url == "https://ffmpegtool.com/api/parse":
                requests.append(request.method)
                response = {"code": 1, "message": "backend busy"} if fail else {"code": 0}
                route.fulfill(status=503 if fail else 200, content_type="application/json", body=json.dumps(response))
            else:
                route.abort()  # No request is allowed to leave this fixture.
        with sync_playwright() as engine:
            class Browser:
                def __init__(self, real):
                    self.real = real
                def new_context(self, **kwargs):
                    context = self.real.new_context(**kwargs)
                    context.route("**/*", route_handler)
                    return context
                def close(self):
                    self.real.close()
            class Chromium:
                def launch(self, **kwargs):
                    return Browser(engine.chromium.launch(**kwargs))
            routed = types.SimpleNamespace(chromium=Chromium())
            if fail:
                with self.assertRaises(sph.Fail) as caught:
                    sph._fft_once(routed, LINK, 15)
                self.assertIn("backend busy", str(caught.exception))
                self.assertNotIn("unrelated feedback", str(caught.exception))
            else:
                self.assertEqual(sph._fft_once(routed, LINK, 15), {"h264": MEDIA})
        self.assertEqual(requests, ["POST"])

    def test_parse_submits_once_and_ignores_hidden_copy_button(self):
        self.run_routed_site()

    def test_api_failure_reports_service_message_not_feedback(self):
        self.run_routed_site(fail=True)


if __name__ == "__main__":
    unittest.main()
