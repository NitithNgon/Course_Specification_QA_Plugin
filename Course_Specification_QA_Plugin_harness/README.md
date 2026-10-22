# Course Specification QA: harness version

This is the Course Specification QA plugin rebuilt on top of the Session 2 `Harness/`
building blocks, so it runs with a local Ollama model instead of Claude Code.

It runs the same pipeline (course-reviewer → curriculum-auditor → verdict-writer) on the
same files: `courses/`, the rulebook in `references/`, and the plugin's own
`hooks/validate_findings.py`. The model works only through typed, permissioned tools,
and every rule with one right answer runs as code inside a tool.

It tracks the `revision` baseline of the plugin: the official CU course-specification
form, 41 checklist rules with an owner each, Bloom levels on assessment methods, and
the `evaluation/` ground truth.

## The rulebook is read at run time

Nothing from the rulebook is copied into code. Edit a reference file and the harness
follows it.

| Plugin file | Read by | Used for |
|---|---|---|
| `references/checklist.md` | `data_store.checklist()` | every rule's severity and owner (the model never supplies a severity) |
| `references/bloom-taxonomy.md` | `data_store.bloom()` | the verb dictionary, convention verbs (`function`, `communicate`), method types for 4.9 |
| `references/plo-catalog.md` | `data_store.plo_catalog()` | valid PLO IDs (2.5) and WA attributes (coverage report) |
| `hooks/validate_findings.py` | `data_store.save_findings()` | **every** `findings.json` write runs the plugin's own validator: rule exists, severity and owner match, required fields present, append-only |

The rule checks themselves (F.1, 1.x–7.x and the precedence list) are in
`harness/qa_rules.py`. Each draft finding takes its severity and owner from
`checklist.md`.

## How the plugin maps onto the harness

| Claude Code plugin | Harness version |
|---|---|
| `commands/review-spec.md` | `pipeline.run_agents()`, `scripts/run_review.py` (`--all [DIR]`). It clears `reports/<code>/` first and skips curriculum-auditor when F.1 fails |
| `agents/*.md` | `Stage` = prompt (`prompts/*@v2.txt`) + tool allow-list + permissions, in `pipeline.STAGES` |
| `skills/course-qa-checklist` | `check_form_gate`, `check_weights`, `run_reviewer_checks`, `record_check_results(structure)` |
| `skills/bloom-verb-rules` | `derive_clo_levels`, `lookup_bloom_verb`, `set_clo_level`, `run_bloom_checks`, `record_check_results(bloom)` |
| `skills/plo-mapping-standard` | `get_plo_catalog`, `run_plo_checks`, `record_check_results(plo)`, `plo_coverage_rollup`, `write_plo_coverage_report` |
| `skills/committee-review-format` | `add_finding`, `get_verdict`, `write_review_note`, `write_batch_summary` |
| hook `validate_findings.py` | imported and run on every `findings.json` save |
| hook `block_approve_with_blocker.py` | `write_review_note` has **no verdict argument**; it computes the verdict from `findings.json` |
| hook `log_verdict.py` | `write_review_note` appends the audit line: open counts, resolved count, `rulebook_sha256` |
| "only a human resolves a finding" | `resolve_finding` needs `dangerous`, which no stage is granted |

## What the model decides, and what it cannot

The model decides:
- which tool to call next;
- the Bloom level of a CLO verb that is in neither `bloom-taxonomy.md` nor the harness
  synonym table, or that a CLO is really a teaching aim (`set_clo_level`, saved as
  reviewer notes in `reports/<code>/clo_levels.json`);
- 2.7 advisory findings (an obvious CLO-to-PLO misfit, with the reason).

The model cannot:
- choose a severity (it is not an argument);
- file a rule another agent owns;
- skip a citation as curriculum-auditor;
- edit or remove an existing finding;
- write a verdict;
- read `evaluation/`, `reports/` or files outside the plugin;
- call a tool its stage was not offered.

### CLO level derivation

`qa_rules.derive_clo` reads a word as a student verb when it:
- opens the CLO;
- follows *to / can / will*;
- follows *and / or / ,* after a student verb, unless a noun head follows, as in
  "design **decisions**";
- is an *-ing* participle of a known verb ("using", "documenting").

Nouns spelled like verbs are skipped ("algorithm **designs**", "query **plans**"), and so
are verbs with another subject ("a scene that **applies**"). Verbs missing from the
dictionary go through `SYNONYMS` in `qa_rules.py` (build → construct, diagnose →
examine, …). Anything left over is marked `needs_judgment` for the model.

## Session 3: agent loop, state machine, routing (W11)

Three ways to run the same three stages, all scored the same way:

| Mode | What drives it | Profiles |
|---|---|---|
| `deterministic` | the pipeline calls the tools itself (no model) | none |
| `agents` | M8 agent loop per stage, fixed order (`pipeline.run_agents`) | `agents:` in config, or one `--profile` for all (single-model baseline) |
| `sm` | M9 state machine around the same loops (`state_machine.run_sm`) | M11 router, per step |

### M8: agent loop (`agent_loop.run_stage`)

Each harness fix from the slide "How small models fail in loops" maps to code here:

| Failure | Harness fix |
|---|---|
| made-up tool / tool not offered | rejected with the list of valid tools (executor + stage allow-list) |
| bad arguments | schema error returned as an observation |
| endless loop | repeats get an error observation, never run again; a step of only repeats stops the loop (`repeat`); `max_steps` |
| stops too early | **completion check** (`completion.py`) before a final answer is accepted. If work is missing, the loop says what and restates the goal |
| too many errors | **error budget**: `max_errors` failed tool calls per stage (`error_budget`) |
| loses the goal | the completion nudge restates the goal. Old steps are never summarised, because rewriting history would break the prefix cache |
| too many tools | each stage, and in `sm` each kind of step, is offered only the tools it needs |

Every stop other than `done` is a logged `safe_failure`. A stop on a limit still runs the
completion check once: if the work is verifiably done (for example, it recorded everything
and then looped), the stage is `verified` and counts as finished. `stopped` keeps the real
reason for the metrics. Each LLM call is logged with `step`, `stage` and (in `sm`) `state`,
and the result's `trace` holds per-step tokens, `load_s`, `prompt_s` and TTFT.

The completion checks are about the outcome: a stage is done when every finding its rule
checks produce is in `findings.json` (and, for the auditor, every unclassifiable CLO has a
`set_clo_level`). A course with nothing to record passes at once, and that is correct, because
the result has been verified.

### M9: state machine (`state_machine.py`)

```
INTAKE -> CLASSIFY -> PLAN -> ACT -> VERIFY -> DONE
             |         |      |      |   └── re-plan (max 2) ──> PLAN
             └─────────┴──────┴──────┴─────> ESCALATE (human / safe failure)
```

| State | Model gets | Does | Next if OK |
|---|---|---|---|
| INTAKE | nothing | reads the spec: form gate, CLO/method counts, unclassifiable CLOs | CLASSIFY |
| CLASSIFY | no tools | M10 classifier → `off_form` / `standard` / `needs_judgment` | PLAN |
| PLAN | nothing | plan template for the task type (`commands/review-spec.md` order); a re-plan restarts at the first stage that failed and tells it what was missing | ACT |
| ACT | that step's tools | one M8 loop per plan step, routed by M11; stops at the first unfinished step so the verdict-writer never writes from incomplete findings | VERIFY |
| VERIFY | nothing | every completion check, read-only | DONE, or PLAN (≤ `max_replans`), else ESCALATE |

PLAN and VERIFY are code, not model calls, because each has one right answer. The
transition table is the slide's: an illegal move raises `IllegalTransition`. If a state
raises an exception (for example, Ollama is down), the run moves to ESCALATE when the
table allows it. ESCALATE writes `reports/<code>/ESCALATION.md` with the reason, the
unfinished checks and the transition log. No review note is published, and the batch
summary shows `ESCALATED`.

The `RunState` (Pydantic) is saved to SQLite (`logs/runs.sqlite`, next to `calls.jsonl`)
after every transition and every ACT step. `--resume RUN_ID` continues a crashed run from
its last saved state. Re-running a step is safe because `record_check_results` skips
duplicates. Each transition is also a `transition` line in `logs/calls.jsonl`.

| Task type | Plan (stage[kind]) |
|---|---|
| `off_form` | course-reviewer[gate] → verdict-writer[write] (gate offers only `check_form_gate`, `record_check_results`, `get_findings`) |
| `standard` | course-reviewer[review] → curriculum-auditor[audit] → verdict-writer[write] (audit is not offered `set_clo_level`) |
| `needs_judgment` | course-reviewer[review] → curriculum-auditor[judge] → verdict-writer[write] |

### M10: task classifier (`classifier.py`)

The classifier tries the cheapest method first. **Rules** use the form fields, so the form
gate and the CLO verb derivation decide every course in `courses/`: CPE440/CPE450 are
`off_form`, CPE503 is `needs_judgment` (CLO1 "Give students ..."), and the rest are
`standard`. When the rules cannot decide (on the form, but no CLO or assessment rows were
parsed), it asks the **small model** (the `classify` route) with an enum schema. If that
fails, it asks the **main LLM** (the router's default profile). If both fail, the run
escalates. A model answer must pass the schema and a domain rule (it may not contradict the
form gate), with one repair attempt per profile.

### M11: model router (`router.py`, `routing:` in `config.yaml`)

1. Look up the kind of work in the table: `classify`, `gate`, `audit` and `write` go to
   `fast`; `review` and `judge` go to `reasoning`.
2. If the estimated prompt (system prompt + task + tool list + spec, about 4 characters per
   token) is over `ctx_ratio` × `num_ctx`, use `long_context` instead.
3. Each `fallback_after` failed attempts of the step moves it one rung up the `ladder`.

Every decision is logged as a `route` line (kind, profile, rule, estimated tokens,
failures). The ladder tops out at `reasoning`. To add a stronger profile, put it at the end
of the ladder; it must list `tools` under Capabilities in `ollama show` (gemma3 does not).

### Comparing the modes (hands-on checkpoint)

```powershell
python scripts/eval_ground_truth.py --mode agents --profile reasoning   # single-model loop
python scripts/eval_ground_truth.py --mode sm                            # state machine + router
python scripts/run_review.py --mode sm courses/CPE501.md                 # transition log for one task
python scripts/prefix_check.py courses/CPE201.md                         # stable vs shuffled prefix, TTFT per step
```

The last line of each eval run reports: task success (verdict right, no miss, no false
positive), mean steps, mean wall time, tool-call success, model switches, load time,
re-plans and escalations.

## Layout

```
config.yaml                 M2  profiles, per-agent budgets, routing (M11), state_machine (M9)
harness/
  llm_client.py config.py   M1/M2  from Harness/ (config gains `agents:`, `routing:`, `state_machine:`)
  prompts.py logger.py      M3/M14 from Harness/
  tools.py executor.py      M6/M7  from Harness/
  harness.py                facade from Harness/ (+ config_agents, log_extra)
  agent_loop.py             M8  loop per Stage: completion check, error budget, repeat, max steps
  completion.py             M8/M9 completion checks per stage (read-only)
  state_machine.py          M9  states, TRANSITIONS, RunState, SQLite checkpoints, resume
  classifier.py             M10 rules -> small model -> main LLM
  router.py                 M11 route table, long context, fallback ladder
  data_store.py             plugin paths, rulebook loaders, validated findings writes
  spec_parser.py            parser for the official form (sections, tables, line numbers)
  qa_rules.py               the 41 rules, precedence, CLO derivation, coverage, verdict
  qa_tools.py               22 @tool functions
  pipeline.py               3 stages, deterministic reference run, batch finish
  ground_truth.py           reads and scores evaluation/*.md (evaluator only)
prompts/                    course_reviewer@v2, curriculum_auditor@v2, verdict_writer@v2, classify_task@v1
scripts/
  run_review.py             /review-spec equivalent (--mode agents|sm|deterministic, --resume)
  eval_ground_truth.py      score against evaluation/ (scratch copy without evaluation/)
  prefix_check.py           prefix-cache check: stable vs unstable prompt prefix
  demo_qa_tools.py          tools on one spec; --failure shows every guarantee
tests/test_offline.py                 25 offline tests with a FakeClient (no Ollama)
tests/test_loop_and_state_machine.py  19 offline tests for M8-M11
```

## Run

Use the venv from `Harness/` (requests, pydantic, pyyaml). Run from **this** folder:

```powershell
cd Course_Specification_QA_Plugin\Course_Specification_QA_Plugin_harness
..\..\Harness\.venv\Scripts\activate

python -m unittest discover -s tests -v                  # offline, no Ollama
python scripts/demo_qa_tools.py --failure                # every guarantee, as tool errors
python scripts/eval_ground_truth.py -v                   # tools only vs evaluation/
python scripts/eval_ground_truth.py --mode agents --courses CPE201,CPE502

python scripts/run_review.py courses/CPE201.md
python scripts/run_review.py --all                       # + COURSE_SPEC_REVIEW.md, PROGRAM_PLO_COVERAGE.md
python scripts/run_review.py --mode sm --all             # state machine + router, prints transitions
python scripts/run_review.py --resume r-1a2b3c4d         # continue a crashed sm run
python scripts/run_review.py --mode deterministic --all  # same tools, no model
```

From the plugin root instead: `python -m unittest discover -s Course_Specification_QA_Plugin_harness/tests`.

Output goes to `./reports/` by default. Pass `--reports-dir ../reports` to write where the
Claude Code plugin writes. Every LLM call, tool call, route decision, completion check and
state transition is one line in `logs/calls.jsonl`, grouped by `run_id`. State-machine runs
are also checkpointed in `logs/runs.sqlite`.

## Results (tools only, `eval_ground_truth.py`)

| Metric | Result |
|---|---|
| Verdicts | 11/11 |
| Expected findings hit | 33/33, rule and severity correct on all |
| Duplicates / false positives | 0 / 0 |
| False blockers on the 5 APPROVE courses | 0 |
| Weight sums | 9/9 (the two off-form courses have none) |
| PLO rollup vs `evaluation/README.md` | 11/11 |

## Limits

- **PDF input.** Only Markdown specs are read. The real PDFs in `total-cases/` need a
  text step first, and the Thai text in some of them is garbled.
- **Method-type exception.** An exam can claim Evaluate/Create only by quoting such an
  item. Detecting that is model judgment and is not automated; exams are capped at Analyze.
- **Heuristic checks.** The 6.x presence checks are keyword searches, and the 4.10 split
  parser expects `- <Method> ...: part n, part n` or `part (n) + part (a × b)` in the
  assessment note.
- **Placeholder catalog.** `references/plo-catalog.md` is still a placeholder.
