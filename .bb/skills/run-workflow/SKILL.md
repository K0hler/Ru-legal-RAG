---
name: run-workflow
description: List, launch, check or stop this project's saved BB workflows in .bb/workflows. Use when the user types /run-workflow or asks to run or manage a saved workflow by name.
---

# Run a saved workflow

Saved workflows live in `.bb/workflows/<name>.js`. Each file starts with a literal
`export const meta` block that holds the name, the description, the optional
`inputSchema` for `args`, and the phases.

## No arguments: list

Read the `meta` block of each `.bb/workflows/*.js` file. Show each workflow's
name, description and the `args` it needs, taken from `inputSchema`. Also show
recent runs from `bb workflows list --limit 10`. Offer to launch one; do not
launch anything yourself.

## `<name> <inputs>`: launch

1. Build `args` from the user's inputs according to `inputSchema`. Ask for a
   missing required input instead of inventing it.
2. Run `bb workflows validate --name <name>`. A validation error stops the
   launch; report it.
3. Launch with the `bb_workflow_run` tool (`name`, `args` as a JSON object) and
   copy its `previewDirective` once as a standalone line. Without that tool,
   write the args to `$BB_THREAD_STORAGE/<name>-args.json` and run
   `bb workflows run --name <name> --args "$(cat "$BB_THREAD_STORAGE/<name>-args.json")"`,
   then report the `runId`.
4. Do not poll. The result arrives in this thread when the run ends.

When a workflow has its own skill (for example `/peer-analysis`), follow that
skill instead, because it explains how to read the result.

## Workflow notes

- `implement-review-fix` (`task`, optional `checks` list and `maxRounds` 1–4,
  default 2): GPT implements, Claude reviews, and GPT fixes the high- and
  medium-severity findings.
  - It writes to this checkout. Before launching, check `git status --short`
    and tell the user which uncommitted files exist. The executor refuses to
    edit files that have unstaged changes or are untracked, and returns
    `status: "blocked"`. Staged-only files are fine, because its edits stay
    unstaged and show up in `git diff`.
  - Cost: 2–3 agent turns per review round.
  - In the result, show `status` (`clean`, `unresolved`, `blocked`,
    `review_failed` or `failed`), `filesChanged`, the checks with exit codes,
    `unresolved` and `minor` findings. Remind the user that nothing is
    committed: they review `git diff` and commit themselves.

## `status | stop | history <runId>`

- `bb workflows status <runId>`: compact progress and small results. A large
  result is omitted there (`resultOmitted: true`) and cut in the completion
  message. Read it from the first history record (`"type": "run"`, field
  `result`), which you get with `--limit 1` as shown below.
- `bb workflows stop <runId>`: cancel the run. Confirm with the user first,
  because running workers are stopped.
- History can hold every prompt and answer. Redirect it to a file instead of
  printing it:
  `bb workflows history <runId> --cursor 0 --limit 100 > "$BB_THREAD_STORAGE/workflows/<runId>.jsonl"`.

To resume a failed or stopped run after editing the script, run it again with
`--resume <runId>`. Successful calls before the first changed call come back
from the cache.
