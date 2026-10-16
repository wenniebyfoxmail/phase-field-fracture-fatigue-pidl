# E022 v1 exact transfer and single launch — approval version

Status: PREPARED ONLY. No SSH, transfer or training performed. Sender: Mac wenxiaofang; recipient drtao@172.16.100.2/GPUServer8 via existingTunnelblick. Scope: two exact files below to a freshroot, single detached dispatcher after allpreflights; three serial runs, no reattempt/fallback. Full proposed resource sharing/pairing/LR/stop conditions are production_plan.json. This action requires the user's explicit approval of this version.

## Two final files

- `E022_a540888.bundle`: 100718 bytes, SHA256 `ead5a95d9877a9ad521007536504617392245541501f042d1bf949168717cfc4`
- `prepare_and_dispatch.sh`: 13255 bytes, SHA256 `b3970a5da507751ff3ec454abac1683f6fa83739cba0bc0931f8af1ac5f3e809`

## Exact commands (not executed)

Atomic newroot creation; if it exists or an outcome is uncertain, stop and inspect read-only rather than overwrite/retry. Filetransfer failure is investigated before any retransmission or launch. The launch command verifies bothtransferredhashes, returns PID; verify actual dispatcher status/source/cwd afterward. A lost SSH session does not prove the job stopped.

```bash
ssh -F /dev/null -o BatchMode=yes -o ConnectTimeout=15 drtao@172.16.100.2 'umask 077
[ "$(id -un)" = drtao ] || exit 1
[ "$(hostname)" = GPUServer8 ] || exit 1
mountpoint -q /mnt/data2 || exit 1
mkdir /mnt/data2/drtao/wennie/S04-E022-last-leak-a540888-20261016-v1'

scp -F /dev/null -o BatchMode=yes -o ConnectTimeout=15 /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E022/producer_submission_v1/E022_a540888.bundle /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E022/producer_submission_v1/prepare_and_dispatch.sh drtao@172.16.100.2:/mnt/data2/drtao/wennie/S04-E022-last-leak-a540888-20261016-v1/

ssh -F /dev/null -o BatchMode=yes -o ConnectTimeout=15 drtao@172.16.100.2 'cd /mnt/data2/drtao/wennie/S04-E022-last-leak-a540888-20261016-v1 || exit 1
[ "$(sha256sum /mnt/data2/drtao/wennie/S04-E022-last-leak-a540888-20261016-v1/E022_a540888.bundle | cut -d " " -f 1)" = ead5a95d9877a9ad521007536504617392245541501f042d1bf949168717cfc4 ] || exit 1
[ "$(sha256sum /mnt/data2/drtao/wennie/S04-E022-last-leak-a540888-20261016-v1/prepare_and_dispatch.sh | cut -d " " -f 1)" = b3970a5da507751ff3ec454abac1683f6fa83739cba0bc0931f8af1ac5f3e809 ] || exit 1
mkdir -p logs || exit 1
nohup bash /mnt/data2/drtao/wennie/S04-E022-last-leak-a540888-20261016-v1/prepare_and_dispatch.sh > /mnt/data2/drtao/wennie/S04-E022-last-leak-a540888-20261016-v1/logs/dispatcher.log 2>&1 < /dev/null &
printf '"'"'dispatcher_pid=%s\n'"'"' "$!"'
```

## Scope and commitments

GPU0 sharing is proposed only while >8GiBfree, no zero-process condition; log others without intervention. No environment install, globalconfiguration, push, model/dataexport to a reviewer, GPUchange or newexperiment. Old E019/E021 sources only read/copy. After all3finished, retrieve9filesperstate+logs/preflights/manifests/aggregate, verify numericalintegrity and actualLR, compare E019/E021 and update researchrecord. Original .001 primarygate and separate background/damage interpretation retained. Newattempt/package/content change requires another reviewable plan; no automaticretry. Runtime,host,mount or assetabsencestops atpreflight with logs.
