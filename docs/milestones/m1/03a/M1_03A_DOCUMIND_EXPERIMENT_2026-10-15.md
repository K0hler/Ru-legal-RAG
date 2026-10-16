# M1-03A: bounded Documind auto-schema experiment

Date: 15 October 2026. This is diagnostic research, not a production integration,
legal edition admission, M1-03A closure, or parser transfer qualification.

## Question and scope

Can an open implementation infer a useful legal schema from a complete document,
then use that schema for extraction without an act-specific schema or parser rules?
The owner authorized this experiment and selected local inference through LM Studio.

The initial gate is the full retained Housing Code. A smaller, complete 59-FZ
control measures actual schema generation separately; it cannot replace the Housing
Code or the remaining mandatory original inputs. If a generated schema cannot
represent the required legal structure, extraction with that schema is not run.

## Pinned implementation and retained evidence

- Upstream: [Documind](https://github.com/DocumindHQ/documind), package version
  `1.1.5`, commit `f258286fc1026c1a6cd2b3f624906453681e7c87`.
- Runtime checkout: `data/m1/tool-environments/documind-20261015/`.
  Dependencies are installed with `npm ci --ignore-scripts --no-audit --no-fund`.
- Local evidence: `data/m1/experiments/documind-housing-code-20261015-v1/`.
- `setup-manifest.json` binds source/prepared HTML and complete model input;
  `paragraphs.jsonl` maps input text back to retained paragraph IDs.
- `token-preflight-gemma.json` and the memory-estimate logs describe the Housing
  Code capacity check. The separate 59-FZ control is under `controls/federal-law-59/`.
- Each actual model run retains request bodies, full raw responses, usage, finish
  reasons, schema artifacts and timing. Authorization headers are never retained.
  `config.local.json` is ignored; it currently points to the local server.
- All these data and runtime directories are ignored by Git and are not included
  in a fresh clone. The tracked report records observations, not the source corpus.

The experiment calls unchanged Documind `autoschema`, schema cleaning and schema
conversion. A runtime model registration selects its OpenAI-compatible adapter for
the installed local model. OpenAI's web-fetch shim permits raw response capture.
Neither upstream prompts nor generated schemas are edited. This does not test the
separate Documind HTML-to-PDF-to-image/OCR front end: complete source-bound text is
supplied directly to its schema layer.

Input preparation does not infer article parents. It retains every non-whitespace
text character of the prepared HTML, including the non-paragraph amendment-list
label, and preserves superscript digits. An initial preparation assertion wrongly
assumed all text was inside `p` elements; that assumption was corrected before any
model call, and complete text preservation was then asserted.

## Full Housing Code: capacity gate

The retained input has 776,020 characters, 243 article headings and 996 editorial
notes. Its UTF-8 input SHA-256 is
`86617757aebf230902ccb9cf22f55bc534f74e6171f0e1385ccd330e43ab53e7`.

Exact tokenization through the LM Studio SDK gives:

| Component | Gemma 4 12B | Qwen3.5 9B |
|---|---:|---:|
| Complete source text | 191,617 | 178,908 |
| Documind system prompt containing that same source | 191,696 | 178,987 |
| Request content, before chat-template/schema overhead | 383,313 | 357,895 |
| Model's declared maximum context | 262,144 | 262,144 |

Documind embeds the complete document in the system prompt and also sends it as
the user message. Its stock request therefore exceeds the declared model window,
for both tokenizers, even if reloaded at maximum context. No truncated Housing Code request
or synthetic full-document success is recorded. Housing schema quality is **untested**.

LM Studio estimated 40.26 GiB for Gemma at 220,000 tokens, and 29.51 GiB for Qwen3.5
9B at 262,144 tokens, both with full GPU offload and one prediction slot. The host
has 16 GiB VRAM / 32 GiB RAM. These are estimates for those settings, not measured
allocation or a claim that every quantized/offloaded configuration is impossible.
A deduplicated-input variation was considered but was not executed.

## Complete 59-FZ control: Gemma 4 12B QAT

Model ID: `google/gemma-4-12b-qat`, Q4_0, context 32,768, one prediction slot.
The complete input has 28,165 characters, 18 article headings and 24 editorial
notes. Its SHA-256 is
`b068e0f77dfde6d609d6b9fade8ec4123762e9cf75f40c2c1fbf635c2af7408a`.

### Stock autoSchema

`schema-run-a/`: one successful HTTP completion, `finish_reason=stop`, 53.269 s;
13,706 prompt tokens and 3,874 completion tokens, including 1,192 reasoning tokens.

Documind generated eight topical root fields: `law_metadata`,
`scope_of_application`, `definitions`, `citizen_rights_and_guarantees`,
`procedural_requirements`, `deadlines`, `special_conditions`, and
`legal_consequences`. The schema passes Documind's schema conversion but describes
a topical information summary, without article/part/item legal structure.
**Legal-schema gate: fail.** No downstream full-text extraction was run.

### Built-in instruction-guided autoSchema

`schema-guided-a/`: the same complete input, using Documind's native
`autoSchema: {instructions: ...}` mode. `guidance.txt` requests complete legal
nesting, source text, numbering, separate quotation/appendix contexts and attached
editorial notes. It is common to all acts; no JSON schema is supplied.

Both LLM calls finished with `stop`; total runtime was 46.082 s. The first call
reduces the instruction to field names. The second generated string fields for
`articles`, `parts`, `numbered_items`, `lettered_subitems`, `node_ids`, and
`parent_ids`, plus a `parent_child_relationships` object without child definitions.
Documind then raised
`Invalid "object" type definition for parent_child_relationships`.

The full raw generated schema remains in `response-2.json`; an additional readable
copy is `schema-raw-from-response.json`. **Legal-schema gate: fail; generated
schema is also unusable by Documind's own converter.** It was not manually repaired.

## Complete 59-FZ control: Qwen3.5 9B

Model ID: `qwen/qwen3.5-9b`, Q8_0, context 32,768, one prediction slot. The complete
source is identical to the Gemma control. Its stock request content takes 12,909
tokens before chat-template/schema overhead.

### Stock autoSchema

`qwen-schema-run-a/`: one successful HTTP completion, `finish_reason=stop`,
93.470 s; 12,921 prompt tokens and 6,457 completion tokens, including 5,382
reasoning tokens.

This schema is closer to legal structure: it has an article array at
`title/metadata/articles`, with article number/title and a `content` array.
However, each content element has only text and an amendment note. It has no
separate part numbering, item layer or item numbering. Thus it can represent
articles with body paragraphs, but cannot type and preserve the required
article/part/item hierarchy. **Legal-schema gate: fail.** No extraction was run
with this incomplete schema.

### Built-in instruction-guided autoSchema

`qwen-schema-guided-a/`: two successful HTTP completions, both with `stop`,
124.612 s in total. The first call returned the names `node_id`, `parent_id`,
`source_text`, `numbering`, `hierarchy_level` and `content_type`.

The generated schema then nested those fields inside one another, but declared
`node_id`, `parent_id`, `source_text` and `numbering` as strings. This violates
Documind's own prompt rule that `children` belongs only on objects/arrays.
Its schema converter does not reject children on a string; it ignores them.
Replaying the saved schema through the unchanged converter and JSON-schema
serializer yields exactly one output property: **`node_id: string`**.
The derived `effective-output-schema.json` and an assertion preserve this finding.
**Legal-schema gate: fail.** No downstream extraction was run.

## Disposition and limits

| Complete 59-FZ schema control | Converter usable | Required legal structure |
|---|---|---|
| Gemma, stock autoSchema | yes | fail: topical summary |
| Gemma, instruction-guided | no | fail: flat string fields and empty object |
| Qwen, stock autoSchema | yes | fail: articles/body paragraphs; no numbered parts/items |
| Qwen, instruction-guided | yes, but discards nested fields | fail: effective schema has only `node_id` |

Four schema controls made six local LLM calls. All HTTP responses were 200 and all
completion finish reasons were `stop`. Total reported run time was 317.433 seconds,
excluding installation, model loading and preflight. None passed the legal-schema
gate, so no downstream full-text extraction was justified. The Housing Code was
blocked by a measured stock-request context limit; its schema quality was not tested.
Neither the other mandatory originals nor the three expansion failures were
submitted after these failed gates.

**Do not integrate this Documind configuration into M1-03A.** The test demonstrates
insufficient automatically generated legal schemas for these two local models and
these modes; it does not prove that every model, provider or modified Documind
workflow fails. A larger-context API, deduplicated-input path, stronger model or
schema-generation repairs would be a separately identified experiment. No such
change is qualified here. The M1-03A production parser and all legal admission
statuses remain unchanged.

Verification includes complete input preservation, source/production hashes,
the synthetic transport self-check, an unchanged upstream checkout, replay of the
Gemma converter error, and the Qwen effective-schema assertion. These are diagnostic
checks, not full legal extraction accuracy or deterministic LLM replay claims.
LM Studio is returned to its initial Gemma model with context 8,192 and four
prediction slots after the experiment.

## Relevant upstream implementation

- [Auto-schema generation](https://github.com/DocumindHQ/documind/blob/f258286fc1026c1a6cd2b3f624906453681e7c87/extractor/src/autoschema/autogenerateSchema.js)
- [Schema/extraction prompts](https://github.com/DocumindHQ/documind/blob/f258286fc1026c1a6cd2b3f624906453681e7c87/extractor/src/prompts.js)
- [Schema converter](https://github.com/DocumindHQ/documind/blob/f258286fc1026c1a6cd2b3f624906453681e7c87/extractor/src/utils/convertToZodSchema.js)
- [Generator's schema-field definition](https://github.com/DocumindHQ/documind/blob/f258286fc1026c1a6cd2b3f624906453681e7c87/extractor/src/autoschema/generation-schemas/base.js)
