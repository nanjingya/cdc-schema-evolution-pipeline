# CDC Schema-Evolution Lakehouse Lite

Local (no Docker) incremental lakehouse pipeline for customer CDC events.

## Constraints
- Python 3.11+
- No Docker / no cloud services
- Dependencies: see requirements.txt
- Entry: `python -m src.pipeline.cli run --incoming data/incoming --lake lake --meta meta --quarantine quarantine`

See `TASK_PROMPT.md` for the assignment prompt text used in the agent session.
