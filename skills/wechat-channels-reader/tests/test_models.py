"""Offline transport/cache regressions for the revised model downloader."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import urllib.request

from test_sph_fetch import sph, Response, SCRIPTS, LINK, MEDIA, MP4


def digest(data):
    return hashlib.sha256(data).hexdigest()


class Interrupted(Response):
    def read1(self, n):
        if not self.stream.tell():
            return self.stream.read(n)
        raise TimeoutError("simulated disconnect")


class ModelTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.payload = {"config.json": b"{}", "model.bin": b"weights",
                        "tokenizer.json": b"{}", "vocabulary.txt": b"tokens"}
        self.files = {n: (len(v), digest(v)) for n, v in self.payload.items()}
        for patch in (
            mock.patch.object(urllib.request.OpenerDirector, "open", side_effect=AssertionError("Network forbidden")),
            mock.patch.object(sph, "MODELS_DIR", self.root / "models"),
            mock.patch.dict(sph.WHISPER_FILES, {"tiny": self.files}),
            mock.patch.dict(os.environ, {"HF_HOME": str(self.root / "hf"), "HF_HUB_CACHE": "",
                                          "HF_ENDPOINT": "", "WCR_DL_TRIES": "3", "WCR_MODEL_SOURCE": "auto"}),
            mock.patch.object(sph.time, "sleep"),
        ):
            patch.start()
            self.addCleanup(patch.stop)

    def test_successful_hash_verified_download(self):
        dest = self.root / "model.bin"
        with mock.patch.object(sph, "open_response", return_value=Response(b"abcd")):
            sph.fetch_file(["https://example.com/model"], dest, 4, digest(b"abcd"))
        self.assertEqual(dest.read_bytes(), b"abcd")
        self.assertFalse(dest.with_name("model.bin.part").exists())

    def test_disconnect_resumes_from_exact_byte(self):
        dest = self.root / "model.bin"
        tail = Response(b"cd", {"Content-Range": "bytes 2-3/4"})
        tail.status = 206
        with mock.patch.object(sph, "open_response", side_effect=[Interrupted(b"ab"), tail]) as opened:
            sph.fetch_file(["https://example.com/model"], dest, 4, digest(b"abcd"), tries=2)
        self.assertEqual(opened.call_args_list[1].args[0].get_header("Range"), "bytes=2-")
        self.assertEqual(dest.read_bytes(), b"abcd")

    def test_ignored_range_restarts_without_appending(self):
        dest = self.root / "model.bin"
        dest.with_name("model.bin.part").write_bytes(b"ab")
        with mock.patch.object(sph, "open_response", return_value=Response(b"abcd")):
            sph.fetch_file(["https://example.com/model"], dest, 4, digest(b"abcd"), tries=1)
        self.assertEqual(dest.read_bytes(), b"abcd")

    def test_wrong_range_never_publishes(self):
        for header in ("bytes 1-3/4", "bytes 2-3/5", "garbage"):
            with self.subTest(header=header):
                dest = self.root / "model.bin"
                part = dest.with_name("model.bin.part")
                part.write_bytes(b"ab")
                response = Response(b"cd", {"Content-Range": header})
                response.status = 206
                with mock.patch.object(sph, "open_response", return_value=response), self.assertRaises(sph.ModelError):
                    sph.fetch_file(["https://example.com/model"], dest, 4, digest(b"abcd"), tries=1)
                self.assertFalse(dest.exists())
                self.assertEqual(part.read_bytes(), b"ab")

    def test_range_body_must_not_exceed_declared_end(self):
        dest = self.root / "model.bin"
        part = dest.with_name("model.bin.part")
        part.write_bytes(b"ab")
        response = Response(b"cd", {"Content-Range": "bytes 2-2/4"})
        response.status = 206
        with mock.patch.object(sph, "open_response", return_value=response), self.assertRaises(sph.ModelError):
            sph.fetch_file(["https://example.com/model"], dest, 4, digest(b"abcd"), tries=1)
        self.assertFalse(dest.exists())

    def test_complete_corrupt_part_is_redownloaded(self):
        dest = self.root / "model.bin"
        dest.with_name("model.bin.part").write_bytes(b"bad!")
        with mock.patch.object(sph, "open_response", return_value=Response(b"abcd")) as opened:
            sph.fetch_file(["https://example.com/model"], dest, 4, digest(b"abcd"), tries=1)
        self.assertEqual(dest.read_bytes(), b"abcd")
        self.assertIsNone(opened.call_args.args[0].get_header("Range"))

    def test_same_size_corrupt_download_is_not_accepted(self):
        dest = self.root / "model.bin"
        with mock.patch.object(sph, "open_response", return_value=Response(b"bad!")), self.assertRaises(sph.ModelError):
            sph.fetch_file(["https://example.com/model"], dest, 4, digest(b"abcd"), tries=1)
        self.assertFalse(dest.exists())
        self.assertFalse(dest.with_name("model.bin.part").exists())

    def test_interrupted_part_survives_for_next_run(self):
        dest = self.root / "model.bin"
        with mock.patch.object(sph, "open_response", return_value=Interrupted(b"ab")), self.assertRaises(sph.ModelError):
            sph.fetch_file(["https://example.com/model"], dest, 4, digest(b"abcd"), tries=1)
        self.assertFalse(dest.exists())
        self.assertEqual(dest.with_name("model.bin.part").read_bytes(), b"ab")

    def test_missing_checksum_rejected_without_request(self):
        with mock.patch.object(sph, "open_response") as opened, self.assertRaises(sph.ModelError):
            sph.fetch_file(["https://example.com/model"], self.root / "model.bin", 4, None)
        opened.assert_not_called()

    def test_expired_budget_does_not_start_request(self):
        with mock.patch.object(sph, "open_response") as opened, self.assertRaises(sph.ModelError):
            sph.fetch_file(["https://example.com/model"], self.root / "model.bin", 4, digest(b"abcd"), deadline=0)
        opened.assert_not_called()

    def test_part_symlink_never_overwrites_external_file(self):
        outside = self.root / "outside"
        outside.write_bytes(b"unchanged")
        dest = self.root / "model.bin"
        dest.with_name("model.bin.part").symlink_to(outside)
        with self.assertRaises(sph.ModelError):
            sph.fetch_file(["https://example.com/model"], dest, 4, digest(b"abcd"))
        self.assertEqual(outside.read_bytes(), b"unchanged")

    def write_model(self, directory):
        directory.mkdir(parents=True, exist_ok=True)
        for name, data in self.payload.items():
            (directory / name).write_bytes(data)

    def test_complete_marker_does_not_bypass_hash_verification(self):
        directory = sph.MODELS_DIR / "faster-whisper-tiny"
        self.write_model(directory)
        (directory / ".complete").write_text("{}")
        (directory / "model.bin").write_bytes(b"corrupt")
        with mock.patch.object(sph, "fetch_file", side_effect=sph.ModelError("offline")) as fetched, \
                self.assertRaises(sph.ModelError):
            sph.whisper_model_path("tiny", source="hf")
        fetched.assert_called()

    def test_valid_hf_cache_is_read_only_and_hash_checked(self):
        cache = self.root / "hf/hub/models--Systran--faster-whisper-tiny/snapshots/revision"
        self.write_model(cache)
        self.assertEqual(sph._hf_cache_dir("tiny"), cache)
        (cache / "model.bin").write_bytes(b"corrupt")
        self.assertIsNone(sph._hf_cache_dir("tiny"))

    def test_fresh_whisper_model_download_and_verified_cache_reuse(self):
        def respond(request, timeout):
            name = request.full_url.rsplit("/", 1)[-1]
            return Response(self.payload[name])
        with mock.patch.object(sph, "open_response", side_effect=respond) as opened:
            directory = sph.whisper_model_path("tiny", source="hf")
        self.assertEqual(opened.call_count, 4)
        self.assertTrue((directory / ".complete").exists())
        with mock.patch.object(sph, "open_response", side_effect=AssertionError("cached model must not download")):
            self.assertEqual(sph.whisper_model_path("tiny"), directory)

    def test_custom_local_model_does_not_download_or_require_standard_weight_size(self):
        directory = self.root / "custom"
        self.write_model(directory)
        (directory / "model.bin").write_bytes(b"custom quantized weights")
        with mock.patch.object(sph, "fetch_file") as fetched:
            self.assertEqual(sph.whisper_model_path("tiny", directory), directory)
        fetched.assert_not_called()

    def test_shared_deadline_stops_source_fallback(self):
        clock = [0]
        def failed(*args, **kwargs):
            clock[0] = 2
            raise sph.ModelError("simulated stall")
        with mock.patch.object(sph.time, "monotonic", side_effect=lambda: clock[0]), \
                mock.patch.object(sph, "fetch_file", side_effect=failed) as fetched, self.assertRaises(sph.ModelError):
            sph.whisper_model_path("tiny", timeout=1)
        self.assertEqual(fetched.call_count, 1)

    def test_duplicate_concurrent_model_preparation_rejected(self):
        directory = self.root / "locked"
        with sph._model_lock(directory):
            with self.assertRaises(sph.ModelError):
                with sph._model_lock(directory):
                    self.fail("Second writer entered")

    def test_manifest_path_traversal_and_missing_hash_rejected(self):
        for name in ("../escape", "nested/../../escape", "/tmp/escape", "C:/escape", "a\\escape", "./model.pt"):
            body = {"Code": 200, "Data": {"Files": [{"Type": "blob", "Path": name, "Size": 4, "Sha256": digest(b"abcd")}]}}
            with self.subTest(name=name), mock.patch.object(sph, "http", return_value=(200, {}, json.dumps(body).encode())), \
                    self.assertRaises(sph.ModelError):
                sph.ms_manifest("iic/demo")
        with self.assertRaises(sph.ModelError):
            sph._manifest_files({"model.pt": (4, None)})

    def test_model_parent_symlink_rejected(self):
        base = self.root / "models"
        base.mkdir()
        (base / "alias").symlink_to(self.root)
        with self.assertRaises(sph.ModelError):
            sph._model_file(base, "alias/model.pt")

    def test_funasr_marker_without_verified_files_does_not_skip_manifest(self):
        directory = sph.MODELS_DIR / "funasr/demo"
        directory.mkdir(parents=True)
        (directory / ".complete").write_text('{"repo":"iic/demo"}')
        with mock.patch.dict(sph.FUNASR_REPOS, {"asr": "iic/demo"}, clear=True), \
                mock.patch.object(sph, "ms_manifest", side_effect=sph.ModelError("offline")) as manifest, \
                self.assertRaises(sph.ModelError):
            sph.funasr_model_paths()
        manifest.assert_called_once()

    def test_funasr_verified_cache_works_offline(self):
        directory = sph.MODELS_DIR / "funasr/demo"
        directory.mkdir(parents=True)
        (directory / "model.pt").write_bytes(b"abcd")
        files = {"model.pt": (4, digest(b"abcd"))}
        (directory / ".complete").write_text(json.dumps({"repo": "iic/demo", "files": files}))
        with mock.patch.dict(sph.FUNASR_REPOS, {"asr": "iic/demo"}, clear=True), \
                mock.patch.object(sph, "ms_manifest") as manifest:
            self.assertEqual(sph.funasr_model_paths()["asr"], directory)
        manifest.assert_not_called()

    def test_funasr_fresh_download_filters_code_and_caches_all_roles(self):
        payload = {"model.pt": b"weights", "config.yaml": b"config", "nested/helper.py": b"code"}
        manifest = {n: (len(v), digest(v)) for n, v in payload.items()}
        with mock.patch.object(sph, "ms_manifest", return_value=manifest), \
                mock.patch.object(sph, "open_response", side_effect=lambda r, t: Response(payload[r.full_url.rsplit('/', 1)[-1]])) as opened:
            paths = sph.funasr_model_paths("modelscope")
        self.assertEqual(set(paths), {"asr", "vad", "punc"})
        self.assertEqual(opened.call_count, 6)
        for directory in paths.values():
            self.assertEqual((directory / "model.pt").read_bytes(), b"weights")
            self.assertFalse((directory / "nested/helper.py").exists())
        with mock.patch.object(sph, "ms_manifest", side_effect=AssertionError("Cache must be usable offline")):
            self.assertEqual(sph.funasr_model_paths(), paths)

    def run_main(self, *arguments):
        output = io.StringIO()
        with mock.patch.object(sys, "argv", ["sph_fetch.py", *arguments]), \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
            code = sph.main()
        return code, json.loads(output.getvalue().splitlines()[-1])

    def test_download_only_cli_keeps_model_options_and_failure_status(self):
        for failure in (False, True):
            with self.subTest(failure=failure), \
                    mock.patch.object(sph, "whisper_model_path", return_value=self.root,
                                      side_effect=sph.ModelError("unavailable") if failure else None) as prepare:
                code, result = self.run_main("--download-model", "tiny", "--model-source", "hf", "--model-timeout", "7")
            self.assertEqual(code, 4 if failure else 0)
            self.assertEqual(result["ok"], not failure)
            prepare.assert_called_once_with("tiny", None, "hf", 7)

    def test_main_preserves_funasr_engine_model_and_budget(self):
        media = {"duration": 1.0, "width": 640, "height": 480, "audio_codec": "aac"}
        with mock.patch.object(sph, "public_metadata", return_value={}), \
                mock.patch.object(sph, "ffmpegtool_resolve", return_value={"h264": MEDIA}), \
                mock.patch.object(sph, "download", side_effect=lambda u, p, **kw: p.write_bytes(MP4)), \
                mock.patch.object(sph, "probe", return_value=media), \
                mock.patch.object(sph.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)), \
                mock.patch.object(sph, "transcribe_funasr", return_value=([], {"language": "zh", "model": "iic/fixture"})) as asr, \
                mock.patch.object(sph, "transcribe") as whisper:
            code, result = self.run_main(LINK, "--out", str(self.root), "--allow-third-party", "--asr", "funasr",
                                         "--model-source", "modelscope", "--model-timeout", "7", "--frames", "0")
        self.assertEqual(code, 0)
        whisper.assert_not_called()
        self.assertEqual(asr.call_args.args[1:], ("modelscope", 7))
        meta = json.loads((Path(result["out"]) / "metadata.json").read_text())
        self.assertEqual(meta["asr"]["model"], "iic/fixture")

    def test_funasr_unsupported_source_is_not_silently_ignored(self):
        with self.assertRaises(sph.ModelError):
            sph.funasr_model_paths("hf")

    def test_source_endpoint_does_not_accept_embedded_credentials(self):
        with mock.patch.dict(os.environ, {"HF_ENDPOINT": "https://user:secret@example.com"}), self.assertRaises(sph.Fail):
            sph._sources("auto")

    def test_cookie_import_drops_unrelated_domains_and_unknown_scope(self):
        file = self.root / "auth.json"
        file.write_text(json.dumps({"cookies": [
            {"name": "hy_user", "value": "dummy", "domain": ".tencent.com"},
            {"name": "hy_token", "value": "dummy", "domain": "yuanbao.tencent.com"},
            {"name": "unrelated_secret", "value": "never-send", "domain": "other.example"},
            {"name": "no_domain_secret", "value": "never-send"},
        ]}))
        auth = sph.load_yuanbao_auth(file)
        self.assertEqual(auth["cookie"], "hy_user=dummy; hy_token=dummy")
        self.assertNotIn("never-send", auth["cookie"])

    def test_download_environment_error_is_runtime_validation_not_import_crash(self):
        with mock.patch.dict(os.environ, {"WCR_DL_TRIES": "invalid"}), self.assertRaises(sph.ModelError):
            sph.fetch_file(["https://example.com/model"], self.root / "model.bin", 4, digest(b"abcd"))

    def test_setup_invalid_arguments_make_no_environment(self):
        env = os.environ.copy()
        env["WCR_VENV"] = str(self.root / "venv")
        for args in (["--model"], ["--model-source", "bad"], ["--model-timeout", "0"]):
            result = subprocess.run(["bash", str(SCRIPTS / "setup.sh"), *args], capture_output=True, env=env, timeout=10)
            self.assertEqual(result.returncode, 2, result.stderr)
        self.assertFalse((self.root / "venv").exists())

    def test_setup_quoted_path_and_partial_model_status_without_installing(self):
        scripts = self.root / "folder'quoted/scripts"
        shutil.copytree(SCRIPTS, scripts, ignore=shutil.ignore_patterns("__pycache__"))
        venv = self.root / "runtime"
        (venv / "bin").mkdir(parents=True)
        python = venv / "bin/python"
        python.write_text(f"#!{sys.executable}\n" + '''import os,sys
args=sys.argv[1:]
if args[:2]==['-m','pip']:
    if 'freeze' in args: print('fixture-package==1')
    sys.exit(0)
if '--download-model' in args: sys.exit(4)
if args[:2]==['-m','playwright']: sys.exit(99)
os.execv(sys.executable,[sys.executable,*args])
''')
        python.chmod(0o755)
        chrome = self.root / "chrome"
        chrome.write_text("#!/bin/sh\nexit 0\n")
        chrome.chmod(0o755)
        env = os.environ.copy()
        env.update({"WCR_VENV": str(venv), "WCR_CHROME": str(chrome)})
        for model, expected in (("none", 0), ("tiny", 5)):
            p = subprocess.run(["bash", str(scripts / "setup.sh"), "--model", model], capture_output=True, env=env, timeout=10)
            self.assertEqual(p.returncode, expected, p.stderr)
        self.assertFalse((scripts / "venv").exists())
        self.assertTrue((venv / "installed-packages.txt").is_file())


if __name__ == "__main__":
    unittest.main()
