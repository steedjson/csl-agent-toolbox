#!/usr/bin/env python3
"""csl-video-ss1 产出自检核验器（回归用）。

用法:
  python3 verify_output.py <report.md> --anchor "锚点块原文" [--anchor "第二块..."] [--min N]
                              [--transcript] [--forbid-accent] [--bgm-expect "15 秒"]

检查项（对应 SKILL.md Output Self-Check）:
  1. 每个锚点块出现次数 >= --min（默认 8）
  2. 禁串: 默认无。--forbid-accent 启用台灣華語/台湾国语/Taiwan Mandarin 扫描——
     仅用于「简体＋非台湾口音」回归样例；繁体或台灣華語为合法参数的产出勿启用
     （技能 L37 允许该口音，聚 合禁串会误杀）。
  3. 自检章节存在且通过项 >= 5
  4. BGM 时长声明存在；--bgm-expect 给定精确值（如 "60 秒"）时按值断言
<report.md> 为技能产出全文; --transcript 传入 Claude 子代理 JSONL 时提取最终报告。

shortcut: 锚点核验为聚合计数，无法定位单份提示词缺锚点（false-PASS 路径已被
G2 冷跑实证）；需要逐份核验时，把产出按提示词切分后逐段调用本脚本 --min 1。
"""
import argparse, json, re, sys

ACCENT_FORBIDDEN = ('台灣華語', '台湾国语', '臺灣', 'Taiwan Mandarin')


def final_report(path):
    hb, last = [], []
    for line in open(path, encoding='utf-8'):
        try:
            o = json.loads(line)
        except Exception:
            continue
        if not isinstance(o, dict) or o.get('type') != 'assistant':
            continue
        m = o.get('message', {})
        for c in (m.get('content') or []):
            if not isinstance(c, dict):
                continue
            if c.get('type') == 'text' and c.get('text', '').strip():
                last = [c['text']]
            if c.get('type') == 'tool_use' and 'Handback' in str(c.get('name', '')):
                buf = []

                def walk(x):
                    if isinstance(x, str):
                        buf.append(x)
                    elif isinstance(x, list):
                        [walk(i) for i in x]
                    elif isinstance(x, dict):
                        [walk(i) for i in x.values()]
                walk(c.get('input', {}))
                hb.append('\n'.join(buf))
    return hb[-1] if hb else '\n'.join(last)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('report')
    ap.add_argument('--anchor', action='append', required=True)
    ap.add_argument('--min', type=int, default=8)
    ap.add_argument('--transcript', action='store_true')
    ap.add_argument('--forbid-accent', action='store_true',
                    help='启用台湾口音禁串扫描（仅限简体非台湾口音回归样例）')
    ap.add_argument('--bgm-expect', default=None, help='期望的 BGM 时长声明，如 "60 秒"')
    args = ap.parse_args()

    t = final_report(args.report) if args.transcript else open(args.report, encoding='utf-8').read()
    ok = True
    for i, (a) in enumerate(args.anchor):
        n = t.count(a)
        passed = n >= args.min
        ok &= passed
        print(f"[{'PASS' if passed else 'FAIL'}] anchor#{i + 1} x{n} (min {args.min})")
    if args.forbid_accent:
        forb = [s for s in ACCENT_FORBIDDEN if s in t]
        ok &= not forb
        print(f"[{'PASS' if not forb else 'FAIL'}] forbidden_accent={forb or 'none'}")
    sc = ('自检' in t or '自檢' in t) and (t.count('通过') + t.count('通過') >= 5)
    ok &= sc
    print(f"[{'PASS' if sc else 'FAIL'}] self_check_section")
    if args.bgm_expect:
        bgm = args.bgm_expect in t
    else:
        bgm = bool(re.search(r'\d+\s*(秒|seconds)', t))
    ok &= bgm
    print(f"[{'PASS' if bgm else 'FAIL'}] bgm_duration{'=' + args.bgm_expect if args.bgm_expect else ''}")
    print('OVERALL:', 'PASS' if ok else 'FAIL')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
