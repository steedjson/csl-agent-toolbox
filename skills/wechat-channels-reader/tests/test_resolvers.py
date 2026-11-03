"""Offline regressions for third-party resolution, consent and budgets."""
import contextlib
import html
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock
import urllib.error
import urllib.request

from test_sph_fetch import sph, LINK, MEDIA, MP4, SCRIPTS


def success_payload():
    meta = {"title": "fixture", "formats": [{"id": "h264", "download_url": MEDIA}]}
    markup = '<div data-parse-meta="' + html.escape(json.dumps(meta), quote=True) + '"></div>'
    return json.dumps({"code": 0, "data": {"html": markup}}).encode()


class ResolverTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for patch in (
            mock.patch.object(urllib.request.OpenerDirector, "open", side_effect=AssertionError("Network forbidden")),
            mock.patch.dict(os.environ, {"WCR_FFT_BACKOFF": "0,0"}),
        ):
            patch.start()
            self.addCleanup(patch.stop)

    def run_main(self, *args):
        output = io.StringIO()
        with mock.patch.object(sys, "argv", ["sph_fetch.py", *args]), \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
            code = sph.main()
        return code, json.loads(output.getvalue().splitlines()[-1])

    def fake_playwright(self):
        api = types.ModuleType("playwright.sync_api")
        manager = mock.MagicMock()
        manager.__enter__.return_value = object()
        api.sync_playwright = lambda: manager
        return mock.patch.dict(sys.modules, {"playwright": types.ModuleType("playwright"), "playwright.sync_api": api})

    def test_ff_error_accepts_non_object_json_and_missing_body(self):
        for value in ([], ["upstream failed"], "error", None, 5):
            with self.subTest(value=value):
                message = sph._fft_api_error([{"status": 500, "json": value}])
                self.assertIn("HTTP 500", message)

    def test_ff_error_does_not_log_gate_query_or_trace(self):
        message = sph._fft_api_error([{"url": "https://ffmpegtool.com/api/parse?token=secret-query",
                                      "status": 503, "json": {"code": 1, "message": "busy", "trace": "secret-trace"}}])
        self.assertIn("busy", message)
        self.assertNotIn("secret", message)
        self.assertEqual(sph._fft_api_error([{"status": 200, "json": {"code": "0"}}]), "")

    def test_quota_detection_does_not_match_processing_or_protocol(self):
        for message in ("processing failed", "protocol error", "proxy busy"):
            self.assertFalse(sph._blocked_message(message), message)
        for message in ("quota exhausted", "PRO plan required", "rate limit", "额度用完", "需要验证码"):
            self.assertTrue(sph._blocked_message(message), message)

    def test_backoff_validated_at_runtime(self):
        for raw in ("oops", "-1", "nan", "inf", "31", "0,0,0,0"):
            with self.subTest(raw=raw), mock.patch.dict(os.environ, {"WCR_FFT_BACKOFF": raw}), self.assertRaises(sph.Fail):
                sph._fft_backoff()
        with mock.patch.dict(os.environ, {"WCR_FFT_BACKOFF": ""}):
            self.assertEqual(sph._fft_backoff(), [])

    def test_help_still_works_with_invalid_backoff_environment(self):
        env = os.environ.copy()
        env["WCR_FFT_BACKOFF"] = "invalid"
        result = subprocess.run([sys.executable, str(SCRIPTS / "sph_fetch.py"), "--help"], env=env,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_ff_retry_keeps_one_shared_budget(self):
        clock, remaining = [0], []
        def once(engine, text, timeout):
            remaining.append(timeout)
            clock[0] += 2
            if len(remaining) == 1:
                raise sph.Fail("busy")
            return {"h264": MEDIA}
        def sleep(seconds):
            clock[0] += seconds
        with self.fake_playwright(), mock.patch.dict(os.environ, {"WCR_FFT_BACKOFF": "1"}), \
                mock.patch.object(sph.time, "monotonic", side_effect=lambda: clock[0]), \
                mock.patch.object(sph.time, "sleep", side_effect=sleep), \
                mock.patch.object(sph, "_fft_once", side_effect=once):
            result = sph.ffmpegtool_resolve(LINK, timeout_s=10)
        self.assertEqual(result, {"h264": MEDIA})
        self.assertEqual(remaining, [10, 7])

    def test_ff_quota_or_captcha_is_not_retried(self):
        with self.fake_playwright(), \
                mock.patch.object(sph, "_fft_once", side_effect=sph.ResolverBlocked("captcha")) as once, \
                self.assertRaises(sph.ResolverBlocked):
            sph.ffmpegtool_resolve(LINK)
        once.assert_called_once()

    def test_ff_backoff_must_fit_remaining_budget(self):
        with self.fake_playwright(), mock.patch.dict(os.environ, {"WCR_FFT_BACKOFF": "30"}), \
                mock.patch.object(sph, "_fft_once", side_effect=sph.Fail("busy")) as once, \
                mock.patch.object(sph.time, "sleep") as sleep, self.assertRaises(sph.Fail):
            sph.ffmpegtool_resolve(LINK, timeout_s=1)
        once.assert_called_once()
        sleep.assert_not_called()

    def test_paste_media_rejects_spoofed_hosts_schemes_and_credentials(self):
        for value in ("https://finder.video.qq.com.example.org/video.mp4",
                      "http://127.0.0.1/video.mp4?tag=finder.video.qq.com",
                      "https://finder.video.qq.com@evil.example/video.mp4",
                      "file:///tmp/finder.video.qq.com.mp4", "http://finder.video.qq.com/video.mp4",
                      "https://finder.video.qq.com:444/video.mp4", "https://finder.video.qq.com/video\n.mp4", None):
            with self.subTest(value=value):
                self.assertIsNone(sph._p2v_media_url(value))
        self.assertEqual(sph._p2v_media_url(MEDIA + "?token=a&sig=b"), MEDIA + "?token=a&sig=b")

    def test_paste_html_handles_metadata_and_encoded_fallback_links(self):
        parsed = sph._PasteHTML()
        parsed.feed(json.loads(success_payload())["data"]["html"])
        self.assertEqual(parsed.urls, {"h264": MEDIA})
        parsed = sph._PasteHTML()
        parsed.feed('<a data-download-url="' + MEDIA + '?a=1&amp;b=2"></a>')
        self.assertEqual(parsed.urls["video"], MEDIA + "?a=1&b=2")

    def test_paste_metadata_filters_malformed_formats_and_untrusted_cover(self):
        parsed = sph._PasteHTML()
        meta = {"formats": [None, "bad", {"url": "https://evil.example/finder.video.qq.com"}],
                "cover": "https://127.0.0.1/secret", "title": "fixture"}
        parsed.feed("<div data-parse-meta='" + html.escape(json.dumps(meta), quote=True) + "'></div>")
        self.assertEqual(parsed.urls, {})
        self.assertNotIn("cover_url", parsed.metadata)

    def test_paste_transient_processing_error_is_retried(self):
        failed = json.dumps({"code": 1, "message": "processing failed"}).encode()
        with mock.patch.object(sph, "http", side_effect=[(200, {}, failed), (200, {}, success_payload())]) as request, \
                mock.patch.object(sph.time, "sleep"):
            urls, _ = sph.paste2vid_resolve(LINK)
        self.assertEqual(urls, {"h264": MEDIA})
        self.assertEqual(request.call_count, 2)

    def test_paste_quota_error_never_retries_or_logs_in(self):
        failed = json.dumps({"code": 1, "message": "额度用完"}).encode()
        with mock.patch.object(sph, "http", return_value=(200, {}, failed)) as request, self.assertRaises(sph.ResolverBlocked):
            sph.paste2vid_resolve(LINK)
        request.assert_called_once()

    def test_paste_http_error_body_is_handled_and_rate_limit_stops(self):
        error = urllib.error.HTTPError("https://paste2vid.com/api/parse2", 429, "limited", {}, io.BytesIO(b"[]"))
        with mock.patch.object(sph, "http", side_effect=error) as request, self.assertRaises(sph.ResolverBlocked):
            sph.paste2vid_resolve(LINK)
        request.assert_called_once()

    def test_paste_non_object_json_is_a_controlled_failure(self):
        with mock.patch.object(sph, "http", return_value=(200, {}, b"[]")), self.assertRaises(sph.Fail):
            sph.paste2vid_resolve(LINK, tries=1)

    def test_paste_redirect_and_initial_host_cannot_escape_allowlist(self):
        request = urllib.request.Request(MEDIA)
        handler = sph.SafeRedirect(sph.P2V_MEDIA_HOSTS)
        with self.assertRaises(sph.Fail):
            handler.redirect_request(request, None, 302, "", {}, "https://evil.example/video")
        with self.assertRaises(sph.Fail):
            sph.open_response(urllib.request.Request("https://evil.example/video"), 1, sph.P2V_MEDIA_HOSTS)
        redirected = handler.redirect_request(request, None, 302, "", {}, MEDIA + "?next=1")
        self.assertEqual(redirected.full_url, MEDIA + "?next=1")

    def test_paste_backend_requires_its_own_explicit_consent(self):
        with mock.patch.object(sph, "paste2vid_resolve") as paste:
            code, result = self.run_main(LINK, "--backend", "paste2vid", "--out", str(self.root))
        self.assertEqual(code, 2)
        self.assertFalse(result["ok"])
        paste.assert_not_called()

    def test_old_third_party_flag_does_not_enable_new_provider(self):
        with mock.patch.object(sph, "public_metadata", return_value={}), \
                mock.patch.object(sph, "ffmpegtool_resolve", side_effect=sph.Fail("busy")), \
                mock.patch.object(sph, "paste2vid_resolve") as paste:
            code, _ = self.run_main(LINK, "--allow-third-party", "--out", str(self.root))
        self.assertEqual(code, 3)
        paste.assert_not_called()

    def test_main_fallback_shares_budget_and_enforces_media_host(self):
        clock, budgets, downloads = [0], [], []
        def ff(url, timeout_s):
            self.assertEqual(url, LINK)
            budgets.append(timeout_s)
            clock[0] += 4
            raise sph.Fail("busy")
        def paste(url, timeout_s):
            self.assertEqual(url, LINK)
            budgets.append(timeout_s)
            return {"h264": MEDIA}, {}
        def download(url, dest, **kwargs):
            downloads.append(kwargs)
            dest.write_bytes(MP4)
        with mock.patch.object(sph.time, "monotonic", side_effect=lambda: clock[0]), \
                mock.patch.object(sph, "public_metadata", return_value={}), \
                mock.patch.object(sph, "ffmpegtool_resolve", side_effect=ff), \
                mock.patch.object(sph, "paste2vid_resolve", side_effect=paste), \
                mock.patch.object(sph, "download", side_effect=download), \
                mock.patch.object(sph, "probe", return_value={"duration": 1, "width": 160, "height": 120, "audio_codec": None}):
            code, result = self.run_main("备注 " + LINK, "--allow-third-party", "--allow-paste2vid",
                                         "--resolve-timeout", "10", "--frames", "0", "--out", str(self.root))
        self.assertEqual(code, 0)
        self.assertEqual(result["backend"], "paste2vid")
        self.assertEqual(budgets, [10, 6])
        self.assertEqual(downloads[0]["allowed_hosts"], sph.P2V_MEDIA_HOSTS)

    def test_exhausted_resolution_budget_never_reads_credentials(self):
        clock = [0]
        def failed(url, timeout_s):
            clock[0] += 2
            raise sph.Fail("busy")
        with mock.patch.object(sph.time, "monotonic", side_effect=lambda: clock[0]), \
                mock.patch.object(sph, "public_metadata", return_value={}), \
                mock.patch.object(sph, "ffmpegtool_resolve", side_effect=failed), \
                mock.patch.object(sph, "paste2vid_resolve") as paste, \
                mock.patch.object(sph, "load_yuanbao_auth") as auth:
            code, _ = self.run_main(LINK, "--allow-third-party", "--allow-paste2vid", "--allow-saved-auth",
                                    "--resolve-timeout", "1", "--out", str(self.root))
        self.assertEqual(code, 3)
        paste.assert_not_called()
        auth.assert_not_called()

    def test_slow_first_backend_leaves_time_for_enabled_fallback(self):
        clock = [0]
        def slow_ff(url, timeout_s):
            clock[0] += timeout_s
            raise sph.Fail("first backend timed out")
        with mock.patch.object(sph.time, "monotonic", side_effect=lambda: clock[0]), \
                mock.patch.object(sph, "public_metadata", return_value={}), \
                mock.patch.object(sph, "ffmpegtool_resolve", side_effect=slow_ff), \
                mock.patch.object(sph, "paste2vid_resolve", return_value=({"h264": MEDIA}, {})) as paste, \
                mock.patch.object(sph, "download", side_effect=lambda u, p, **kw: p.write_bytes(MP4)), \
                mock.patch.object(sph, "probe", return_value={"duration": 1, "width": 160, "height": 120, "audio_codec": None}):
            code, _ = self.run_main(LINK, "--allow-third-party", "--allow-paste2vid", "--frames", "0", "--out", str(self.root))
        self.assertEqual(code, 0)
        self.assertLess(clock[0], 180)
        self.assertGreater(paste.call_args.kwargs["timeout_s"], 0)


if __name__ == "__main__":
    unittest.main()
