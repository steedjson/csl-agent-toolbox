"""Offline regression tests. No network, browser, model or real credentials required."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import urllib.request

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
spec = importlib.util.spec_from_file_location("sph_fetch", SCRIPTS / "sph_fetch.py")
sph = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sph)
LINK = "https://weixin.qq.com/sph/AbCd_123"
MEDIA = "https://finder.video.qq.com/test.mp4"
MP4 = b"\x00\x00\x00\x18ftypisom" + b"x" * 80


class Response:
    status = 200

    def __init__(self, data, headers=None):
        self.stream = io.BytesIO(data)
        self.headers = headers or {"Content-Type": "video/mp4"}

    def read1(self, n):
        return self.stream.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.stream.close()


class ReaderTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        # Any unexpected real request fails instead of leaving the test sandbox.
        network = mock.patch.object(urllib.request.OpenerDirector, "open",
                                    side_effect=AssertionError("Unexpected network access"))
        network.start()
        self.addCleanup(network.stop)

    def run_main(self, *args):
        stdout = io.StringIO()
        with mock.patch.object(sys, "argv", ["sph_fetch.py", *args]), \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(io.StringIO()):
            code = sph.main()
        return code, json.loads(stdout.getvalue().splitlines()[-1])

    def arguments(self, *extra):
        return [LINK, "--out", str(self.root), "--backend", "ffmpegtool",
                "--allow-third-party", *extra]

    def test_extracts_only_canonical_link_from_share_text(self):
        link = sph.extract_link("私有备注 " + LINK + "?tracking=1 另外一些文案")
        self.assertEqual(link["url"], LINK)

    def test_channels_id_cannot_escape_output_root(self):
        for sid in ("../../escape", "%2e%2e%2fescape", "", "a/b", "a%5Cb", "a&id=b"):
            with self.subTest(sid=sid), self.assertRaises(sph.Fail):
                sph.extract_link("https://channels.weixin.qq.com/example?id=" + sid)

    def test_rejects_insecure_or_spoofed_inputs(self):
        for url in ("http://weixin.qq.com/sph/abc", "https://weixin.qq.com.evil/sph/abc",
                    "https://user@weixin.qq.com/sph/abc", "https://weixin.qq.com:444/sph/abc",
                    "https://weixin.qq.com/sph/a/../../escape"):
            with self.subTest(url=url), self.assertRaises(sph.Fail):
                sph.extract_link(url)

    def test_valid_channels_id_and_eid(self):
        self.assertEqual(sph.extract_link("https://channels.weixin.qq.com/example?id=AbCd_123")["url"], LINK)
        eid = sph.extract_link("https://channels.weixin.qq.com/example?eid=some-value")
        self.assertRegex(eid["code"], r"^feed-[a-f0-9]{16}$")

    def test_each_run_uses_fresh_directory(self):
        first = sph.make_output(self.root, "same")
        (first / "video.mp4").write_bytes(b"old")
        second = sph.make_output(self.root, "same")
        self.assertNotEqual(first, second)
        self.assertFalse((second / "video.mp4").exists())
        self.assertEqual((first / "video.mp4").read_bytes(), b"old")

    def test_output_symlink_escape_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            (self.root / "escape").symlink_to(outside)
            with self.assertRaises(sph.Fail):
                sph.make_output(self.root, "escape")

    def test_no_route_enabled_makes_no_request_or_output_directory(self):
        with mock.patch.object(sph, "public_metadata") as public:
            code, result = self.run_main(LINK, "--out", str(self.root / "output"))
        self.assertEqual(code, 2)
        self.assertFalse(result["ok"])
        public.assert_not_called()
        self.assertFalse((self.root / "output").exists())

    def test_yuanbao_requires_explicit_credentials_selection(self):
        with mock.patch.object(sph, "load_yuanbao_auth") as auth:
            code, _ = self.run_main(LINK, "--backend", "yuanbao")
        self.assertEqual(code, 2)
        auth.assert_not_called()

    def test_old_video_does_not_turn_failed_resolution_into_success(self):
        old = sph.make_output(self.root, "AbCd_123")
        (old / "video.mp4").write_bytes(b"old")
        with mock.patch.object(sph, "public_metadata", return_value={}), \
                mock.patch.object(sph, "ffmpegtool_resolve", side_effect=sph.Fail("offline")), \
                mock.patch.object(sph, "probe") as probe:
            code, result = self.run_main(*self.arguments())
        self.assertEqual(code, 3)
        self.assertFalse(result["ok"])
        self.assertNotEqual(Path(result["out"]), old)
        probe.assert_not_called()
        self.assertEqual((old / "video.mp4").read_bytes(), b"old")
        metadata = json.loads((Path(result["out"]) / "metadata.json").read_text())
        self.assertFalse(metadata["ok"])

    def test_download_failure_is_not_success(self):
        with mock.patch.object(sph, "public_metadata", return_value={}), \
                mock.patch.object(sph, "ffmpegtool_resolve", return_value={"h264": MEDIA}), \
                mock.patch.object(sph, "download", side_effect=sph.Fail("download failed")), \
                mock.patch.object(sph, "probe") as probe:
            code, result = self.run_main(*self.arguments())
        self.assertEqual(code, 3)
        self.assertEqual(result["stage"], "download")
        probe.assert_not_called()

    def test_third_party_gets_only_url_and_no_implicit_auth_fallback(self):
        args = self.arguments()
        args[0] = "秘密备注 " + LINK + "?track=1 后续文案"
        with mock.patch.object(sph, "public_metadata", return_value={}), \
                mock.patch.object(sph, "ffmpegtool_resolve", side_effect=sph.Fail("offline")) as resolve, \
                mock.patch.object(sph, "load_yuanbao_auth") as auth:
            code, _ = self.run_main(*args)
        self.assertEqual(code, 3)
        self.assertEqual(resolve.call_args.args, (LINK,))
        self.assertGreater(resolve.call_args.kwargs["timeout_s"], 0)
        auth.assert_not_called()

    def test_mp4_validation_reads_header_without_loading_whole_file(self):
        dest = self.root / "video.mp4"
        with mock.patch.object(sph, "open_response", return_value=Response(MP4)), \
                mock.patch.object(Path, "read_bytes", side_effect=AssertionError("whole-file read")):
            sph.download(MEDIA, dest, expect_mp4=True)
        self.assertEqual(dest.read_bytes(), MP4)
        self.assertFalse((self.root / "video.mp4.part").exists())

    def test_streaming_size_limit_cleans_partial_file(self):
        dest = self.root / "video.mp4"
        with mock.patch.object(sph, "open_response", return_value=Response(MP4)), \
                self.assertRaisesRegex(sph.Fail, "大小"):
            sph.download(MEDIA, dest, expect_mp4=True, max_bytes=12)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_content_length_limit_cleans_partial_file(self):
        response = Response(MP4, {"Content-Length": "1000"})
        with mock.patch.object(sph, "open_response", return_value=response), \
                self.assertRaisesRegex(sph.Fail, "大小"):
            sph.download(MEDIA, self.root / "video.mp4", max_bytes=100)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_non_mp4_content_and_wrong_headers_are_rejected(self):
        for body, headers in ((b"bad media", {"Content-Type": "application/octet-stream"}),
                              (MP4, {"Content-Type": "text/html"})):
            with self.subTest(headers=headers), \
                    mock.patch.object(sph, "open_response", return_value=Response(body, headers)), \
                    self.assertRaises(sph.Fail):
                sph.download(MEDIA, self.root / "video.mp4", expect_mp4=True)
            self.assertEqual(list(self.root.iterdir()), [])

    def test_timeout_cleans_partial_file(self):
        with mock.patch.object(sph, "open_response", return_value=Response(MP4)), \
                mock.patch.object(sph.time, "monotonic", side_effect=[0, 301]), \
                self.assertRaisesRegex(sph.Fail, "时限"):
            sph.download(MEDIA, self.root / "video.mp4", timeout=300)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_sensitive_redirect_cannot_change_origin(self):
        request = urllib.request.Request("https://yuanbao.tencent.com/api/test", headers={"Cookie": "hy_token=dummy"})
        with self.assertRaises(sph.Fail):
            sph.SafeRedirect().redirect_request(request, None, 302, "", {}, "https://other.example/test")
        with self.assertRaises(sph.Fail):
            sph.SafeRedirect().redirect_request(request, None, 302, "", {}, "http://yuanbao.tencent.com/test")

    def test_credentials_created_private_and_outside_source(self):
        target = self.root / "config/auth.json"
        old = os.umask(0)
        try:
            sph.save_auth(target, {"cookie": "hy_user=dummy; hy_token=dummy"})
        finally:
            os.umask(old)
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        self.assertFalse(sph.DEFAULT_COOKIE.is_relative_to(SCRIPTS))
        self.assertEqual(sph.load_yuanbao_auth(target)["cookie"], "hy_user=dummy; hy_token=dummy")
        self.assertEqual(list(target.parent.iterdir()), [target])

    def test_credential_symlink_not_overwritten(self):
        original = self.root / "original"
        original.write_text("unchanged")
        link = self.root / "auth.json"
        link.symlink_to(original)
        with self.assertRaises(sph.Fail):
            sph.save_auth(link, {"cookie": "dummy"})
        self.assertEqual(original.read_text(), "unchanged")

    def test_silent_video_skips_asr_and_produces_frames(self):
        def downloaded(url, path, **kwargs):
            path.write_bytes(MP4)

        media = {"duration": 2.0, "width": 640, "height": 480, "video_codec": "h264", "audio_codec": None}
        with mock.patch.object(sph, "public_metadata", return_value={}), \
                mock.patch.object(sph, "ffmpegtool_resolve", return_value={"h264": MEDIA}), \
                mock.patch.object(sph, "download", side_effect=downloaded), \
                mock.patch.object(sph, "probe", return_value=media), \
                mock.patch.object(sph, "transcribe") as asr, \
                mock.patch.object(sph, "extract_frames", return_value=["frame.jpg"]) as frames:
            code, result = self.run_main(*self.arguments())
        self.assertEqual(code, 0)
        self.assertTrue(result["ok"])
        self.assertEqual(result["asr"], "skipped")
        asr.assert_not_called()
        self.assertEqual(frames.call_args.args[2], 4)
        meta = json.loads((Path(result["out"]) / "metadata.json").read_text())
        self.assertEqual(meta["asr"]["reason"], "视频无音轨")
        self.assertTrue((Path(result["out"]) / "summary_input.md").is_file())

    def test_probe_failure_preserves_failure_metadata(self):
        with mock.patch.object(sph, "public_metadata", return_value={}), \
                mock.patch.object(sph, "ffmpegtool_resolve", return_value={"h264": MEDIA}), \
                mock.patch.object(sph, "download", side_effect=lambda u, p, **kw: p.write_bytes(MP4)), \
                mock.patch.object(sph, "probe", side_effect=subprocess.TimeoutExpired("ffprobe", 30)):
            code, result = self.run_main(*self.arguments())
        self.assertEqual(code, 4)
        self.assertFalse(result["ok"])
        self.assertEqual(result["stage"], "probe")
        self.assertTrue((Path(result["out"]) / "metadata.json").exists())

    def test_successful_transcription_and_asr_failure_are_distinct(self):
        media = {"duration": 1.0, "width": 640, "height": 480, "audio_codec": "aac"}
        segments = [{"start": 0.0, "end": 1.0, "text": "测试正文"}]
        for failure in (False, True):
            with self.subTest(failure=failure), \
                    mock.patch.object(sph, "public_metadata", return_value={}), \
                    mock.patch.object(sph, "ffmpegtool_resolve", return_value={"h264": MEDIA}), \
                    mock.patch.object(sph, "download", side_effect=lambda u, p, **kw: p.write_bytes(MP4)), \
                    mock.patch.object(sph, "probe", return_value=media), \
                    mock.patch.object(sph.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)), \
                    mock.patch.object(sph, "transcribe", side_effect=sph.Fail("model unavailable") if failure else None,
                                      return_value=(segments, {"language": "zh"})):
                code, result = self.run_main(*self.arguments("--frames", "0"))
            out = Path(result["out"])
            self.assertTrue((out / "video.mp4").exists())
            if failure:
                self.assertEqual(code, 5)
                self.assertFalse(result["ok"])
                self.assertTrue(result["video_ok"])
                self.assertEqual(result["status"], "partial")
                self.assertEqual(result["asr"], "failed")
                self.assertIn("转写失败", (out / "summary_input.md").read_text())
                self.assertIn("转写失败", (out / "transcript.txt").read_text())
            else:
                self.assertEqual(code, 0)
                self.assertTrue(result["ok"])
                self.assertIn("测试正文", (out / "transcript.txt").read_text())

    def test_duration_limit_stops_before_audio_processing(self):
        with mock.patch.object(sph, "public_metadata", return_value={}), \
                mock.patch.object(sph, "ffmpegtool_resolve", return_value={"h264": MEDIA}), \
                mock.patch.object(sph, "download", side_effect=lambda u, p, **kw: p.write_bytes(MP4)), \
                mock.patch.object(sph, "probe", return_value={"duration": 7201}), \
                mock.patch.object(sph, "transcribe") as asr:
            code, result = self.run_main(*self.arguments())
        self.assertEqual(code, 4)
        self.assertEqual(result["stage"], "probe")
        asr.assert_not_called()

    def test_explicitly_enabled_yuanbao_fallback_works(self):
        args = self.arguments("--cookie", str(self.root / "explicit-cookie.json"), "--no-asr", "--frames", "0")
        args[args.index("ffmpegtool")] = "auto"
        media = {"duration": 1.0, "width": 640, "height": 480, "audio_codec": "aac"}
        with mock.patch.object(sph, "public_metadata", return_value={}), \
                mock.patch.object(sph, "ffmpegtool_resolve", side_effect=sph.Fail("offline")), \
                mock.patch.object(sph, "load_yuanbao_auth", return_value={"cookie": "dummy"}) as auth, \
                mock.patch.object(sph, "yuanbao_resolve", return_value=({"h264": MEDIA}, {"author": "示例作者"})), \
                mock.patch.object(sph, "download", side_effect=lambda u, p, **kw: p.write_bytes(MP4)), \
                mock.patch.object(sph, "probe", return_value=media):
            code, result = self.run_main(*args)
        self.assertEqual(code, 0)
        self.assertEqual(result["backend"], "yuanbao")
        auth.assert_called_once_with(self.root / "explicit-cookie.json")

    def test_auth_exception_does_not_leak_credentials(self):
        secret = "sample-secret-never-log"
        with mock.patch.object(sph, "public_metadata", return_value={}), \
                mock.patch.object(sph, "load_yuanbao_auth", return_value={"cookie": secret}), \
                mock.patch.object(sph, "yuanbao_resolve", side_effect=ValueError("bad header " + secret)):
            code, result = self.run_main(LINK, "--backend", "yuanbao", "--allow-saved-auth", "--out", str(self.root))
        self.assertEqual(code, 3)
        self.assertNotIn(secret, json.dumps(result))
        self.assertNotIn(secret, (Path(result["out"]) / "metadata.json").read_text())

    def test_invalid_probe_result_rejected(self):
        result = subprocess.CompletedProcess([], 0, stdout="{}", stderr="")
        with mock.patch.object(sph.subprocess, "run", return_value=result), self.assertRaises(sph.Fail):
            sph.probe(self.root / "video.mp4")

    def test_command_help_requires_no_browser_or_models(self):
        for script in ("sph_fetch.py", "yuanbao_login.py"):
            result = subprocess.run([sys.executable, str(SCRIPTS / script), "--help"], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
        result = subprocess.run(["bash", str(SCRIPTS / "setup.sh"), "--help"], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
