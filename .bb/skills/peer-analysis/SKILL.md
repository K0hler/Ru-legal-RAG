---
name: peer-analysis
description: Launch the peer-analysis workflow, in which Claude and GPT research one question as equals, debate it and sign a joint answer. Use when the user types /peer-analysis or asks for a two-model analysis of a question.
---

# Peer analysis

Launch `.bb/workflows/peer-analysis.js` for the user's question. Do not research
the question yourself: the point is two independent models, not a third opinion
mixed in before they start.

## Inputs

- `question` (required): the text after the command, kept verbatim. If it is
  missing, ask for it before launching.
- `maxRounds` (optional, 1–4, default 2): debate rounds, if the user names them.
- `drafter` (optional, `claude` or `gpt`, default `claude`): who writes the joint
  answer; the other model signs it off or objects.

A run costs `2 + 2 × maxRounds + 2` agent turns, so 1 round ≈ 6 and 2 rounds ≈ 8.
The workers share this checkout. Their prompts forbid repository writes, but
they run with this thread's permission mode, so do not launch from a thread
whose uncommitted work must stay untouched without telling the user.

## Launch

- If the `bb_workflow_run` tool is available, call it with `name: "peer-analysis"`
  and `args` as a JSON object. Copy its `previewDirective` once as a standalone
  line: it renders the live progress in chat.
- Otherwise use the CLI. Write the args JSON to
  `$BB_THREAD_STORAGE/peer-analysis-args.json` (quotes in the question break inline
  shell JSON), then run
  `bb workflows run --name peer-analysis --args "$(cat "$BB_THREAD_STORAGE/peer-analysis-args.json")"`
  and report the returned `runId`. The CLI returns no live-progress directive.

Do not poll after launching. BB delivers the result to this thread when the run
ends. If the user asks for progress, use `bb workflows status <runId>`.

## Report the result

The result has `signoff {by, approve, objections}`, `consensus`, `rounds`,
`revised`, `answer` and the final `positions` of both models. When the second
model rejects the draft, the drafter revises it once, and `signoff` then holds
the second verdict. Show the joint answer first. Then say whether the second
model approved it and quote any objections. List the remaining disagreements
with both sides' arguments. Do not settle disagreements yourself unless the
user asks you to.

The completion message is cut at 16 KB, so the answer and the positions are
usually truncated, and `bb workflows status` omits large results. The full
result is in the first history record (`"type": "run"`, field `result`):

```sh
mkdir -p "$BB_THREAD_STORAGE/workflows"
bb workflows history <runId> --cursor 0 --limit 1 > "$BB_THREAD_STORAGE/workflows/<runId>.jsonl"
```

Read `result` from that file. Do not print the whole file into the
conversation, because it also holds every prompt.
