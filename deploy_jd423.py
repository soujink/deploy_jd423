"""deploy_jd423 —— 给模型部署工程师·回归集与线上样本的差分算一个特征指纹并定位可疑片段。

通过字符级与结构级特征识别模型部署工程师·回归集与线上样本的差分的痕迹，给出密度与命中位置

定位：
  只做特征匹配不做语义判定，所以不会被同义改写绕过

岗位对应：
  目标岗位　零一万物 · 实习模型部署工程师
  技能主线　MLOps、Docker、Kubernetes、大模型推理
  领域标签　MLOps、AI基础设施

设计约束：
  1. **只报告能定位到具体位置的结论**，不做语义猜测。
  2. **规则表公开**，每条命中都能对应到岗位要求的一条明示规则。
  3. **输入为空或格式不对时明确报错**，不静默返回空结果。

仅依赖 Python 标准库。

用法:
    python deploy_jd423.py --help
    python deploy_jd423.py --file input.txt
    python deploy_jd423.py --text "示例内容"
    python deploy_jd423.py --file input.txt --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys

# 岗位规则表：每条规则独立可核查，命中即报，不做推断。
# 规则由岗位 JD 的技能线与领域标签派生——每条都能对回岗位要求。
# 目标岗位：零一万物 · 实习模型部署工程师
RULES: list[dict] = [
    {
        "name": "模型部署工程师·回归集与线上样本的差分·缺失",
        "why": "岗位要求「MLOps」在输入里找不到对应内容",
        "severity": "high",
        "keywords": ['missing', 'absent', '缺少', '没有', '未提供', 'MLOps'],
    },
    {
        "name": "模型部署工程师·回归集与线上样本的差分·冲突",
        "why": "两处关于「Docker」的描述互相矛盾",
        "severity": "high",
        "keywords": ['conflict', 'contradict', '矛盾', '不一致', '相反', 'Docker'],
    },
    {
        "name": "模型部署工程师·回归集与线上样本的差分·越界",
        "why": "「Kubernetes」的取值超出岗位场景的常规范围",
        "severity": "medium",
        "keywords": ['out of range', 'outlier', '越界', '超限', '超过', 'Kubernetes'],
    },
    {
        "name": "模型部署工程师·回归集与线上样本的差分·退化",
        "why": "「大模型推理」相关的信息量不足以支撑判断",
        "severity": "medium",
        "keywords": ['degrade', 'insufficient', '不足', '太少', '无法', '大模型推理'],
    },
    {
        "name": "模型部署工程师·回归集与线上样本的差分·泄漏",
        "why": "「AI基础设施」相关的内容被意外暴露",
        "severity": "high",
        "keywords": ['leak', 'expose', '泄漏', '暴露', '明文', 'AI基础设施'],
    },
    {
        "name": "模型部署工程师·回归集与线上样本的差分·重复",
        "why": "同一处「模型部署工程师」信息被反复传递",
        "severity": "low",
        "keywords": ['duplicate', 'repeat', '重复', 'again', '模型部署工程师'],
    },
    {
        "name": "模型部署工程师·回归集与线上样本的差分·陈旧#2",
        "why": "「MLOps」的时效性已过期",
        "severity": "medium",
        "keywords": ['stale', 'expired', '过期', '陈旧', '旧版', 'MLOps'],
    },
    {
        "name": "模型部署工程师·回归集与线上样本的差分·不可核#2",
        "why": "关于「Docker」的说法无法追溯到具体证据",
        "severity": "high",
        "keywords": ['unverifiable', 'no evidence', '无法追溯', '没有来源', 'Docker'],
    },
]

# 特征规则：(名称, 正则, 说明)
SIGNATURE_RULES: list[tuple[str, str, str]] = [('invisible', '[\\u200b-\\u200f\\u202a-\\u202e\\u2060-\\u2064\\ufeff]', '不可见控制字符'), ('fullwidth', '[\\uff01-\\uff5e]', '全角字符'), ('homoglyph', '[\\u0430-\\u044f\\u0450-\\u045f]', '西里尔同形字'), ('override', '(ignore (all )?previous|ignore above|disregard)', '覆盖指令'), ('role_switch', '(you are now|act as|pretend to be)', '角色切换'), ('exfil', '(send|post|upload).{0,30}(http|www\\\\.)', '外传意图'), ('模型部署工程师', '模型部署工程师', '岗位关键词「模型部署工程师」')]



PATTERNS: list[tuple[str, re.Pattern]] = [
    (name, re.compile(pat, re.I)) for name, pat, _ in SIGNATURE_RULES
]


def deploy_jd423_locate(text: str) -> list[dict]:
    """定位所有命中的特征片段。"""
    out: list[dict] = []
    for name, rx in PATTERNS:
        for m in rx.finditer(text):
            out.append({
                "feature": name,
                "start": m.start(),
                "end": m.end(),
                "snippet": m.group(0)[:80],
            })
    out.sort(key=lambda d: (d["start"], d["feature"]))
    return out


def deploy_jd423_density(text: str) -> float:
    """可疑字符密度。"""
    if not text:
        return 0.0
    hits = deploy_jd423_locate(text)
    covered = sum(d["end"] - d["start"] for d in hits)
    return covered / len(text)


def deploy_jd423_analyze(text: str) -> dict:
    """主分析：返回命中位置与密度。"""
    hits = deploy_jd423_locate(text)
    by_feature: dict[str, int] = {}
    for h in hits:
        by_feature[h["feature"]] = by_feature.get(h["feature"], 0) + 1
    return {
        "length": len(text),
        "hits": hits,
        "hit_count": len(hits),
        "by_feature": by_feature,
        "density": round(deploy_jd423_density(text), 4),
        "clean": not hits,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def render(result: dict) -> str:
    """把结果渲染成人读的文本。每个工具的版式不同。"""
    out: list[str] = []
    if not result.get("ok", True):
        out.append(f"无法分析：{{result.get('error', '未知原因')}}")
        return "\n".join(out)
    out.append(f"长度：{result['length']}  命中：{result['hit_count']}  密度：{result['density']}")
    out.append("")
    for h in result["hits"]:
        out.append(f"  {h['feature']:<14} @{h['start']:>5}  {h['snippet']!r}")
    if result["clean"]:
        out.append("没有命中任何特征规则。")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="deploy_jd423",
        description="通过字符级与结构级特征识别模型部署工程师·回归集与线上样本的差分的痕迹，给出密度与命中位置（仅依赖标准库）",
        epilog=(
            "示例:\n"
            "  python deploy_jd423.py --file input.txt\n"
            "  python deploy_jd423.py --text '示例内容'\n"
            "  python deploy_jd423.py --file input.txt --json\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--file", help="输入文件路径")
    src.add_argument("--text", help="直接给出输入内容")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    args = ap.parse_args(argv)

    if args.file:
        try:
            with open(args.file, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError as e:
            print(f"读不了文件：{{e}}", file=sys.stderr)
            return 2
    else:
        content = args.text

    if not content.strip():
        print("输入是空的。", file=sys.stderr)
        return 2

    result = deploy_jd423_analyze(content)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print(render(result))
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
