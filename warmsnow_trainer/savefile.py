"""Locate, read and modify Warm Snow save files.

Warm Snow (暖雪, Steam app id 1296830) stores its save data in a Proton
prefix under ``LocalLow/BadMudStudio/WarmSnow/Save``.  The per-slot file is
``save_<slot>`` and is a .NET BinaryFormatter-serialized ``PlayerSave``.
"""

from __future__ import annotations

import os
import shutil
import struct
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from . import binaryformatter as bf

# Steam app id for Warm Snow
APP_ID = "1296830"

# Relative path of the save folder inside a Proton prefix
_REL_SAVE = (
    "pfx/drive_c/users/steamuser/AppData/LocalLow/BadMudStudio/WarmSnow/Save"
)


@dataclass(frozen=True)
class Field:
    key: str              # PlayerSave member name
    label: str            # Chinese label
    note: str = ""        # extra explanation
    default: Optional[int] = None  # None -> no default suggestion


# Editable soul / meta-currency fields, ordered for display.
FIELDS: List[Field] = [
    Field("souls", "灵魂（蓝魂）", "主线灵魂货币，战斗中拾取的蓝色魂", 999999),
    Field("redsouls", "红魂", "红魂商店货币（终业 DLC）", 99999),
    Field("timeGlow", "时之辉光（橙）", "终业 DLC 机心天赋升级货币（≥10 级使用）", 999999999),
    Field("dreamAsh", "梦灰（黄魂）", "烬梦 DLC 货币", 999999),
    Field("dreamJewel", "梦玉", "烬梦 DLC 货币", 999999),
    Field("MementoSouls", "幽冥之魂", "残响/记忆相关魂", 999999),
    Field("soulJarCount", "魂罐数量", "可携带的魂罐数", 999999),
    Field("nightmareFastSouls", "梦魇速魂", "梦魇模式货币", 999999),
]


def save_dir_candidates() -> List[str]:
    """Return candidate Warm Snow save directories, best matches first."""
    home = os.path.expanduser("~")
    steam_roots = [
        os.path.join(home, "snap", "steam", "common", ".local", "share", "Steam"),
        os.path.join(home, ".local", "share", "Steam"),
        os.path.join(home, ".steam", "steam"),
        os.path.join(home, ".steam", "root"),
        os.path.join(home, ".var", "app", "com.valvesoftware.Steam", ".local", "share", "Steam"),
        os.path.join(home, ".var", "app", "com.valvesoftware.Steam", "data", "Steam"),
    ]
    candidates = []
    for root in steam_roots:
        candidates.append(os.path.join(root, "steamapps", "compatdata", APP_ID, _REL_SAVE))
        candidates.append(os.path.join(root, "steamapps", "compatdata", APP_ID, "pfx",
                                       "drive_c", "users", "steamuser", "AppData",
                                       "LocalLow", "BadMudStudio", "WarmSnow", "Save"))
    return candidates


def find_save_dir() -> Optional[str]:
    env = os.environ.get("WARMSNOW_SAVE_DIR")
    if env and os.path.isdir(env):
        return env
    for cand in save_dir_candidates():
        if os.path.isdir(cand):
            return cand
    return None


def save_file_path(save_dir: str, slot: int = 0) -> str:
    return os.path.join(save_dir, f"save_{slot}")


def read_player_save(path: str) -> tuple[bytearray, bf.ParseResult]:
    with open(path, "rb") as fh:
        data = bytearray(fh.read())
    res = bf.parse(bytes(data))
    if not isinstance(res.root, bf.ObjValue) or res.root.meta is None or res.root.meta.name != "PlayerSave":
        raise bf.BinaryFormatterError("file does not contain a PlayerSave object")
    return data, res


def read_fields(path: str) -> Dict[str, int]:
    """Read the editable currency fields from a save file."""
    data, res = read_player_save(path)
    root = res.root
    out: Dict[str, int] = {}
    for field in FIELDS:
        value = root.values.get(field.key)
        if isinstance(value, bool) or not isinstance(value, int):
            value = 0
        out[field.key] = value
    return out


def backup(path: str) -> str:
    """Create a timestamped backup next to the save file."""
    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup_path = f"{path}.bak_{stamp}"
    counter = 0
    while os.path.exists(backup_path):
        counter += 1
        backup_path = f"{path}.bak_{stamp}_{counter}"
    # shutil.copy copies content + permissions but leaves the destination
    # mtime as "now", so the backup's shown time matches the timestamp in its
    # name (shutil.copy2 would preserve the old source mtime, which confuses).
    shutil.copy(path, backup_path)
    return backup_path


def write_fields(path: str, values: Dict[str, int]) -> str:
    """Overwrite the given currency fields in-place.

    A backup is made first; the absolute path of the backup file is returned.
    """
    data, res = read_player_save(path)
    root = res.root
    for key, value in values.items():
        offset = root.offsets.get(key)
        if offset is None:
            raise ValueError(f"unknown field: {key}")
        if not (-2_147_483_648 <= value <= 2_147_483_647):
            raise ValueError(f"value out of int32 range for {key}: {value}")
        struct.pack_into("<i", data, offset, value)
    backup_path = backup(path)
    with open(path, "wb") as fh:
        fh.write(data)
    return backup_path
