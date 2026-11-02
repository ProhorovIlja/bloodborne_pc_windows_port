# CI observability: safe output contract

Scope: Seamless Hunt, Yharnam Together, native PC port, server, launcher, gameplay, all current and future **open** pull requests. This is an observability rule; it does not assert gameplay or network correctness.

## Do not fetch full Actions logs into ChatGPT

**Never call GitHub \`fetch_workflow_job_logs\`**, download whole run logs, fetch \`/actions/runs/{id}/logs\`, or print entire job JSON, all PR diffs, build outputs, packet captures, or source trees into a tool response. The upstream GitHub backend can return tens of megabytes before output truncation, and truncating after receiving it will NOT protect SSE transport.

Use these sources in this order:

1. PR metadata: head SHA, base, Draft/merged status.
2. Explicit run ID and result, selecting at most 3 latest runs (no wide \`per_page=100\` runs collection).
3. \`fetch_workflow_run_jobs\` or \`fetch_workflow_job_steps\`; output ONLY job name, conclusion and failed/in-progress step. Avoid full job objects.
4. GitHub check-run **summaries** or small annotations if an approved connector supports that endpoint. Not available is not success.
5. Read the **relevant source file only**, preferably at most 100 lines using \`fetch_file(start_line,end_line)\` or an individual changed-file patch. Never retrieve a whole giant PR patch as a shortcut.
6. If error text is still unavailable, amend a Draft workflow to separate preflight, staging, compilation, runtime and source-diff checks; emit an \`::error\` with at most 360 characters and save a *bounded* diagnostic artifact. Inspect the artifact size **before** download. Avoid full logs even when CI is red.

**Chat/tool result soft limit:** 16 KiB, never exceed 20 KiB in any displayed response. Some GitHub connector endpoints may generate huge backend responses *before* rendering; choose narrowly scoped endpoints, not client-side slicing of gigabytes.

## Run and artifact budgets

- Python \`tools/ci/ci_output_guard.py inspect-run --repo owner/repo --run-id N\` reads run/job/step metadata only. No log endpoints are implemented. Its JSON stdout is capped to 16,384 bytes.
- \`scan-local\` examines checkout workflows as text, without running them.
- \`audit-open-prs --repo owner/repo\` walks the default branch and currently open PR heads, reads only workflow text, deduplicates Git blob SHAs, reports suspicious patterns, and never executes untrusted branches.
- Each workflow file is capped at 64 KiB before retrieval. Every GitHub API response is capped at 1 MiB *inside CI*, and every externally produced report is capped at 16,384 bytes. A report can be incomplete when request, PR or file budgets are exhausted; **never treat incomplete as GREEN**.
- Findings are hints, not proof of a broken workflow. \`raw-actions-log-download\` is critical; unbounded \`cat\` of a log, \`tee\`, large \`tail\`, or unbounded Git diffs are flagged for review. Strict enforcement of legacy workflows requires review to avoid false positives.
- A failed CI compile should save **at most 6 KiB** of sanitized compiler diagnostics as a short-lived artifact. Never upload save data, decrypted game binaries, raw packets, player IPs, credentials, game files, or full build logs.

## CI behavior and limits

The new read-only workflow runs its unit tests and scans the checked-out branch on each push to the dedicated Draft PR. A daily scheduled cross-PR scan is effective **only after the workflow has been reviewed and merged into the default branch**. It covers the first 100 open PRs; if there are more, it marks coverage incomplete. It does not retroactively change jobs or old CI logs in other branches. Other active Draft PRs remain untouched.

Raw job logs are intentionally not accessible via this utility; however, no GitHub repo patch can disable an assistant's external connector endpoint. The interaction rule above must also be respected by any agent, automation or future CI investigator.

Keep all changes in Draft until tested. No merge, release or Fornex production deployment is implied.
