# 试标提交草稿（UID 236）

## User Prompt
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

## 所属领域
数据工程

## 子方向
数据采集、爬虫与 RPA
（更准确：数仓/ETL 增量管道，若选项无精确项可选「*其他」；重点子方向里最接近的是数据采集相关的增量落库清洗。若下拉仅有「数据采集、爬虫与 RPA / *其他」，选「*其他」并在备注说明 CDC schema evolution lakehouse。）

建议：若有「*其他」选其他；否则选「数据采集、爬虫与 RPA」。

## 任务类型
功能开发

## 任务难度
困难

## 语言/框架
Python, pandas, pyarrow, pytest, PyYAML

## Harness
Codex CLI

## Harness 版本
0.167.0-alpha.3.2

## 操作系统
MacOS

## 初始环境快照
https://github.com/nanjingya/cdc-schema-evolution-pipeline/commit/e8bb8e67e3a3f7b1980574d9bcbf97ac2208709a

## SessionID
01a1c9ea-1d48-71e0-a5ff-acbeaf6726ea

## TurnID/PromptID
01a1c9ea-1dcd-7521-8c70-1f2641fc4f12

## 轨迹文件
https://raw.githubusercontent.com/nanjingya/cdc-schema-evolution-pipeline/d3455bb9080a12ab7da82b98a4f51ced6f7078cf/artifacts/session-01a1c9ea-1d48-71e0-a5ff-acbeaf6726ea.jsonl

## 产物快照
https://github.com/nanjingya/cdc-schema-evolution-pipeline/commit/d3455bb9080a12ab7da82b98a4f51ced6f7078cf

## 运行录屏
https://github.com/nanjingya/cdc-schema-evolution-pipeline/raw/d3455bb9080a12ab7da82b98a4f51ced6f7078cf/artifacts/run-demo.mp4

## 交付完整性
4

## Feedback
过程问题：
在首轮探索完成后进入实现阶段前，模型出现一次会话重连（Reconnecting 1/5），导致首轮会话中断需重新开跑；正式会话中，模型先宣称要用 apply_patch，随后发现该工具不可用，才改用 heredoc 写文件，多走了一步无效规划。首次执行 pytest 时因未配置 pythonpath 触发 ModuleNotFoundError: No module named 'src'，说明其在宣称可测前没有先确认测试导入路径。手动端到端验证时又使用了被 sandbox 拒绝的 rm -rf 风格清理命令，被迫改写命令后才完成验证。

产物问题：
最终产物在功能上满足验收：pytest -q 1 passed；CLI 对 batch_001/batch_002 完成 schema 演进（registry version 升到 2 并加入 tier）、watermark 迟到隔离、三条 DQ 规则、按 event_ts 的 upsert 与软删除，以及 checkpoint/manifest。湖中最终仅保留 c2（email=b2@x.com, tier=gold, is_deleted=false），quarantine 正确包含 late_event / balance_non_negative_on_upsert / event_id_unique_in_batch / email_required_unless_delete。因此交付完整性评为 4 分：主要需求全部达成且可运行、无虚假成功，但过程存在工具误判、导入路径遗漏与非法清理命令等瑕疵，未达到“零过程缺陷的一次性完美”。

## 备注
GitHub 仓库因本机 gh 登录账号为 nanjingya，已创建在 https://github.com/nanjingya/cdc-schema-evolution-pipeline ；SSH 身份 1562600869 可访问但无该账号 API token，未能建在 1562600869 名下。录屏为验收输出翻页视频（约9秒，720p mp4），如甲方要求真实终端录屏可补录替换。
