# Evaluation Report — Blink AI

## 1. Purpose

The evaluation strategy checks whether Blink AI selects appropriate tools, sends correct arguments, executes tools, fulfils user tasks, returns database-grounded answers, and completes requests within reasonable latency. The tests also cover preference memory, user isolation, reliability, frontend rendering, and streaming execution traces.

This report separates individual test runs because the results were collected at different points in development. A passing result from an earlier run does not overwrite a later regression failure.

## 2. Evaluation metrics

| Metric | Meaning | Evidence to record |
|---|---|---|
| Tool Selection Accuracy | Did the model choose the expected tool? | Expected tool vs. actual tool call |
| Tool Argument Accuracy | Were the extracted filters and entity names correct? | Expected arguments vs. actual arguments |
| Tool Execution Success | Did the selected tool execute without an exception? | Tool start/end status and error details |
| Task Success Rate | Did the complete interaction fulfil the user's request? | Task-level expected vs. actual outcome |
| Answer Correctness | Does the answer match retrieved database facts? | Product IDs, names, prices, ratings and review counts |
| Latency | How long did execution take? | End-to-end wall-clock duration and, where available, per-step timing |

Do not infer task success from HTTP 200 alone. A request can return HTTP 200 and still call the wrong tool or return incorrect facts.

## 3. Tool-calling evaluation cases

The practical tool-calling checklist defined six user scenarios:

| Scenario | Example request | Expected capability |
|---|---|---|
| Product search | Find organic honey under $20. | `search_product_tool` |
| Product details | Give me the details of Organic Raw Honey. | `check_product_tool` |
| Product comparison | Compare Organic Raw Honey and Organic Acacia Honey. | `compare_product_tool` |
| Save favorite | Save Organic Raw Honey to my favorites. | `save_favorite_tool` |
| Retrieve favorites | Show me my saved favorites. | `get_favorites_tool` |
| Remove favorite | Remove Organic Raw Honey from my favorites. | `remove_favorite_tool` |

The checklist describes intended coverage. The reported evaluation runs below provide the evidence actually recorded; they do not establish that all six scenarios passed in one consolidated run.

## 4. Product search case PS-001

Request: `Find organic honey under $20`.

| Criterion | Expected | Actual | Reported result |
|---|---|---|---|
| Tool selection | `search_product_tool` | `search_product_tool` | Pass |
| Category | `honey` | `honey` | Pass |
| Maximum price | 20 | 20 | Pass |
| Organic filter | `true` | `true` | Pass |
| Sorting | `price_asc` | `price_asc` | Pass |
| Product IDs | 1, 7, 5 | 1, 7, 5 | Pass |

Reported standalone result: **1/1 case passed**. The developer's run notes state that preference extraction identified category, product preference, and budget; the agent selected the correct tool, passed the expected arguments, retrieved three matching products, and returned to the LLM for final synthesis.

## 5. Golden-dataset agent evaluation

The JSONL dataset in the inspected archive contains five cases:

| Case ID | Capability | Input | Expected tool |
|---|---|---|---|
| PS-001 | Organic product search | Find organic honey under $20 | `search_product_tool` |
| PS-002 | Search under budget | Show me honey products under $15 | `search_product_tool` |
| PS-003 | Rating-based search | Find organic honey under $25, sorted by highest rating | `search_product_tool` |
| PC-001 | Comparison | Compare Organic Raw Honey and Wildflower Honey | `compare_product_tool` |
| PD-001 | Product details | Tell me the details of Organic Manuka Honey | `check_product_tool` |

### Earlier run history

- The PS-001 case passed separately as a standalone evaluation.
- A later run was reported as **4/4 cases passed** in **11.55 seconds**, with 13 non-blocking deprecation warnings. The developer explicitly corrected the count: the four collected cases were PS-002, PS-003, PC-001, and PD-001; PS-001 was from the earlier separate run. Do not report that run as five collected cases.
- The five-case LangSmith experiment named `blink-ai-agent-eval-v1-cb83c2` was reported as successful with **5 runs**. The displayed average score was **1.00** for the applicable evaluator results: `tool_selection_accuracy`, `tool_argument_accuracy`, and `product_result_accuracy`. Some evaluator/case combinations were `not_applicable`; that means the evaluator did not apply to that case, not that the case failed.

### Later regression run

A subsequent Pytest regression run reported:

- **10 passed**
- **1 failed**
- Failure: `PD-001`
- Expected tool: `check_product_tool`
- Actual tool: `search_product_tool`

This is a tool-selection inconsistency for product-detail requests. The developer chose to retain it as a known limitation rather than weaken the expected result or change graph logic during that iteration.

## 6. Memory evaluation

The reported memory suite passed **6/6 tests**:

1. Preference persistence and retrieval.
2. Updating an existing preference.
3. Isolation between users.
4. Preference extraction and storage.
5. Injecting saved preferences into a new conversation.
6. Empty user ID validation.

An earlier combined automated run was reported as **10/10 passing**: four agent tests plus six memory tests, completing in 17.25 seconds. This earlier result is superseded as a description of the latest regression state by the later 10-passed/1-failed run.

## 7. Frontend smoke tests

The developer reported all **8/8 frontend smoke tests passed**:

1. Product search returns three correct product cards.
2. No duplicate Markdown product table appears.
3. Search execution trace completes correctly.
4. Comparison card displays both products accurately.
5. Comparison execution trace belongs to its response.
6. All three consecutive messages remain visible.
7. Each message retains its own execution trace.
8. No horizontal clipping or broken layout.

The developer subsequently reported that streaming and related public-site functionality were working. The 8/8 figure is a frontend smoke-test checklist result, not an overall application test-suite pass rate.

## 8. Docker and deployed integration evidence

The reported local Docker verification included:

- Backend image built successfully.
- FastAPI container started and reached `healthy`.
- `/api/health` returned `status: ok`.
- SQLite integrity check returned `ok`.
- Row counts matched before and after container recreation: products 32, reviews 102, orders 0, customer_preferences 105, users 8, favorites 0.
- Docker Compose started backend and frontend containers.
- Nginx served frontend assets successfully.
- Login and token verification returned HTTP 200 in the observed logs.
- `/api/chat/stream` returned HTTP 200 and the agent executed `search_product_tool`, retrieving four product results in that observed interaction.

The developer later confirmed public streaming and UI behavior were working. These are integration observations, not a substitute for repeated automated load or uptime tests.

## 9. Current evaluation status

| Area | Latest supported result | Status / note |
|---|---|---|
| PS-001 standalone | 1/1 passed | Passed in its separate run |
| Golden dataset earlier four-case run | 4/4 passed | Earlier run only; collected cases were PS-002, PS-003, PC-001, PD-001 |
| Memory tests | 6/6 passed | Passed |
| Earlier combined suite | 10/10 passed | Historical run; 4 agent + 6 memory tests |
| Latest regression suite | 10 passed, 1 failed | PD-001 tool-selection failure |
| LangSmith experiment | 5 runs; applicable evaluator averages 1.00 | Reported; `not_applicable` is not a failure |
| Frontend smoke tests | 8/8 passed | Reported by developer |
| Local Docker DB persistence | Before/after row counts matched | Verified in reported test |
| Public streaming integration | Reported working | Manual end-to-end confirmation |

## 10. Known evaluation limitations

- Product-detail tool routing is inconsistent for PD-001. This should remain a regression case.
- Preference extraction needs continued validation to distinguish long-term reusable preferences from temporary request constraints.
- The reported 13 deprecation warnings were non-blocking but should be reviewed when dependencies are next updated.
- The five-run LangSmith scores are a small evaluation sample, not a statistically robust estimate of general performance.
- The dataset primarily covers basic and intermediate product search, comparison, and detail requests. It does not establish performance across broad user populations or adversarial prompts.
- Favorite operations are included in the planned test checklist and are implemented as tools, but the supplied run summary does not provide a consolidated pass/fail report for all three favorite scenarios.

## 11. Recommended next evaluation work

1. Keep PD-001 unchanged and improve tool descriptions or routing instructions, then rerun it repeatedly to measure consistency.
2. Add a clear result record for save, retrieve, and remove favorite operations.
3. Add multi-turn workflows combining budget, organic preference, comparison, and favorites.
4. Separate permanent preference statements from one-off filters in the extraction evaluation set.
5. Store per-case latency and tool traces alongside the expected/actual tool and argument values.
6. Rerun the full suite after each agent prompt or dependency change and retain experiment identifiers with the report.
