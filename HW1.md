---
title: HW1

---

### 環境設置：
```
uname -r
5.15.0-198-generic
```
![image](https://hackmd.io/_uploads/ryGbIKz2zx.png)
```bash
$ git clone https://github.com/snu-csl/nvmevirt
git checkout c93e88c
sudo apt update
sudo apt install build-essential linux-headers-$(uname -r) -y
```

### Show: two namespaces running (conventional vs. ZNS) and their Identify info. 
**直到最後一個compare 之前zone size 都是 256MB**
從4GB開始保留2GB
```
sudo nano /etc/default/grub
GRUB_CMDLINE_LINUX="memmap=2049M\\\$4G" (記得要多加上1MB)
```
Kbuild 註解
```c
#CONFIG_NVMEVIRT_NVM := y
CONFIG_NVMEVIRT_SSD := y
CONFIG_NVMEVIRT_ZNS := y
#CONFIG_NVMEVIRT_KV := y
#ccflags-$(CONFIG_NVMEVIRT_ZNS) += -DBASE_SSD=WD_ZN540 避免蓋掉 ccflags-$(CONFIG_NVMEVIRT_SSD) += -DBASE_SSD=SAMSUNG_970PRO
#ccflags-$(CONFIG_NVMEVIRT_ZNS) += -DBASE_SSD=ZNS_PROTOTYPE

註解KV
#ccflags-$(CONFIG_NVMEVIRT_KV) += -DBASE_SSD=KV_PROTOTYPE
#nvmev-$(CONFIG_NVMEVIRT_KV) += kv_ftl.o append_only.o bitmap.o
```
``` c
修改
#if (BASE_SSD == SAMSUNG_970PRO)
#define NR_NAMESPACES 1  修改為 2
```
容量都設定為 1GB
```
#define NS_CAPACITY_0 GB(1)
#define NS_CAPACITY_1 GB(1)
```

修改 `NS_SSD_TYPE_1 NS_SSD_TYPE_0` 改為 `NS_SSD_TYPE_1 SSD_TYPE_ZNS`
![image](https://hackmd.io/_uploads/H15MLVQ3fg.png)
新增在 SAMSUNG_970PRO BLOCK 下
```c
#define ZONE_SIZE MB(256)
#define DIES_PER_ZONE 1
#define MAX_ZRWA_ZONES 0
#define ZONE_WB_SIZE 0
#define ZRWA_SIZE 0
#define ZRWAFG_SIZE 0
#define ZRWA_BUFFER_SIZE 0
```
註解 main.c
![image](https://hackmd.io/_uploads/r1LlNr7hGe.png)
```
ERROR: modpost: "kv_init_namespace" [/home/memory/nvmevirt/nvmev.ko] undefined!
ERROR: modpost: "simple_init_namespace" [/home/memory/nvmevirt/nvmev.ko] undefined!
```

兩個 namespace 的capacity必須整除  ZONE_SIZE
又Reserved memory must be 1 MB larger than the requested size
所以要傳入 2048+1MB

`sudo insmod nvmev.ko memmap_start=4G memmap_size=2049M cpus=0,1` (要加入cpu)
 
 成功會出現
 ![image](https://hackmd.io/_uploads/ryLl6PXnMe.png)
 ![image](https://hackmd.io/_uploads/r1D_TDQ2Ml.png)
```bash
lsblk
NAME                      MAJ:MIN RM  SIZE RO TYPE MOUNTPOINTS
sr0                        11:0    1 1024M  1 rom  
vda                       252:0    0   20G  0 disk 
├─vda1                    252:1    0    1M  0 part 
├─vda2                    252:2    0  1.8G  0 part /boot
└─vda3                    252:3    0 18.2G  0 part 
  └─ubuntu--vg-ubuntu--lv 253:0    0   10G  0 lvm  /
nvme0n1                   259:0    0  957M  0 disk 
nvme0n2                   259:1    0    1G  0 disk 
```
**Conventional**
identity info
```c
sudo nvme id-ns /dev/nvme0n1
NVME Identify Namespace 1:
nsze    : 0x1de813
ncap    : 0x1de813
nuse    : 0x1de813
nsfeat  : 0
nlbaf   : 6
flbas   : 0
mc      : 0
dpc     : 0
dps     : 0
nmic    : 0
rescap  : 0
fpi     : 0
dlfeat  : 0
nawun   : 0
nawupf  : 0
nacwu   : 0
nabsn   : 0
nabo    : 0
nabspf  : 0
noiob   : 0
nvmcap  : 0
mssrl   : 0
mcl     : 0
msrc    : 0
anagrpid: 0
nsattr	: 0
nvmsetid: 0
endgid  : 0
nguid   : 00000000000000000000000000000000
eui64   : 0000000000000000
lbaf  0 : ms:0   lbads:9  rp:0x2 (in use)
lbaf  1 : ms:8   lbads:9  rp:0x2 
lbaf  2 : ms:16  lbads:9  rp:0x2 
lbaf  3 : ms:0   lbads:12 rp:0 
lbaf  4 : ms:8   lbads:12 rp:0 
lbaf  5 : ms:64  lbads:12 rp:0 
lbaf  6 : ms:128 lbads:12 rp:0 
```
```c
sudo nvme zns report-zones /dev/nvme0n1
nr_zones: 0
```


**ZNS**
identity info
```c
sudo nvme id-ns /dev/nvme0n2
NVME Identify Namespace 2:
nsze    : 0x200000
ncap    : 0x200000
nuse    : 0x200000
nsfeat  : 0
nlbaf   : 6
flbas   : 0
mc      : 0
dpc     : 0
dps     : 0
nmic    : 0
rescap  : 0
fpi     : 0
dlfeat  : 0
nawun   : 0
nawupf  : 0
nacwu   : 0
nabsn   : 0
nabo    : 0
nabspf  : 0
noiob   : 0
nvmcap  : 0
mssrl   : 0
mcl     : 0
msrc    : 0
anagrpid: 0
nsattr	: 0
nvmsetid: 0
endgid  : 0
nguid   : 00000000000000000000000000000000
eui64   : 0000000000000000
lbaf  0 : ms:0   lbads:9  rp:0x2 (in use)
lbaf  1 : ms:8   lbads:9  rp:0x2 
lbaf  2 : ms:16  lbads:9  rp:0x2 
lbaf  3 : ms:0   lbads:12 rp:0 
lbaf  4 : ms:8   lbads:12 rp:0 
lbaf  5 : ms:64  lbads:12 rp:0 
lbaf  6 : ms:128 lbads:12 rp:0 
```

```c
sudo nvme zns report-zones /dev/nvme0n2
nr_zones: 4
SLBA: 0          WP: 0          Cap: 0x80000    State: 0x10 Type: 0x2  Attrs: 0    AttrsInfo: 0   
SLBA: 0x80000    WP: 0x80000    Cap: 0x80000    State: 0x10 Type: 0x2  Attrs: 0    AttrsInfo: 0   
SLBA: 0x100000   WP: 0x100000   Cap: 0x80000    State: 0x10 Type: 0x2  Attrs: 0    AttrsInfo: 0   
SLBA: 0x180000   WP: 0x180000   Cap: 0x80000    State: 0x10 Type: 0x2  Attrs: 0    AttrsInfo: 0   
```
show identity info 的時候如果出現 core dump 需要先 sudo dmesg -C 
->還未找到原因

### Show: benchmark runs on both namespaces. (30%)
CONV
```bash
sudo fio --name=test_conv_256m --filename=/dev/nvme0n1 --direct=1 --rw=write --bs=4k --ioengine=libaio --iodepth=1 --size=256M
test_conv_256m: (g=0): rw=write, bs=(R) 4096B-4096B, (W) 4096B-4096B, (T) 4096B-4096B, ioengine=libaio, iodepth=1
fio-3.28
Starting 1 process
Jobs: 1 (f=1)
test_conv_256m: (groupid=0, jobs=1): err= 0: pid=1439: Mon Oct 19 11:17:40 2026
  write: IOPS=61.5k, BW=240MiB/s (252MB/s)(256MiB/1065msec); 0 zone resets
    slat (nsec): min=2625, max=59254, avg=2843.74, stdev=774.07
    clat (nsec): min=872, max=216486, avg=13039.83, stdev=5713.45
     lat (usec): min=13, max=230, avg=15.95, stdev= 5.80
    clat percentiles (usec):
     |  1.00th=[   12],  5.00th=[   12], 10.00th=[   12], 20.00th=[   12],
     | 30.00th=[   12], 40.00th=[   12], 50.00th=[   12], 60.00th=[   12],
     | 70.00th=[   15], 80.00th=[   15], 90.00th=[   15], 95.00th=[   16],
     | 99.00th=[   21], 99.50th=[   26], 99.90th=[  149], 99.95th=[  157],
     | 99.99th=[  180]
   bw (  KiB/s): min=230400, max=260520, per=99.72%, avg=245460.00, stdev=21298.06, samples=2
   iops        : min=57600, max=65130, avg=61365.00, stdev=5324.51, samples=2
  lat (nsec)   : 1000=0.01%
  lat (usec)   : 2=0.01%, 10=0.02%, 20=98.78%, 50=1.03%, 100=0.02%
  lat (usec)   : 250=0.13%
  cpu          : usr=10.53%, sys=32.33%, ctx=65546, majf=0, minf=14
  IO depths    : 1=100.0%, 2=0.0%, 4=0.0%, 8=0.0%, 16=0.0%, 32=0.0%, >=64=0.0%
     submit    : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     complete  : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     issued rwts: total=0,65536,0,0 short=0,0,0,0 dropped=0,0,0,0
     latency   : target=0, window=0, percentile=100.00%, depth=1

Run status group 0 (all jobs):
  WRITE: bw=240MiB/s (252MB/s), 240MiB/s-240MiB/s (252MB/s-252MB/s), io=256MiB (268MB), run=1065-1065msec

Disk stats (read/write):
  nvme0n1: ios=72/54776, merge=0/0, ticks=101/660, in_queue=760, util=91.88%
```
ZNS
```bash
sudo fio --name=test_zns --filename=/dev/nvme0n2 --direct=1 --rw=write --bs=4k --ioengine=libaio --iodepth=1 --size=256M --zonemode=zbd
test_zns: (g=0): rw=write, bs=(R) 4096B-4096B, (W) 4096B-4096B, (T) 4096B-4096B, ioengine=libaio, iodepth=1
fio-3.28
Starting 1 process
Jobs: 1 (f=0)
test_zns: (groupid=0, jobs=1): err= 0: pid=1426: Mon Oct 19 11:11:13 2026
  write: IOPS=35.9k, BW=140MiB/s (147MB/s)(256MiB/1828msec); 0 zone resets
    slat (nsec): min=2656, max=44237, avg=2856.22, stdev=608.06
    clat (nsec): min=901, max=3762.3k, avg=24515.55, stdev=68080.22
     lat (usec): min=14, max=3765, avg=27.44, stdev=68.08
    clat percentiles (usec):
     |  1.00th=[   13],  5.00th=[   13], 10.00th=[   13], 20.00th=[   13],
     | 30.00th=[   13], 40.00th=[   13], 50.00th=[   13], 60.00th=[   14],
     | 70.00th=[   14], 80.00th=[   15], 90.00th=[   92], 95.00th=[  106],
     | 99.00th=[  109], 99.50th=[  111], 99.90th=[  265], 99.95th=[ 2008],
     | 99.99th=[ 2966]
   bw (  KiB/s): min=142976, max=144960, per=100.00%, avg=143637.33, stdev=1145.46, samples=3
   iops        : min=35744, max=36240, avg=35909.33, stdev=286.37, samples=3
  lat (nsec)   : 1000=0.01%
  lat (usec)   : 2=0.01%, 10=0.03%, 20=88.92%, 50=0.65%, 100=1.36%
  lat (usec)   : 250=8.86%, 500=0.10%, 750=0.01%, 1000=0.01%
  lat (msec)   : 2=0.02%, 4=0.05%
  cpu          : usr=5.25%, sys=20.63%, ctx=65560, majf=0, minf=16
  IO depths    : 1=100.0%, 2=0.0%, 4=0.0%, 8=0.0%, 16=0.0%, 32=0.0%, >=64=0.0%
     submit    : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     complete  : 0=0.0%, 4=100.0%, 8=0.0%, 16=0.0%, 32=0.0%, 64=0.0%, >=64=0.0%
     issued rwts: total=0,65536,0,0 short=0,0,0,0 dropped=0,0,0,0
     latency   : target=0, window=0, percentile=100.00%, depth=1

Run status group 0 (all jobs):
  WRITE: bw=140MiB/s (147MB/s), 140MiB/s-140MiB/s (147MB/s-147MB/s), io=256MiB (268MB), run=1828-1828msec

Disk stats (read/write):
  nvme0n2: ios=48/58743, merge=0/0, ticks=8/1367, in_queue=1376, util=95.23%
```


|效能指標| Conventional (傳統 SSD / nvme0n1)|ZNS (分區儲存 / nvme0n2) |
| -------- | -------- | -------- |
| 寫入頻寬 (Bandwidth)     | 240 MiB/s    | 140 MiB/s     |
| 每秒寫入次數 (IOPS)   |61,500 次/秒  | 35,900 次/秒  |
| 平均延遲 (Avg Latency)  | 15.95 us   | 27.44 us  |
| 最大延遲 (Max Latency)   | 230 us  | 3,765 us  |
### Present: short write-up comparing NVMeVirt code paths. (20%)
**code path:**
- [ ] Namespace的建立
 從 insmod  之後呼叫 `module_init(NVMeV_init); `
 在 `NVMeV_init()`中 會分別 
 call `VDEV_INIT()` `NVMEV_STORAGE_INIT(nvmev_vdev)` 和 `NVMEV_NAMESPACE_INIT(nvmev_vdev)`
其中 `NVMEV_STORAGE_INIT(nvmev_vdev)` 會用memremap 將記憶體映射到 kernel 虛擬位址
`NVMEV_NAMESPACE_INIT()` 會設定剩餘容量與起始位址，分配 namespace 的大小
之後依據不同的類型分別呼叫不同的 init function 如 `conv_init_namespace()` 和`zns_init_namespace()`
![image](https://hackmd.io/_uploads/r1Y1yc43fe.png)
而 `VDEV_INIT()` defined in pci.c 會配置虛擬裝置的kernel data structure，配置一頁記憶體來存放 PCI 相關結構，並設定各個 PCI 結構的指標。

1. `conv_init_namespace()`defined in `conv_ftl.c` 
`conv_init_namespace()` 會初始化 Conventional Namespace 所需的 SSD 與 Conventional FTL。透過 `ssd_init_params()` 和 `conv_init_params()` 分別初始化 SSD 與 Conventional FTL 的參數，接著依據 SSD_PARTITIONS 配置多個 conv_ftl instances，並在迴圈中為每個 partition 配置 struct ssd，呼叫 `ssd_init()` 初始化 SSD，再透過 `conv_init_ftl()` 初始化對應的 Conventional FTL。
初始化完成後，會將各個 partition 的 PCIe model 與 write buffer 設定為共用資源，以避免每個 partition 都獨立使用這些資源。然後設定 Namespace 等相關資訊，包括 Namespace ID、CSI、partition 數量、FTL 指標、記憶體映射位址，以及 I/O command handler。`ns->csi` 設定為 `NVME_CSI_NVM`， `ns->proc_io_cmd` 設定為 `conv_proc_nvme_io_cmd()`，讓後續的 I/O commands 交由 Conventional FTL 對應的處理函數處理。
最後， `cpp.pba_pcent` 計算 Namespace 的 logical size，並輸出 physical space 與 logical space 的資訊。

2. `zns_init_namespace()` defined in `zns_ftl.c`
`zns_init_namespace()` 則負責初始化 Zoned Namespace（ZNS）所需的 SSD 與 ZNS FTL。接著配置一個 struct ssd，透過 `ssd_init_params()` 設定 SSD 參數，再呼叫 `ssd_init()` 初始化 SSD。
和Conventional FTL 不同的是，ZNS 目前只支援單一 partition，因此 `nr_parts` 固定設為 1，並透過 `NVMEV_ASSERT()` 確認此條件。之後配置 `struct zns_ftl`，呼叫 `zns_init_params()` 初始化 ZNS 專用參數，再透過 `zns_init_ftl()` 初始化 ZNS FTL，並傳入 mapped_addr 作為記憶體映射區域。
完成初始化後，設定 Namespace 的相關欄位，包括 Namespace ID、CSI、partition 數量、FTL 指標、容量與記憶體映射位址。最後，`zns_init_namespace()` 完成 ZNS Namespace 的初始化並返回。與 Conventional Namespace 不同，這裡的 ns->size 直接使用傳入的 size，而不是透過 `cpp.pba_pcent` 重新計算。
- [ ] API / Command Differences
NVMeVirt 透過不同的 I/O command handler，分別處理 Conventional Namespace 與 Zoned Namespace（ZNS）的 NVMe I/O commands。在 Namespace 初始化時，Conventional Namespace 設定 conv_proc_nvme_io_cmd() 作為 I/O command handler，而 ZNS Namespace 則設定 zns_proc_nvme_io_cmd()。兩者皆透過 cmd->common.opcode 判斷命令類型，再呼叫對應的處理函數。
    1. Conventional Namespace
    在` conv_proc_nvme_io_cmd()` 中，先透過 `NVMEV_ASSERT(ns->csi == NVME_CSI_NVM)` 確認 Namespace 使用 NVM Command Set，接著根據 NVMe command opcode 分派命令。
    目前此函數明確處理三種命令：
    Write（nvme_cmd_write）：呼叫 `conv_write() `處理寫入請求。
    Read（nvme_cmd_read）：呼叫` conv_read()` 處理讀取請求。
    Flush（nvme_cmd_flush）：呼叫 `conv_flush()` 處理 Flush 請求。

    2. Zoned Namespace（ZNS）
    在 `zns_proc_nvme_io_cmd()` 中，先透過 `NVMEV_ASSERT(ns->csi == NVME_CSI_ZNS)` 確認 Namespace 使用 Zoned Namespace Command Set，並透過 `NVMEV_ASSERT(ns->nr_parts == 1)` 確認目前只支援單一 partition。
    相較於 Conventional Namespace，ZNS handler 除了一般讀寫命令外，也處理 Zone Append 與 Zone Management 相關命令：
    **Write**（nvme_cmd_write）：呼叫 `zns_write()` 處理寫入請求。
    **Zone Append**（nvme_cmd_zone_append）：同樣呼叫 `zns_write()` 處理寫入請求。
    **Read**（nvme_cmd_read）：呼叫 `zns_read()` 處理讀取請求。
    **Flush**（nvme_cmd_flush）：呼叫 `zns_flush()` 處理 Flush 請求。
    **Zone Management Send**（nvme_cmd_zone_mgmt_send）：呼叫 `zns_zmgmt_send()` 處理 Zone 管理操作。
    **Zone Management Receive**（nvme_cmd_zone_mgmt_recv）：呼叫 `zns_zmgmt_recv()` 處理 Zone 資訊查詢。
    3. 兩者的主要差異
    Conventional Namespace 的 I/O handler 主要處理一般的 Read、Write 與 Flush 命令；ZNS Namespace 則額外處理 **Zone Append、Zone Management Send 和 Zone Management Receive**。其中，Zone Append 允許將資料追加至指定 Zone，由裝置依照該 Zone 的寫入規則決定實際寫入位置；Zone Management Send 則用於執行 Zone 管理操作，而 Zone Management Receive 可用於取得 Zone 相關資訊。
- [ ] Data Placement Policies
    在 Conventional FTL 中，Host 指定要寫入的起始 LBA，而 FTL 負責將邏輯頁面轉換成 NAND 的實體位址。在 `conv_write()` 中，程式會先查詢既有的位址映射；如果該邏輯頁面已有資料，便將舊的實體頁面標記為無效，再透過 `get_new_page()` 配置新的實體頁面，並更新正向與反向映射表。此外，程式會依照 LPN 除以分割區數量的餘數，將邏輯頁面分配至不同的 FTL 分割區。
    在 ZNS FTL 中，寫入行為受到 Zone 邊界、Zone 狀態與寫入指標（Write Pointer, WP）的限制。`__zns_write()` 會檢查起始 LBA 是否等於該 Zone 目前的 WP，並確認 Zone 的狀態及可用資源是否允許寫入。通過檢查後，程式會更新 WP。若使用 Zone Append 命令，程式會先將起始 LBA 設為該 Zone 目前的 WP，再進行後續檢查。與 Conventional FTL 不同， ZNS 透過 `__lpn_to_ppa()` 取得實體位址，而不是使用 Conventional FTL 中的 `get_new_page()` 配置路徑。
    兩種實作都會模擬 NAND 寫入延遲，但在寫入位置的限制與實體位址的取得方式上不一樣。Conventional FTL 主要由裝置內部管理邏輯位址與實體位址的映射，以及實體頁面的配置；ZNS 則透過 Zone 層級的寫入規則，讓 Host 能夠更明確地控制資料寫入的位置。
- [ ] Zone Management vs. Hidden FTL
Conventional FTL 與 ZNS FTL 的主要差異，在於資料位置與儲存空間管理責任的分配方式。
在 Conventional FTL 中，Host 透過 LBA 存取資料，而裝置內部的 FTL 負責管理邏輯頁面與 NAND 實體頁面的映射。在 NVMeVirt 的 `conv_write()` 中，`get_maptbl_ent()` 用於查詢既有映射，`get_new_page()` 用於配置新的實體頁面，而 `set_maptbl_ent()` 則負責更新映射。這些內部管理機制對 Host 隱藏，因此 Host 不需要直接管理 NAND 實體頁面的配置。
ZNS 則透過 Zone Management 命令與寫入指標，讓 Host 能夠更明確地管理資料寫入的位置。在 NVMeVirt 中，`zns_proc_nvme_io_cmd()` 將 Zone Management Send 與 Zone Management Receive 分別交由 `zns_zmgmt_send()` 和 `zns_zmgmt_recv()` 處理；`__zns_write()` 則會檢查 Zone 狀態、寫入邊界與目前的 WP，並在合法寫入後更新 WP。
Conventional FTL 將較多的位址映射與實體頁面配置工作交由裝置內部處理；ZNS 則透過 Zone 層級的管理介面，讓 Host 必須遵守明確的寫入限制。


### Show: modified NVMeVirt printing/logging parallelism stats. (10%)

#### Channel 映射

`__lpn_to_ppa()` 使用下列順序決定實體位址：

```text
sdie = (zone_id * dies_per_zone) % total_luns
die  = sdie + ((zone_offset_pages / pages_per_oneshot) % dies_per_zone)
channel = die % channels
```

本次設定是 8 channels、每個 channel 2 LUNs、`DIES_PER_ZONE=1`，所以
`total_luns=16` 且第二項恆為 0。
每個 zone 的所有頁面都在同一個 die，`channel=(zone_id % 16) % 8=zone_id % 8`；
zone 0–7 對應 channel 0–7，zone 8–15 再對應 channel 0–7。
若 `DIES_PER_ZONE` 改變，單一 zone 可能跨 channel，不能再直接使用 `zone_id % 8`。

#### 統計程式

修改 `zns_ftl.h` 與 `zns_ftl.c`，依實際 channel/zone 數量配置
`ch_busy_until` 和 `zone_busy_until`，卸載 namespace 時釋放。
修改 `zns_read_write.c`：每次真正呼叫 `ssd_advance_nand()` 後，
用該 NAND 命令的 `ppa.g.ch` 與完成時間更新對應 channel 和 zone；
因此一筆請求若碰到數個 channel，也會分別記錄。
只有 `ret->status == NVME_SC_SUCCESS` 的讀寫命令才印統計。
`bool handled` 只表示 handler 接受命令，不能作為 NVMe 成功條件。

每筆成功 I/O 到達時，程式掃描完成時間大於 `req->nsecs_start` 的項目，
印出此時仍有模擬 NAND 工作待完成的 channel 與 zone 數。
v2 log 格式如下，數字僅作格式示例：

```text
[ZNS Parallelism v2] Pending NAND Channels: 4 / 8, Pending NAND Zones: 4 / 16 (Total IOs: 1234, Op: write)
```

這是**請求到達時的樣本**，包含已排隊、尚未完成的 NAND 工作；
不能解讀成時間加權的 NAND bus 使用率。
每筆成功 I/O 都輸出一行 `pr_info`，因此量測仍含 logging 負擔；
兩種檔案系統必須使用同一版模組與相同設定。

#### 工作負載與有效性

`ssd_config.h` 設定 `WRITE_EARLY_COMPLETION=0`、
`NAND_PROG_LATENCY=50000000` ns，讓寫入完成時間涵蓋模擬 NAND programming。
50 ms 是為了展示重疊而放大的教學設定，不代表實體 SSD 延遲。
在目前 64 MiB zone 設定下，四個 fio jobs 分別寫 zone 0–3，對應 channel 0–3：

```bash
sudo fio --name=multi_zone_test --filename=/dev/nvme0n2 --ioengine=io_uring --direct=1 --rw=write --bs=64k --size=64M --iodepth=2 --numjobs=4 --offset_increment=64M --zonemode=zbd --group_reporting
```

先前 `iodepth=32` 的畫面若出現 `Need to increase array size`，
表示 `channel_model.c` 的時間視窗不足，模型會直接返回 request time；
該次效能與平行度結果不可採用。上述較低的 depth 仍須以沒有該警告、
沒有 WP 或 I/O error 且 fio 成功的實際 log 為準。
這次程式修改後需在虛擬機重建模組並重新收集 v2 log；
舊 `[ZNS Parallelism]` 截圖只能標成舊版示範，不能當成 v2 量測。

### Compare: differences in parallelism utilization between ZoneFS and F2FS workloads(graphs/tables/logs). (10%)
本節的舊截圖與舊 kernel log 使用 v1 統計；程式修改後須在虛擬機用相同模組、scheduler、fio 參數重測 ZoneFS 與 F2FS，
並收集同次的 fio JSON 與 包含 `[ZNS Parallelism v2]` 的 kernel log。
結果用 `python3 hw1_parallelism/analyze.py hw1_parallelism/results --workers 4 --repeat 2` 產生表與圖。
平均值為每筆成功 ZNS write 到達時的 pending NAND channel/zone 數（包含當時尚未完成的讀取工作），僅用來比較這兩個固定 4 workers 的 workload。
若 log 出現 `Need to increase array size` 等模型錯誤，該次結果不納入比較。

為了讓 1 GiB namespace 提供至少 10 個 zones，將 zone size 從 256 MiB 改為 64 MiB，共有 16 個 zones。
`#define ZONE_SIZE MB(64) ` in ssd_config.h
`sudo insmod nvmev.ko memmap_start=4G memmap_size=2049M cpus=0,1,2,3`
make Fake Block Device
把 loop0  放 Metadata，把 nvme0n2 當作擴充硬碟 (放 Data)：
```bash
dd if=/dev/zero of=f2fs_meta.img bs=1M count=100
100+0 records in
100+0 records out
104857600 bytes (105 MB, 100 MiB) copied, 0.184045 s, 570 MB/s

sudo losetup -f --show f2fs_meta.img
/dev/loop0
```

下載zonefs tools:
```
sudo apt-get install -y git build-essential autoconf libtool pkg-config uuid-dev libblkid-dev
git clone https://github.com/westerndigitalcorporation/zonefs-tools.git
cd zonefs-tools
./autogen.sh
./configure
make
sudo make install
```
測試 ZoneFS
ZoneFS 會把硬碟的每一個 Zone 直接變成一個檔案。
接著對前 4 個檔案寫入。
掛載和格式化
```
sudo umount /mnt/zonefs 2>/dev/null
sudo mkfs.zonefs -f /dev/nvme0n2

sudo mount -t zonefs /dev/nvme0n2 /mnt/zonefs

mount | grep zonefs
/dev/nvme0n2 on /mnt/zonefs type zonefs (rw,relatime,errors=remount-ro)
```


