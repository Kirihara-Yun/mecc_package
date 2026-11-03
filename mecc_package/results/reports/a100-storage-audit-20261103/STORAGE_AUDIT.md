# A100 存储介质只读审计（2026-11-03）

本审计仅做只读查询；**未安装驱动、未改变 RAID 配置、未写任何实验数据**。

## 结论（先行）

- `/data` 由本地块设备 `/dev/sdb` 以 `ext4` 挂载（`rw,relatime,stripe=64`），容量 3.5T、可用 336G（90% 已用），**非 tmpfs / 非 NFS**，可正常读写。
- `lsblk`：`sdb` 的 `MODEL=MR9364-8i`、`ROTA=1`、`TYPE=disk`、`SIZE=3.5T`、`MOUNTPOINTS=/data`。
- 内核属性：`/sys/block/sdb/queue/rotational = 1`（视为旋转介质）；`vendor=AVAGO`、`model=MR9364-8i`。
- 系统中**无 `/dev/nvme*` 设备**；`/proc/mdstat` 显示 `unused devices: <none>`（无 md 软 RAID）。
- RAID 控制器工具 `storcli64` 存在（`/opt/MegaRAID/storcli/storcli64`），但只读 `show` 返回
  `Number of Controllers = 0`；`sudo -n` 提示 `a password is required`（无免密 sudo）。
- **判定：物理介质类型 = `unknown`。无法证明 `/data` 为 NVMe SSD。**

## 含义与约束

- `cold_ssd=true` 仅表示**代码走冷读路径**，不表示盘内物理介质为 NVMe SSD。
- 在存储介质未确认前，本轮 B1/B2/B3 运行**仅用于显存（OOM）触发条件诊断**，不得表述为
  "NVMe SSD 性能"，也不得与任何 SSD 带宽/IOPS 结论关联。

## 命令与原始输出

### 1) 挂载点

```console
$ findmnt -T /data
TARGET SOURCE   FSTYPE OPTIONS
/data  /dev/sdb ext4   rw,relatime,stripe=64

$ df -hT /data
Filesystem     Type  Size  Used Avail Use% Mounted on
/dev/sdb       ext4  3.5T  3.0T  336G  90% /data
```

### 2) 块设备布局

```console
$ lsblk -o NAME,PATH,MODEL,ROTA,TYPE,SIZE,MOUNTPOINTS
NAME   PATH      MODEL     ROTA TYPE   SIZE MOUNTPOINTS
sda    /dev/sda  MR9364-8i    1 disk 893.8G
├─sda1 /dev/sda1              1 part   512M /boot/efi
└─sda2 /dev/sda2              1 part 893.2G /
sdb    /dev/sdb  MR9364-8i    1 disk   3.5T /data
```

### 3) 内核媒体/设备属性

```console
$ cat /sys/block/sdb/queue/rotational
1
$ cat /sys/block/sdb/device/vendor /sys/block/sdb/device/model
AVAGO
MR9364-8i
$ ls /dev/nvme*
ls: cannot access '/dev/nvme*': No such file or directory
$ cat /proc/mdstat
Personalities :
unused devices: <none>
```

### 4) RAID 控制器只读查询

```console
$ /opt/MegaRAID/storcli/storcli64 show
Status Code = 0
Status = Success
Number of Controllers = 0
Host Name = manager
Operating System  = Linux6.8.0-40-generic

$ /opt/MegaRAID/storcli/storcli64 /c0 show
Status = Failure
Description = Controller 0 not found

$ sudo -n /opt/MegaRAID/storcli/storcli64 /c0 show
sudo: a password is required
```

## 判定链

1. 挂载为本地 ext4 块设备 → 可作为 store 落盘位置（可用）。
2. `ROTA=1` 且无 NVMe 设备、无 md RAID、控制器不可查询 → **介质类型未知**，不能声称 NVMe SSD。
3. 结论：**`unknown`**。后续任何性能表述必须带此前提。
