# Historical PAM checkpoints

`assurance/HANDOFF_STATE.json` is the single mutable `current` handoff.

Files in this directory are immutable `historical_checkpoint` snapshots created only at material boundaries such as a validated milestone, session end, material plan change, agent transfer, or blocked state.

They exist to preserve what was known and authorized at that point in time. They never override live repository, issue, or CI state.

Create a checkpoint explicitly:

```bash
python tools/create_handoff_checkpoint.py \
  --name 2026-09-05-example-milestone \
  --created-at 2026-09-05T18:44:00Z \
  --reason milestone_transition

make docs-sync
make check
```

Rules:

- never overwrite an existing checkpoint;
- never edit a historical checkpoint merely because current understanding changed;
- create a new checkpoint for a new material state;
- keep hidden benchmark/oracle material out of agent-visible handoffs and checkpoints;
- run the pinned PAM validator over every checkpoint in CI;
- generated README/status documentation may list checkpoints, but checkpoints are evidence of past state, not the authority for current state.

The first archived checkpoint is `2026-09-05-executable-replay-frontier.json`.
