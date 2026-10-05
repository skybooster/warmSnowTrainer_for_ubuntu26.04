# Warm Snow Trainer for Linux (暖雪存档修改器)

English | [中文](README.md)

A save-file trainer for *Warm Snow* (暖雪) targeting **Ubuntu 26.04** with the
**snap Steam + Proton** setup. It currently edits **out-of-run currencies**:
red souls, blue souls (`souls`), yellow souls (`dreamAsh`), dream jewels,
memento souls, soul jar count, and nightmare fast souls.

Pure Python with no third-party dependencies. It performs **in-place patching**
on the save file — only the 4 bytes of the target field are rewritten, so the
file structure and length stay identical. A backup is created automatically
before each change.

## How the save file works

Warm Snow's save is a .NET BinaryFormatter-serialized `PlayerSave` object,
located inside the Proton prefix:

```
.../steamapps/compatdata/1296830/pfx/drive_c/users/steamuser/
    AppData/LocalLow/BadMudStudio/WarmSnow/Save/save_<slot>
```

This tool parses that binary format, locates the byte offsets of `souls`
(blue souls), `redsouls` (red souls), `dreamAsh` (dream ash / yellow souls),
and other fields, then rewrites them directly.

## Usage

```bash
# 1. Show current save values (auto-detects the save directory)
python3 -m warmsnow_trainer list

# 2. Change a single field (key or Chinese name both work)
python3 -m warmsnow_trainer set souls 999999      # souls (blue)
python3 -m warmsnow_trainer set redsouls 99999    # red souls
python3 -m warmsnow_trainer set timeGlow 999999999  # time glow (orange, Machine Heart talent)
python3 -m warmsnow_trainer set dreamAsh 999999   # dream ash (yellow)
python3 -m warmsnow_trainer set dreamJewel 999999
python3 -m warmsnow_trainer set MementoSouls 999999
python3 -m warmsnow_trainer set soulJarCount 999999

# 3. Interactive, field-by-field editing
python3 -m warmsnow_trainer interactive

# 4. Choose a slot / point to a save directory manually
python3 -m warmsnow_trainer --slot 1 list
python3 -m warmsnow_trainer --save-dir /path/to/Save set redsouls 99999
```

Editable fields:

| Field key       | Chinese          | Description                                   |
|-----------------|------------------|-----------------------------------------------|
| `bluesouls`     | 蓝魂     | Main soul currency; the blue souls dropped in runs |
| `redsouls`      | 红魂             | Red-soul shop currency   |
| `timeGlow`      | 时之辉光（橙魂）   | Machine Heart talent upgrade currency (Endgame DLC) |
| `dreamAsh`      | 梦灰（黄魂）     | Ember Dream (烬梦) DLC currency               |
| `dreamJewel`    | 梦玉             | Ember Dream (烬梦) DLC currency               |
| `MementoSouls`  | 幽冥之魂         | Souls used for echoes / memories              |
| `soulJarCount`  | 魂罐数量         | Number of soul jars you can carry             |
| `nightmareFastSouls` | 梦魇速魂   | Nightmare-mode currency                       |

## Notes

- **Exit the game before editing.** Otherwise the in-memory data will overwrite
  your changes when the game saves, and Steam Cloud may sync the old values back.
- Every edit creates a `save_0.bak_<timestamp>` backup next to the save, and
  the command prints the backup file's absolute path. To restore, remove the
  `.bak_<timestamp>` suffix from the name. **Each edit stores one pre-edit
  snapshot of the save.**
- If auto-detection fails, use `--save-dir` to point at the Save folder, or set
  the `WARMSNOW_SAVE_DIR` environment variable.
- The first game launch after editing may be slower than usual; please be patient.

## Install as a command (optional)

```bash
pip install -e .          # run at the project root
warmsnow-trainer list
```

## Finally

This trainer only edits some out-of-run item quantities. It is for players who
don't want to struggle through the early game with low numbers and would rather
skip straight to the late-game power fantasy. **But who says the early grind
isn't part of the fun?** This tool also aims to fill the gap of Warm Snow
trainers on Ubuntu. (Does it really count as filling a gap? Feels a bit
half-hearted, doesn't it?)

And one last thing — I wrote this with DeepSeek on a whim. The model used was
DeepSeek V4 Pro.

## Contact

yixuanliu@bluemailx.com
