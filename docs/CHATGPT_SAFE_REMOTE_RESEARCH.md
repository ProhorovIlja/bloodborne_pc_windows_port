# ChatGPT remote-query safety contract (2026-11-01)
Applies to every future Bloodborne / Yharnam Together continuation, PR #84, PR #85, and upstream research. PRIORITY: do not flood or stall chat.

## Hard restrictions
1. NEVER fetch full GitHub Actions logs, check-run logs, complete PR patches/diffs, complete commit diffs, archive ZIPs, repository trees, or large source files into chat. Never use a full-results fallback after a narrow request fails.
2. Read PR and workflow **metadata only** (SHA, status, conclusion, changed filenames when essential). For code, use a pinpointed GitHub file path and 1-based `start_line`/`end_line` (at most 60 lines), preferably after finding a symbol. Do not open a whole source file to locate a symbol.
3. At most 2 remote operations per batch. No fan-out of broad searches (GitHub, Drive, internet); finish, inspect tiny summaries, then decide the next request. Search `topn <= 5`; specific PR number or SHA preferred.
4. Per-remote-result model-visible projection: <= 1,500 characters. Per batch: <= 3,000 characters. In orchestration, output a selected allowlist of fields, NEVER the raw response object. Do not rely only on truncating a giant full response; narrow the upstream request first.
5. For CI, list only most recent relevant 1-3 runs and their status/conclusion; if a job fails, inspect failing step names only. No log fetching as an escalation. If a deeper diagnosis requires a log, ask for an extracted 20-40 line fragment or create a bounded on-run diagnostic artifact with strict size limits. No secrets.
6. Do not stream giant previous chats or game directories into the model. Use targeted Drive filenames and small ranges/metadata. Large private game bytes are processed by a bounded local/private script, not returned in chat.
7. If a remote tool lacks upstream pagination/line limits, DON'T call it on uncertain-size resources. Use source search, a smaller approved API, or state that inspection is incomplete. Never compensate with large Promise.all batches.
8. No retry loops on errors or timeouts. One narrow retry only when the failure mode is understood; otherwise stop and report.
9. Keep the working context small: summary of change, actual verified SHA, CI outcome, blocker. No pasted source, logs or massive lists. Before each tool call, check whether it might produce an unbounded response.

## Safe continuation sequence
- Check PR #84 and #85 metadata (two calls, print <300 chars each).
- Identify ONE issue and ONE symbol/file via a top-3 code search.
- Inspect only 20-60 relevant source lines.
- Make a focused change with complete file content ONLY when needed for a GitHub write; do not print that file to chat.
- Run named CI, read conclusion and failing step names only. Do not fetch raw logs.
- Record one concise result and stop. Treat any unresolved fact as unresolved.

## Limitations
This is a persisted operational rule for the assistant, not a platform-enforced cap on the GitHub/Drive tool implementations. Tool-side fetching may still occur internally; avoid asking for large resources in the first place. No claim that this alone fixes underlying UI/tool timeouts. Never claim an unexecuted build or gameplay test succeeded.

## 2026-11-01: `Error in input stream` operational RCA and mitigations

- Root cause of any specific ChatGPT UI error is **NOT established**. Official
  OpenAI troubleshooting notes that errors can stem from transient server-side
  faults, browser/WebSocket/VPN/proxy/extension interference, or long chats.
  Official status history did not list a new Nov 1 incident when checked.
  We cannot modify ChatGPT's internal stream infrastructure from this repo.
- Public Developer Community reports this exact message even on trivial Python
  or container calls during an infrastructure incident. Do not reflexively
  blame GitHub or a user's source code without evidence.
- New private Bloodborne V204 scanner-generator safety:
  `bounded_private_subprocess_v210.py` replaces unbounded
  `capture_output=True`; all five processes drain incrementally and
  retain only the first/last 32 KiB of output in private 0600 files. Failure,
  timeout and truncated stream metadata stay outside Git.
- `private_pipeline_status_v211.py --work <PRIVATE_WORK_DIR>` emits only
  a small, private-safe checkpoint status, making progress inspectable
  after the chat stream drops without ever copying the log into ChatGPT.
- Synthetic CI: V210 Linux/Windows
  https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41308752559 ;
  V211 Linux/Windows
  https://github.com/ProhorovIlja/bloodborne_pc_windows_port/actions/runs/41308942452 .
- Keep PR/CI reads bounded and source reads to specific line spans. No full
  logs, PR diffs, game binaries or whole long chat imports into the response.
- If UI failures persist even with small chat/tool calls: test hard refresh
  and a new conversation in the same Project, incognito without extensions,
  no VPN/proxy, different network; collect request timestamps/IDs and contact
  OpenAI Support if reproduced across devices. Official guidance:
  https://help.openai.com/en/articles/7996703-troubleshooting-chatgpt-error-messages .
- Neither source-only synthetic CI nor a clean stream establishes successful
  full-game AOT, true five-player gameplay, native Bloodborne boot, or P2P.
