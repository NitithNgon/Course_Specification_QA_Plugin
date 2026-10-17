# Course Specification QA: harness version

This is the Course Specification QA plugin rebuilt on top of the Session 2 `Harness/`
building blocks. It runs with a local Ollama model instead of Claude Code.

It is the same pipeline: course-reviewer, then curriculum-auditor, then verdict-writer.
It reads the plugin's own `courses/` and `references/`. The difference is that the
model works only through typed, permissioned tools. Every rule with one right answer
runs as code inside a tool.

## How the plugin maps onto the harness

| Claude Code plugin | Harness version | Where |
|---|---|---|
| `commands/review-spec.md` | `pipeline.run_agents()` / `scripts/run_review.py` | orchestration |
| `agents/*.md` (3 roles) | `Stage` = prompt + tool allow-list + permission set | `pipeline.STAGES`, `prompts/*@v1.txt` |
| `skills/course-qa-checklist` | `run_structure_check`, `check_weights` | `qa_rules.check_structure` |
| `skills/bloom-verb-rules` | `bloom_review`, `lookup_bloom_verb`, `run_bloom_check` | `qa_rules.check_bloom` |
| `skills/plo-mapping-standard` | `get_plo_catalog`, `validate_plo_ids`, `run_plo_check`, `plo_coverage_rollup` | `qa_rules.check_plo` |
| `skills/committee-review-format` | `add_finding` (schema + severity lock), `get_verdict`, `write_review_note` | `qa_tools.py` |
| PreToolUse `block_approve_with_blocker.py` | `write_review_note` takes **no verdict argument**. It computes the verdict from `findings.json` | `qa_tools.write_review_note` |
| PostToolUse `log_verdict.py` | the same tool appends to `audit-log.jsonl` | `qa_tools.write_review_note` |
| "only a human may resolve a blocker" | `resolve_finding` has `dangerous` permission, and no stage grants it | `tools.py` permission + `executor.py` |

The Claude Code hook catches a bad verdict after the model has written it. In the
harness, the bad verdict cannot be expressed at all. The argument does not exist, and
unknown argument names are rejected.

## Layout

```
config.yaml                 M2  profiles (fast/reasoning) + per-agent profile and step budget
harness/
  llm_client.py config.py   M1/M2  copied from Harness/ (config gains an `agents:` block)
  prompts.py logger.py      M3/M14 copied unchanged
  tools.py executor.py      M6/M7  copied unchanged
  harness.py                facade, copied (+ config_agents property)
  data_store.py             paths: plugin courses/ and references/; reports/ output folder
  spec_parser.py            deterministic parser for course_specification.md
  qa_rules.py               checklist, Bloom, PLO and verdict rules as pure functions
  qa_tools.py               @tool wrappers (20 tools), importing registers them
  agent_loop.py             M8  loop: h.llm(tools) -> execute -> tool_message, per Stage
  pipeline.py               3 stages + deterministic reference run + batch finish
prompts/                    course_reviewer@v1, curriculum_auditor@v1, verdict_writer@v1
scripts/
  run_review.py             /review-spec equivalent
  eval_gold.py              score against courses/gold-labels.json (sandboxed)
  demo_qa_tools.py          tools on one spec; --failure shows every guarantee
tests/test_offline.py       19 offline tests with a FakeClient (no Ollama)
```

## Tools

| Tool | Perm | Purpose |
|---|---|---|
| `list_course_specs` | read | spec files under `courses/` |
| `read_course_spec` | read | raw text (only `.md` specs; gold labels and files outside the plugin are refused) |
| `parse_course_spec` | read | code, name, CLO table, assessment table, total, rubric, policies (verbatim rows) |
| `check_weights` | read | exact weight sum and delta from 100 |
| `run_structure_check` | read | checklist 1.x, 2.1–2.3, 2.5, 3.1–3.5, 4.x as draft findings |
| `bloom_review` | read | per-CLO verb level vs stated level. `needs_model_judgment` marks unknown verbs |
| `lookup_bloom_verb` | read | one verb, looked up in `bloom-taxonomy.md` |
| `run_bloom_check` | read | checklist 2.4 and 3.6 with Bloom citations |
| `get_plo_catalog` / `validate_plo_ids` | read | the catalog, and valid vs dangling IDs |
| `run_plo_check` | read | checklist 2.5 and 2.6 |
| `plo_coverage_rollup` | read | program coverage: covered / unverified-only / gaps |
| `get_findings` / `get_verdict` | read | state of `findings.json` and the policy-table verdict |
| `add_finding` | write | one judgment-based finding (inferred verb, `plo-fit` note) |
| `record_check_results` | write | run a check and append all its findings in one call, with deduplication |
| `write_review_note` | write | REVIEW_NOTE.md + audit log + amendments queue. Computes its own verdict |
| `write_batch_summary` / `write_plo_coverage_report` | write | COURSE_SPEC_REVIEW.md, PROGRAM_PLO_COVERAGE.md |
| `resolve_finding` | dangerous | human-only. Marks a finding resolved with a note and never deletes it |

### What the model still decides

- Which tool to call next.
- The Bloom level of verbs that are not in the dictionary (`needs_model_judgment`, e.g. "Give", "Build").
- `plo-fit` advisory notes.

### Guarantees enforced in code, not in prompts

- **Severity lock.** A checklist rule's severity is fixed by `checklist.md`. Rule 2.4 is the one exception: it may be major or minor (over-claim vs under-claim).
- **Citations.** curriculum-auditor findings must have a `standard_ref`.
- **Source attribution.** `source_agent` is injected by the stage, not trusted from the model.
- **Stage scope.** A stage can only call the tools it was offered, and can only record its own checks. Reviewer records structure; auditor records bloom and plo.
- **Loop safety.** A repeated identical call is refused, and the loop stops on repeats or at `max_steps`.

## Run

Use the venv from `Harness/` (requests, pydantic, pyyaml):

```powershell
cd Course_Specification_QA_Plugin\Course_Specification_QA_Plugin_harness
..\..\Harness\.venv\Scripts\activate

python -m unittest discover -s tests -v                      # offline, no Ollama
python scripts/demo_qa_tools.py --failure                    # every guarantee, as tool errors
python scripts/eval_gold.py                                  # deterministic reference vs gold
python scripts/eval_gold.py --mode agents --cases blocker_02_weight_95.md

python scripts/run_review.py courses/clean_01_data_structures.md
python scripts/run_review.py --all                           # + batch summary and PLO coverage
python scripts/run_review.py --mode deterministic --all      # same tools, no model
```

Output goes to `./reports/` by default. Pass `--reports-dir ../reports` to write where the
Claude Code plugin writes. That overwrites the pilot's REVIEW_NOTE.md evidence.
Every LLM call and tool call is one line in `logs/calls.jsonl`, grouped by `run_id`.

## Limits

- The parser expects the Markdown template used in `courses/`. The real PDFs in
  `total-cases/` need a PDF-to-text step first, which is not implemented.
- The Bloom verb chain is read from the start of the CLO ("Design, develop and evaluate").
  A CLO that opens with a non-verb ("Give students…") is passed to the model.
- `references/plo-catalog.md` is still the template catalog.
