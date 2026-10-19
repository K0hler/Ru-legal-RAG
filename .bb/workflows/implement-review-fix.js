export const meta = {
  name: "implement-review-fix",
  description: "GPT implements one task, Claude reviews the diff, GPT fixes blocking findings until the review is clean",
  inputSchema: {
    type: "object",
    required: ["task"],
    additionalProperties: false,
    properties: {
      task: { type: "string", minLength: 20 },
      checks: { type: "array", items: { type: "string", minLength: 1 }, maxItems: 10 },
      maxRounds: { type: "integer", minimum: 1, maximum: 4 },
    },
  },
  phases: [
    { title: "Implement", detail: "GPT executor writes code and tests" },
    { title: "Review", detail: "Claude checks the new diff against the task" },
    { title: "Fix", detail: "GPT addresses blocking findings" },
  ],
};

const WORK = {
  type: "object",
  required: ["status", "summary", "filesChanged", "checks"],
  properties: {
    status: { enum: ["done", "blocked"] },
    summary: { type: "string" },
    filesChanged: { type: "array", items: { type: "string" } },
    checks: {
      type: "array",
      items: {
        type: "object",
        required: ["command", "exitCode", "result"],
        properties: {
          command: { type: "string" },
          exitCode: { type: "integer" },
          result: { type: "string" },
        },
      },
    },
  },
};

const REVIEW = {
  type: "object",
  required: ["findings"],
  properties: {
    findings: {
      type: "array",
      items: {
        type: "object",
        required: ["severity", "file", "line", "problem", "fix"],
        properties: {
          severity: { enum: ["high", "medium", "low"] },
          file: { type: "string" },
          line: { type: "integer" },
          problem: { type: "string" },
          fix: { type: "string" },
        },
      },
    },
  },
};

// The checkout is shared with the user's own uncommitted work. Staged changes are
// theirs; the worker's edits must stay unstaged so `git diff` shows only them.
const GIT_RULES =
  "The repository checkout is shared with the user's unfinished work. Before editing, run `git status --porcelain`. " +
  "You may edit a file that is clean or has only staged changes. If a file you need has unstaged changes or is " +
  "untracked, do not touch it: return status \"blocked\" and say which file and why. Never stage, unstage, stash, " +
  "reset, checkout, restore or commit anything; leave your edits unstaged. Follow the nearest AGENTS.md files, " +
  "except that the user commits.";

function checksText() {
  if (args.checks && args.checks.length) return "Run these checks:\n- " + args.checks.join("\n- ");
  return "Run the acceptance checks that the nearest AGENTS.md files name for the code you change, scoped to that code.";
}

const maxRounds = args.maxRounds || 2;

let work = await agent(
  "Implement this task.\n\n" + args.task + "\n\n" + checksText() + "\n\n" + GIT_RULES +
    "\n\nReport every file you changed or created in filesChanged, and every check you ran with its exit code.",
  { provider: "codex", model: "gpt-6.1-sol", reasoningLevel: "high", phase: "Implement", label: "implement", schema: WORK },
);
if (!work) return { status: "failed", stage: "implement" };
if (work.status === "blocked") return { status: "blocked", stage: "implement", work };

let rounds = 0;
let blocking = [];
let minor = [];
for (let round = 1; round <= maxRounds; round++) {
  rounds = round;
  const review = await agent(
    "Review an executor's changes for this task:\n\n" + args.task +
      "\n\nExecutor report:\n" + JSON.stringify(work, null, 2) +
      "\n\nThe user's own work may be staged in the same files. Review only the executor's edits: " +
      "`git diff -- <file>` (working tree against the index) for tracked files in filesChanged, and the full " +
      "content of new untracked files in filesChanged. Check correctness, whether the task is fully done, test " +
      "coverage of the change, and the repository rules in the nearest AGENTS.md files. Rerun a check if the " +
      "report looks doubtful. Report only problems you verified. Do not edit, stage or commit files.",
    { provider: "claude-code", model: "claude-opus-5-5", reasoningLevel: "high", phase: "Review", label: "review #" + round, schema: REVIEW },
  );
  if (!review) {
    log("Review #" + round + " failed; stopping without a clean review");
    return { status: "review_failed", rounds, work };
  }
  blocking = review.findings.filter((f) => f.severity !== "low");
  minor = review.findings.filter((f) => f.severity === "low");
  if (blocking.length === 0) break;
  if (round === maxRounds) {
    log("Stopped after " + maxRounds + " review rounds with " + blocking.length + " blocking findings");
    break;
  }
  const fixed = await agent(
    "Fix these review findings for the task below. Add regression tests where a finding describes a behavior bug.\n\n" +
      "Task:\n" + args.task + "\n\nFindings:\n" + JSON.stringify(blocking, null, 2) +
      "\n\nYour previous report:\n" + JSON.stringify(work, null, 2) + "\n\n" + checksText() + "\n\n" + GIT_RULES +
      "\n\nReport the complete list of files changed by you across all rounds.",
    { provider: "codex", model: "gpt-6.1-sol", reasoningLevel: "high", phase: "Fix", label: "fix #" + round, schema: WORK },
  );
  if (!fixed) {
    log("Fix #" + round + " failed; keeping the previous state");
    break;
  }
  work = fixed;
  if (work.status === "blocked") return { status: "blocked", stage: "fix #" + round, unresolved: blocking, work };
}
if (minor.length) log(minor.length + " low-severity findings left for the user");

// Compact fields first: the completion message is cut at maxNotificationBytes.
return {
  status: blocking.length ? "unresolved" : "clean",
  rounds,
  filesChanged: work.filesChanged,
  checks: work.checks,
  unresolved: blocking,
  minor,
  summary: work.summary,
};
