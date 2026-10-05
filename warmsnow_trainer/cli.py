"""Command-line interface for the Warm Snow save trainer."""

from __future__ import annotations

import argparse
import os
import sys

from . import __version__, savefile


def _print_values(values: dict) -> None:
    print("当前存档数值：")
    print("-" * 46)
    for field in savefile.FIELDS:
        print(f"  {field.label:<14} {values.get(field.key, 0):>10}   ({field.key})")
    print("-" * 46)


def cmd_list(args) -> int:
    save_dir = savefile.find_save_dir()
    if not save_dir:
        print("未找到暖雪存档目录。请用 --save-dir 指定，或设置环境变量 WARMSNOW_SAVE_DIR。", file=sys.stderr)
        return 1
    path = savefile.save_file_path(save_dir, args.slot)
    if not os.path.isfile(path):
        print(f"找不到存档文件: {path}", file=sys.stderr)
        return 1
    values = savefile.read_fields(path)
    print(f"存档文件: {path}")
    _print_values(values)
    return 0


def _find_field(key: str):
    for f in savefile.FIELDS:
        short = f.label.split("（")[0].split("(")[0]
        if key in (f.key, f.label, short):
            return f
    return None


def cmd_set(args) -> int:
    save_dir = savefile.find_save_dir()
    if not save_dir:
        print("未找到暖雪存档目录。", file=sys.stderr)
        return 1
    path = savefile.save_file_path(save_dir, args.slot)
    if not os.path.isfile(path):
        print(f"找不到存档文件: {path}", file=sys.stderr)
        return 1

    field = _find_field(args.key)
    if field is None:
        print(f"未知字段: {args.key}", file=sys.stderr)
        print("可用字段:", ", ".join(f"{f.key}({f.label})" for f in savefile.FIELDS), file=sys.stderr)
        return 1

    current = savefile.read_fields(path)
    before = current.get(field.key, 0)
    backup_path = savefile.write_fields(path, {field.key: args.value})
    print(f"已修改 {field.label}: {before} -> {args.value}")
    print(f"备份文件: {os.path.abspath(backup_path)}")
    return 0


def cmd_interactive(args) -> int:
    save_dir = savefile.find_save_dir()
    if not save_dir:
        print("未找到暖雪存档目录。", file=sys.stderr)
        return 1
    path = savefile.save_file_path(save_dir, args.slot)
    if not os.path.isfile(path):
        print(f"找不到存档文件: {path}", file=sys.stderr)
        return 1

    print(f"存档文件: {path}")
    _print_values(savefile.read_fields(path))
    print()
    print("输入要修改的项目，回车保持原值；输入 q 退出并保存。")
    updates = {}
    current = savefile.read_fields(path)
    for field in savefile.FIELDS:
        raw = input(f"{field.label} [{field.key}] 当前 {current.get(field.key, 0)} -> ")
        raw = raw.strip()
        if raw.lower() == "q":
            break
        if not raw:
            continue
        try:
            updates[field.key] = int(raw)
        except ValueError:
            print("  不是有效整数，跳过。")

    if updates:
        backup_path = savefile.write_fields(path, updates)
        print("已保存修改。")
        print(f"备份文件: {os.path.abspath(backup_path)}")
    else:
        print("没有修改。")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="warmsnow-trainer",
        description="暖雪（Warm Snow）存档修改器 —— 修改红魂/蓝魂/黄魂等局外货币数量",
    )
    parser.add_argument("--save-dir", help="暖雪 Save 目录（自动探测失败时使用）")
    parser.add_argument("--slot", type=int, default=0, help="存档槽位（默认 0）")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list", help="显示当前存档数值")

    p_set = sub.add_parser("set", help="修改单个字段")
    p_set.add_argument("key", help="字段名或中文名，如 souls / 红魂")
    p_set.add_argument("value", type=int, help="新数值")

    sub.add_parser("interactive", help="交互式逐项修改")

    args = parser.parse_args(argv)
    if args.save_dir:
        os.environ["WARMSNOW_SAVE_DIR"] = args.save_dir

    if args.command == "list":
        return cmd_list(args)
    if args.command == "set":
        return cmd_set(args)
    if args.command == "interactive":
        return cmd_interactive(args)
    return cmd_list(args)


if __name__ == "__main__":
    raise SystemExit(main())
