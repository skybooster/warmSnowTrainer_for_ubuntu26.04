# 暖雪存档修改器（Warm Snow Trainer for Linux）

[English](README_EN.md) | 中文

针对 **Ubuntu 26.04，Steam 为 snap 版 + Proton** 的《暖雪 / Warm Snow》存档修改器。目前实现 **局外货币修改**：红魂、蓝魂（灵魂）、黄魂（梦灰）、梦玉、幽冥之魂、魂罐数量、梦魇速魂等。

纯 Python 实现，无第三方依赖，直接对存档文件做**原地定点修改**，只改写对应字段的 4 字节，文件结构和长度不变，修改前会自动备份。

## 存档原理

暖雪的存档是 .NET BinaryFormatter 序列化的 `PlayerSave` 对象，位于 Proton前缀内：

```
.../steamapps/compatdata/1296830/pfx/drive_c/users/steamuser/
    AppData/LocalLow/BadMudStudio/WarmSnow/Save/save_<槽位>
```

本工具解析该二进制格式，定位到 `souls`（蓝魂/灵魂）、`redsouls`（红魂）、`dreamAsh`（梦灰/黄魂）等字段的字节偏移后直接改写。

## 使用方法

```bash
# 1. 查看当前存档数值（自动探测存档目录）
python3 -m warmsnow_trainer list

# 2. 修改单个字段（字段名或中文名均可）
python3 -m warmsnow_trainer set souls 999999      # 灵魂（蓝魂）
python3 -m warmsnow_trainer set 红魂 99999
python3 -m warmsnow_trainer set 时之辉光 99999   # 橙色货币（终业 DLC 机心天赋）
python3 -m warmsnow_trainer set 梦灰 999999      # 黄魂
python3 -m warmsnow_trainer set dreamJewel 999999
python3 -m warmsnow_trainer set 幽冥之魂 999999
python3 -m warmsnow_trainer set soulJarCount 999999

# 3. 交互式逐项修改
python3 -m warmsnow_trainer interactive

# 4. 修改指定槽位 / 手动指定存档目录
python3 -m warmsnow_trainer --slot 1 list
python3 -m warmsnow_trainer --save-dir /path/to/Save set 红魂 99999
```

可修改字段：

| 字段 key | 中文名 | 说明 |
|----------|--------|------|
| `bluesouls` |蓝魂 | 主线灵魂货币，战斗中拾取的蓝色魂 |
| `redsouls` | 红魂 | 红魂商店货币 |
| `timeGlow` | 时之辉光（橙魂） | 终业 DLC 升级货币 |
| `dreamAsh` | 梦灰（黄魂） | 烬梦 DLC 货币 |
| `dreamJewel` | 梦玉 | 烬梦 DLC 货币 |
| `MementoSouls` | 幽冥之魂 | 残响/记忆相关魂 |
| `soulJarCount` | 魂罐数量 | 可携带的魂罐数 |
| `nightmareFastSouls` | 梦魇速魂 | 梦魇模式货币 |

## 注意事项

- **修改前先退出游戏**，否则游戏内内存数据会在存档时覆盖你的修改，且 Steam
  云存档可能同步回旧值。
- 每次修改都会在存档旁生成 `save_0.bak_时间戳` 备份文件，命令执行后会在终端打印该备份文件的绝对路径。若要恢复修改前的存档删去 `.bak_时间戳 `即可。**注意：每一次修改都会保存一个修改前的存档文件。**
- 若自动探测失败，用 `--save-dir` 指定 Save 目录，或设置环境变量 `WARMSNOW_SAVE_DIR`。
- 修改存档之后，第一次启动较慢，请耐心等待。

## 安装为命令（安不安装都无所谓）

```bash
pip install -e .          # 在项目根目录执行
warmsnow-trainer list
```

## 最后

该修改器仅仅支持修改局外的一些道具的数量，支持不想在游戏前期因为数值低而屡屡受挫的玩家跳过前期的折磨，享受游戏后期割草的快乐。**但是谁说前期的积累不是游戏的快乐呢？**本修改器的目的也是为了填补《warmsnow》修改器在ubuntu系统中的空白。（这也算是一种填补吗？有点水，不是吗？）

最后的最后，这是我拿deepseek随便写的。大模型为DeepSeek V4 Pro。

## 有问题联系我

yixuanliu@bluemailx.com