export const meta = {
  name: "peer-analysis",
  description: "Claude and GPT research one question as equals, debate, and sign a joint answer",
  inputSchema: {
    type: "object",
    required: ["question"],
    additionalProperties: false,
    properties: {
      question: { type: "string", minLength: 10 },
      maxRounds: { type: "integer", minimum: 1, maximum: 4 },
      drafter: { enum: ["claude", "gpt"] },
    },
  },
  phases: [
    { title: "Research", detail: "Both agents investigate independently" },
    { title: "Debate", detail: "Each checks the other's evidence and revises its own position" },
    { title: "Joint answer", detail: "One drafts, the other signs off or objects" },
  ],
};

const POSITION = {
  type: "object",
  required: ["answer", "claims", "disagreements"],
  properties: {
    answer: { type: "string" },
    claims: {
      type: "array",
      items: {
        type: "object",
        required: ["claim", "evidence", "confidence"],
        properties: {
          claim: { type: "string" },
          evidence: { type: "string" },
          confidence: { enum: ["high", "medium", "low"] },
        },
      },
    },
    disagreements: {
      type: "array",
      items: {
        type: "object",
        required: ["point", "why"],
        properties: { point: { type: "string" }, why: { type: "string" } },
      },
    },
  },
};

const SIGNOFF = {
  type: "object",
  required: ["approve", "objections"],
  properties: {
    approve: { type: "boolean" },
    objections: { type: "array", items: { type: "string" } },
  },
};

// Workers share the user's checkout, which may hold someone's unfinished work.
const RULES =
  "This is an analysis task. Do not modify, create, delete, stage or commit repository files; " +
  "put any scratch files under $BB_THREAD_STORAGE. Use repository files and web search as needed. " +
  "Every claim needs evidence: a URL or file:line. Separate verified facts from inferences. " +
  "Write in the language of the question.";

function researchPrompt() {
  return "Question:\n" + args.question + "\n\nLeave disagreements empty. " + RULES;
}

function debatePrompt(own, peer) {
  return (
    "Question:\n" + args.question +
    "\n\nYour current position:\n" + JSON.stringify(own, null, 2) +
    "\n\nYour peer's position:\n" + JSON.stringify(peer, null, 2) +
    "\n\nCheck the peer's evidence yourself. Adopt what holds up, reject what does not, and revise your position. " +
    "List in disagreements only the points where you still disagree after checking. " + RULES
  );
}

function draftPrompt(claude, gpt) {
  return (
    "Write the joint answer to:\n" + args.question +
    "\n\nUse both final positions. State the agreed conclusions with their evidence. List every remaining " +
    "disagreement with both sides' arguments; do not resolve it yourself.\n\nClaude:\n" +
    JSON.stringify(claude, null, 2) + "\n\nGPT:\n" + JSON.stringify(gpt, null, 2) + "\n\n" + RULES
  );
}

function signoffPrompt(own, draft) {
  return (
    "Your peer drafted this joint answer. Approve it only if it states your position and the evidence " +
    "faithfully; otherwise list your objections.\n\nQuestion:\n" + args.question +
    "\n\nYour final position:\n" + JSON.stringify(own, null, 2) + "\n\nDraft:\n" + draft + "\n\n" + RULES
  );
}

phase("Research");
let [claude, gpt] = await parallel([
  () => agent(researchPrompt(), { provider: "claude-code", model: "claude-opus-5-5", reasoningLevel: "high", label: "claude: research", schema: POSITION }),
  () => agent(researchPrompt(), { provider: "codex", model: "gpt-6.1-sol", reasoningLevel: "high", label: "gpt: research", schema: POSITION }),
]);
if (!claude || !gpt) return { error: "a research agent failed", claude, gpt };

const maxRounds = args.maxRounds || 2;
let rounds = 0;
let consensus = false;
phase("Debate");
for (let round = 1; round <= maxRounds; round++) {
  const [c, g] = await parallel([
    () => agent(debatePrompt(claude, gpt), { provider: "claude-code", model: "claude-opus-5-5", reasoningLevel: "high", label: "claude: round " + round, schema: POSITION }),
    () => agent(debatePrompt(gpt, claude), { provider: "codex", model: "gpt-6.1-sol", reasoningLevel: "high", label: "gpt: round " + round, schema: POSITION }),
  ]);
  if (!c || !g) {
    log("Round " + round + " failed for one side; keeping the previous positions");
    break;
  }
  claude = c;
  gpt = g;
  rounds = round;
  consensus = claude.disagreements.length === 0 && gpt.disagreements.length === 0;
  if (consensus) {
    log("Consensus after round " + round);
    break;
  }
  if (round === maxRounds) log("Disagreements remain after " + maxRounds + " rounds");
}

function revisePrompt(draft, objections) {
  return (
    "Your peer refused to sign off your joint answer to:\n" + args.question +
    "\n\nObjections:\n" + JSON.stringify(objections, null, 2) + "\n\nDraft:\n" + draft +
    "\n\nCheck each objection against the evidence. Apply the ones that hold up. Keep the ones you reject " +
    "under remaining disagreements with both sides' arguments. Return the full revised answer. " + RULES
  );
}

const gptDrafts = args.drafter === "gpt";
const reviewerPosition = gptDrafts ? claude : gpt;

function draftBy(prompt, label) {
  if (gptDrafts) return agent(prompt, { provider: "codex", model: "gpt-6.1-sol", reasoningLevel: "high", label: "gpt: " + label });
  return agent(prompt, { provider: "claude-code", model: "claude-opus-5-5", reasoningLevel: "high", label: "claude: " + label });
}

function signBy(prompt, label) {
  if (gptDrafts) return agent(prompt, { provider: "claude-code", model: "claude-opus-5-5", reasoningLevel: "high", label: "claude: " + label, schema: SIGNOFF });
  return agent(prompt, { provider: "codex", model: "gpt-6.1-sol", reasoningLevel: "high", label: "gpt: " + label, schema: SIGNOFF });
}

phase("Joint answer");
let answer = await draftBy(draftPrompt(claude, gpt), "draft");
let signoff = await signBy(signoffPrompt(reviewerPosition, answer), "sign-off");
let revised = false;
if (answer && signoff && !signoff.approve && signoff.objections.length) {
  const revision = await draftBy(revisePrompt(answer, signoff.objections), "revision");
  if (revision) {
    answer = revision;
    revised = true;
    signoff = await signBy(signoffPrompt(reviewerPosition, answer), "second sign-off");
  }
  if (!signoff || !signoff.approve) log("The joint answer is still not approved after one revision");
}

// Compact fields first: the completion message is cut at maxNotificationBytes.
return {
  signoff: { by: gptDrafts ? "claude" : "gpt", ...signoff },
  consensus,
  rounds,
  revised,
  answer,
  positions: { claude, gpt },
};
