# HW1 最後一題：ZoneFS / F2FS parallelism 比較（固定 n=4、r=2）

本目錄提供工作設定產生器與結果分析工具；本版分析需要更新後的 NVMeVirt v2 統計程式。
工具不會自動格式化、重設 zone 或掛載檔案系統。下列 sudo 指令由你確認測試裝置後手動執行。

## 配置與控制變數

保留 conventional namespace /dev/nvme0n1；本題兩種檔案系統輪流使用 /dev/nvme0n2。
沿用已完成的 cpus=0,1,2,3、WRITE_EARLY_COMPLETION=0、NAND_PROG_LATENCY=50000000、DIES_PER_ZONE=1。
沿用最後一題已改好的 ZONE_SIZE=64 MiB，不改回前題的 256 MiB。
1 GiB ZNS / 64 MiB = 16 zones；「至少 10 個」指 zone 數量，不是 zone size。
但 zone 數量並非唯一限制：F2FS 還需要 metadata、對齊及 GC 保留空間，16 zones 不保證自動格式化成功。
CPU 0 是 dispatcher，CPU 1–3 是 emulator workers；fio worker 數是另一個變數。

本流程只比較固定 4 個 fio workers 的 ZoneFS 與 F2FS，各保存一組成功結果，統一使用 r2 檔名。
`n4` 表示 4 個 workers；`r2` 只是本次測試編號，不會自動執行兩次。
所有測試固定總寫入 32 MiB，每個 worker 寫 8 MiB；
bs=64 KiB、direct=1、libaio、iodepth=1，每 worker 一筆 outstanding I/O。
這份結果只支持固定 4 workers 下的比較，不用來推論增加 workers 後的擴展性。
不要使用 psync：目前 ZoneFS 的同步 direct write 路徑使用 Zone Append，
而本份 NVMeVirt 的 admin.c 明確註明尚未支援此命令；completion 沒有正確回傳寫入 LBA，
會出現 Corrupted write pointer 0 / EIO。libaio 改走非同步 direct I/O 路徑以避開此限制。
兩種 FS 都改用 libaio，舊 psync 結果不能混入同一組比較。
這是小容量、空檔案系統的順序寫入測試，不代表長時間 GC/穩態表現。
不加 time_based，避免 ZoneFS 寫滿後回到開頭違反順序寫入限制。
產生器使用 file_append=1：避免 fio 3.28 準備空檔案時先 unlink；ZoneFS 不允許刪除 zone 檔案。
兩個 FS 都使用此設定，並要求每次測試從空檔案開始。
allow_file_create=0 本身不會阻止 fio 在準備階段嘗試 unlink。
若 ZoneFS 已成為 ro，先保存錯誤 log 並檢查裝置，不能將該次失敗執行納入圖表。

## 準備（在 repo 根目錄執行）

本版是 mq-deadline 下的重測流程。兩種 FS 都要重測，仍固定 n4-r2，
新結果統一存到 `hw1_parallelism/results/`，直接覆寫先前同名的 none 測試檔案。
同一次測試的 .fio、.json、.kernel.log、.zones.txt 都使用相同 BASE，避免新舊結果混用。
每份 kernel log 只收一次 fio；不要讓同一個 dmesg 收集程序跨多次測試。

```bash
cd /home/memory/nvmevirt
mkdir -p hw1_parallelism/results
echo mq-deadline | sudo tee /sys/block/nvme0n2/queue/scheduler
cat /sys/block/nvme0n2/queue/scheduler
cat /sys/block/nvme0n2/queue/scheduler > hw1_parallelism/results/scheduler.txt
uname -a > hw1_parallelism/results/environment.txt
cat /proc/cmdline >> hw1_parallelism/results/environment.txt
git rev-parse HEAD >> hw1_parallelism/results/environment.txt
git diff > hw1_parallelism/results/source.patch
fio --version >> hw1_parallelism/results/environment.txt
lsblk -o NAME,SIZE,MODEL,MOUNTPOINTS >> hw1_parallelism/results/environment.txt
sudo nvme zns report-zones /dev/nvme0n2 > hw1_parallelism/results/initial-zones.txt
```

確認顯示 `none [mq-deadline]`，方括號表示正在使用的 scheduler。
`[none] mq-deadline` 表示仍在用 none，不能當作已切換。
模組重新載入或裝置重建後要重新確認；若裝置名稱改變，也要同步調整本文所有裝置路徑。
本環境較舊核心的 zoned F2FS 需要 mq-deadline 協調 zone 寫入派送順序；
先前 none 下曾出現 WP error，是否解決仍須由本次無錯誤的結果確認。
參考：https://zonedstorage.io/docs/filesystems/f2fs

可在切換 FS 前額外保存 source / notes / 舊結果（不包含 mounted FS 的資料）：

```bash
tar -czf hw1_parallelism/results/prior-work.tar.gz HW1.md Kbuild ssd_config.h main.c io.c nvmev.h zns_ftl.c zns_ftl.h zns_read_write.c nvmev.ko zonefs_result.log
```

## ZoneFS

### ZoneFS：格式化與掛載

先查看目前掛載狀態：

```bash
findmnt /mnt/f2fs
findmnt /mnt/zonefs
```

若目前是 F2FS，先保存需要的資料及舊結果，再卸載：

```bash
sudo umount /mnt/f2fs
```

**從 F2FS 切換到 ZoneFS 需要重新格式化 /dev/nvme0n2，會清除上面的 F2FS 資料。**
確認此裝置未掛載後執行；不要對 /dev/nvme0n1 操作：

```bash
sudo mkdir -p /mnt/zonefs
sudo mkfs.zonefs -f /dev/nvme0n2
sudo mount -t zonefs /dev/nvme0n2 /mnt/zonefs
findmnt /mnt/zonefs
cat /sys/block/nvme0n2/queue/scheduler
```

若裝置已是 ZoneFS、只是尚未掛載，只需以下指令，不必 mkfs：

```bash
sudo mkdir -p /mnt/zonefs
sudo mount -t zonefs /dev/nvme0n2 /mnt/zonefs
```

若已掛載 ZoneFS，跳過上述格式化／掛載指令，直接檢查狀態。
同一個 ZNS namespace 不能同時供 ZoneFS 與 F2FS 掛載使用。

### ZoneFS：執行固定 4 workers、r2

若 /mnt/zonefs 已掛載，不需要重新格式化。先確認 seq/0 到 seq/3 均存在，並檢查掛載狀態：

```bash
findmnt /mnt/zonefs
ls -l /mnt/zonefs/seq/{0,1,2,3}
```

OPTIONS 開頭的 rw 才是目前可寫；errors=remount-ro 只是遇到錯誤時轉為唯讀的策略。
若目前是 ro，先保存錯誤並確認原因，不要直接重跑 fio。
若其中有需要保留的資料，先複製到 host 的其他目錄；下方 truncate 會清除選定 zone 的資料。
只重設這次測試會使用的 zone，不碰 conventional namespace。

原本 none 下的 zonefs-n4-r2 不可直接搭配本次 mq-deadline 的 F2FS 結果。
只有已完成本次 mq-deadline 下的成功測試且 log 配對完整，才可跳過重測。
以下重測會覆寫同名結果；需要保留時先備份。BASE 是 Bash 變數，新 terminal 不會自動繼承。

```bash
N=4
R=2
BASE="hw1_parallelism/results/zonefs-n${N}-r${R}"
for ((i=0; i<N; i++)); do sudo truncate -s 0 "/mnt/zonefs/seq/$i" || break; done
python3 hw1_parallelism/make_job.py zonefs "$N" > "$BASE.fio"
```

確認四個 truncate 都成功；若任一失敗，先停止，不能繼續 fio。

另一個 terminal：在重設 zone 完成後、fio 前開始收集，只收集這次測試。

```bash
cd /home/memory/nvmevirt
sudo dmesg --follow-new > hw1_parallelism/results/zonefs-n4-r2.kernel.log
```

原 terminal：

```bash
sudo fio "$BASE.fio" --output-format=json --output="$BASE.json"
```

fio 結束後立即在 log terminal 按 Ctrl+C，再回原 terminal 保存 zone report，
避免把後續診斷或下次測試也收進 workload log：

```bash
sudo nvme zns report-zones /dev/nvme0n2 > "$BASE.zones.txt"
```

完成後在 log terminal 按 Ctrl+C。確認 fio 成功，並確認 kernel log 有 [ZNS Parallelism]。
每個 run 必須單獨收 log；不要讓不同測試共用同一份 log。
ZoneFS 的 n4-r2 成功且保存完整後，再切換至 F2FS。
`--output="$BASE.json"` 的等號後面不要加空白。

## F2FS

目前已在本環境驗證 `-o 50` 格式化成功，並成功以 rw 掛載到 /mnt/f2fs。
但重測必須從空的 F2FS 開始；先前已執行過 fio 的 F2FS，請保存結果後重新格式化。
若剛切換回 ZoneFS，依下方指令重新建立 F2FS。

### F2FS：首次建立與掛載

切換格式會清除 /dev/nvme0n2 上的 ZoneFS 內容，並非只改掛載點。
先保存上方所有 ZoneFS 結果及需要的檔案。以下不格式化 /dev/nvme0n1，
也不覆寫你已有的 f2fs_meta.img，而使用本題新建的 metadata image。

```bash
sudo umount /mnt/zonefs
```

若目前掛載的是舊 F2FS，改執行 `sudo umount /mnt/f2fs`。
確認兩個掛載點都已卸載，再繼續：

```bash
test ! -e hw1_parallelism/meta.img && truncate -s 128M hw1_parallelism/meta.img
sudo losetup -j "$PWD/hw1_parallelism/meta.img"
```

若最後一行沒有輸出，才建立新的 loop mapping：

```bash
META=$(sudo losetup --find --show "$PWD/hw1_parallelism/meta.img")
echo "$META"
```

若已顯示 mapping，例如 /dev/loop0，直接設定 `META=/dev/loop0`，不要重複連接。
確認 META 是這個 image 對應的 loop device，再格式化與掛載：

```bash
sudo mkdir -p /mnt/f2fs
sudo mkfs.f2fs -f -m -o 50 -c /dev/nvme0n2 "$META"
sudo mount -t f2fs "$META" /mnt/f2fs
findmnt /mnt/f2fs
df -h /mnt/f2fs
cat /sys/block/nvme0n2/queue/scheduler
```

記下 META 的實際路徑，不要假設一定是 /dev/loop0。新 terminal 必須重新設定此變數。
若格式化或掛載失敗，停止收集效能結果，保存錯誤與 dmesg；不要更動前題程式來湊出結果。

本環境不指定 -o 時曾出現 Device size is not sufficient for F2FS volume。
較舊 f2fs-tools 的自動 overprovision 搜尋範圍可能無法容納這個小容量、大 section 配置所需的保留空間。
因此上方改為明確指定 -o 50（overprovision 設定值 50%，不是把一半 ZNS 改成 conventional）。
本環境已驗證此設定成功，不需要修改 namespace 容量、zone size 或前題程式。
報告記錄這個 mkfs 參數；實際可用容量還會扣除 metadata 與其他保留空間，以 df -h /mnt/f2fs 為準。
若仍失敗，保存診斷輸出：sudo mkfs.f2fs -f -m -o 50 -d 1 -c /dev/nvme0n2 "$META"。

成功輸出範例（本次實測）：

```text
Info: Overprovision ratio = 50.000%
Info: Overprovision segments = 448 (GC reserved = 384)
Info: format successful

TARGET    SOURCE     FSTYPE OPTIONS
/mnt/f2fs /dev/loop0 f2fs   rw,...

Filesystem      Size  Used Avail Use% Mounted on
/dev/loop0      1.1G  961M  128M  89% /mnt/f2fs
```

`rw` 表示目前可讀寫；128 MiB available 足夠本次合計 32 MiB 的測試。
格式化後顯示的 Used 961M 主要反映 metadata 與保留空間，不代表已寫入 961 MiB 的測試資料。
實際 loop 編號與容量顯示以你的輸出為準。

### F2FS：執行固定 4 workers、r2

本流程只執行一組 F2FS n4-r2，使用上方剛格式化的空檔案系統。
不要對已寫過資料的同一組檔案直接重跑，否則 file_append=1 會接續寫入。
設定 N、R 並產生工作設定：

```bash
cd /home/memory/nvmevirt
mkdir -p hw1_parallelism/results
N=4
R=2
BASE="hw1_parallelism/results/f2fs-n${N}-r${R}"
python3 hw1_parallelism/make_job.py f2fs "$N" > "$BASE.fio"
cat "$BASE.fio"
```

確認設定包含 ioengine=libaio、iodepth=1、bs=64k、direct=1、file_append=1、size=8m，
以及 w0 到 w3 四個 jobs。每個 worker 寫入 8 MiB，合計 32 MiB。

另一個 terminal，在格式化／掛載完成後開始記錄：

```bash
cd /home/memory/nvmevirt
sudo dmesg --follow-new > hw1_parallelism/results/f2fs-n4-r2.kernel.log
```

原 terminal：

```bash
sudo fio "$BASE.fio" --output-format=json --output="$BASE.json"
```

fio 結束後立即在 log terminal 按 Ctrl+C，再保存 zone report：

```bash
sudo nvme zns report-zones /dev/nvme0n2 > "$BASE.zones.txt"
```

完成後在 log terminal 按 Ctrl+C。不要把格式化、掛載或後續 sync 計入 workload log。
確認 fio 成功，且該次 kernel log 沒有新增 WP error、I/O error、Corrupted write pointer 或 ioremap 錯誤。
保存以下三份檔案，JSON 與 kernel log 必須來自同一次測試：

```text
hw1_parallelism/results/f2fs-n4-r2.json
hw1_parallelism/results/f2fs-n4-r2.kernel.log
hw1_parallelism/results/f2fs-n4-r2.zones.txt
```

此測試量測 direct write 完成，沒有宣稱涵蓋 end_fsync 的耐久性成本。
Metadata 在 host loop device，其 I/O 不會出現在 ZNS parallelism log，需在報告註明。
報告同時記錄：128 MiB metadata loop device、mkfs.f2fs -o 50，以及格式化後可用空間 128 MiB。

若需回復空的 ZoneFS（不能復原原資料），先完成並保存 F2FS 結果，再：

```bash
sudo umount /mnt/f2fs
sudo losetup -d "$META"
sudo mkfs.zonefs -f /dev/nvme0n2
sudo mount -t zonefs /dev/nvme0n2 /mnt/zonefs
```

## 用 v2 log 比較結果

更新後的模組在每筆成功的 ZNS read/write 到達時印出一筆 `[ZNS Parallelism v2]`：
`Pending NAND Channels` 與 `Pending NAND Zones` 分別是此時仍有模擬 NAND 工作待完成的 channel 和 zone 數。
channel 取自實際 NAND 命令的 `ppa.g.ch`；同一請求若涉及多個 channel，會分別追蹤。
完成時間取自 `ssd_advance_nand()`，不再以含有其他階段延遲的 host completion 時間代替。
這是「請求到達時」的樣本平均，不是以時間加權的實體 NAND bus 使用率。
每筆請求寫一行 kernel log 會增加量測負擔；ZoneFS 與 F2FS 要使用相同模組與設定。

目前目錄內原有的 `n4-r2` kernel log 是舊版格式，不能當作 v2 結果。
在虛擬機內使用更新後的模組，依上方流程各重跑一次 ZoneFS 與 F2FS；
兩次都要在格式化／掛載完成後、fio 開始前單獨啟動 `dmesg --follow-new`，
並在 fio 結束後停止。保留同次執行的 `.fio`、`.json`、`.kernel.log` 和 `.zones.txt`。
不要混入前一次測試的檔案。

確認 log 有下列格式（數字僅示意）：

```text
[ZNS Parallelism v2] Pending NAND Channels: 4 / 8, Pending NAND Zones: 4 / 16 (Total IOs: 1234, Op: write)
```

在虛擬機內產生比較表與圖：

```bash
python3 hw1_parallelism/analyze.py hw1_parallelism/results --workers 4 --repeat 2
```

工具會檢查 fio job 成功且總共寫入 32 MiB、v2 log 存在且編號連續、channel/zone 總數一致。
圖表只在成功的 ZNS write 到達時取樣，避免檔案系統讀取請求改變寫入比較的樣本比例；
每個樣本的 pending channel/zone 數仍包含當時尚未完成的讀取與寫入 NAND 工作。
如果 log 出現 `WP error`、`Need to increase array size`、`No free entry` 等錯誤，工具會拒絕採用該次資料。
後兩種訊息表示 channel model 無法預約那麼遠的模擬時間，不能解讀成正常排隊；
需降低直接 I/O 示範的 `iodepth` 或調低人為放大的 latency，並以相同設定重跑兩個 FS。

輸出在 `results/summary.csv`、`throughput.svg`、`channels.svg`、`zones.svg`。
表中的 `mean_pending_nand_channels`、`peak_pending_nand_channels` 和 `sampled_pending_channel_percent`
是成功 I/O 到達時取樣的 pending NAND 數量與比例。圖只會有 n=4 的點；
這組固定 4 workers、單次測試不能推論 worker 擴展性，也沒有重複測試誤差估計。

目前 `DIES_PER_ZONE=1` 時，每個 zone 固定映射到一個 channel，恰好等於 `zone_id % 8`。
ZoneFS 的四個 worker 寫不同 zone；F2FS 的資料放置由 allocator 決定，可能集中於較少 zone。
以更新後的實測 log 與 fio JSON 填寫報告，不沿用舊圖的數值。
F2FS metadata 位於 host loop device，其 I/O 不在 ZNS log 中。
50 ms programming latency 是教學用放大的模擬設定，不代表真實 SSD 效能。
