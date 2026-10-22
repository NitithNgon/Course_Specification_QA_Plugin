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

## Layout

```
config.yaml                 M2  profiles + per-agent profile and step budget
harness/
  llm_client.py config.py   M1/M2  from Harness/ (config gains an `agents:` block)
  prompts.py logger.py      M3/M14 from Harness/
  tools.py executor.py      M6/M7  from Harness/
  harness.py                facade from Harness/ (+ config_agents)
  agent_loop.py             M8  h.llm(tools) -> execute -> tool_message, per Stage
  data_store.py             plugin paths, rulebook loaders, validated findings writes
  spec_parser.py            parser for the official form (sections, tables, line numbers)
  qa_rules.py               the 41 rules, precedence, CLO derivation, coverage, verdict
  qa_tools.py               22 @tool functions
  pipeline.py               3 stages, deterministic reference run, batch finish
  ground_truth.py           reads and scores evaluation/*.md (evaluator only)
prompts/                    course_reviewer@v2, curriculum_auditor@v2, verdict_writer@v2
scripts/
  run_review.py             /review-spec equivalent
  eval_ground_truth.py      score against evaluation/ (scratch copy without evaluation/)
  demo_qa_tools.py          tools on one spec; --failure shows every guarantee
tests/test_offline.py       25 offline tests with a FakeClient (no Ollama)
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
python scripts/run_review.py --mode deterministic --all  # same tools, no model
```

From the plugin root instead: `python -m unittest discover -s Course_Specification_QA_Plugin_harness/tests`.

Output goes to `./reports/` by default. Pass `--reports-dir ../reports` to write where the
Claude Code plugin writes. Every LLM call and tool call is one line in `logs/calls.jsonl`,
grouped by `run_id`.

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
