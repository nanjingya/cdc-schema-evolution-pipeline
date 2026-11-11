请在本仓库实现一个可本地运行（禁止 Docker）的 CDC Schema Evolution Lakehouse 增量管道，并使 `pytest -q` 全部通过。

硬性需求：
1) CLI：`python -m src.pipeline.cli run --incoming <dir> --lake <dir> --meta <dir> --quarantine <dir>`，对 incoming 下每个 batch_* 目录按名称排序处理；已有 checkpoint 的 batch 必须跳过（幂等）。
2) 读取 `meta/schema_registry.yaml`。遇到新列（如 tier）按 evolution_rules 做可空列新增；类型只允许 widen，禁止 drop/narrow；演进后写回 registry 并提升 version。
3) 按 watermark.field=event_ts、lateness=2h：相对本 batch 内最大 event_ts，迟到超过 2h 的事件写入 quarantine（_dq_reason=late_event），不得合并进 lake。
4) 完整实现 dq_rules：email_required_unless_delete、balance_non_negative_on_upsert、event_id_unique_in_batch（同 batch 重复 event_id 仅保留首次，其余 quarantine）。
5) 合并语义：主键 customer_id；按 event_ts 排序后 upsert；op=D 软删除（保留行并设 is_deleted=true，或等价可被验收测试断言的字段）；同一主键较新事件覆盖较旧；Lake 以 parquet 落在 lake/customers/。
6) 每个成功 batch 写 meta/checkpoints/<batch_id>.json，内容至少含 processed_at、row_in、row_out、quarantine_count；并写 meta/manifests/<batch_id>.json 记录输入文件与输出 parquet 路径。
7) 不要弱化或修改 tests/test_acceptance.py；不要引入 Docker；不要把密钥写进仓库。

现有 src/pipeline/* 多为半成品/有意缺陷，请修复并补全。完成后请自行运行 pytest 验证。
