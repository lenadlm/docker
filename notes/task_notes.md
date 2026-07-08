# Hermes Task State Management Protocol

You are responsible for maintaining reliable continuity across long-running tasks and sessions. To accomplish this, maintain a **temporary task state** that is completely separate from your long-term memory (MEMORY.md), user preferences (USER.md), and reusable Skills.

## Purpose

The task state exists only to track the progress of the **current task**.

It is **not** a knowledge base, documentation system, or long-term memory.

Never store permanent knowledge, user preferences, reusable procedures, or lessons learned in the task state.

---

# Task Workspace

Maintain the following workspace under:

```text
~/.hermes/tasks
```

```
CURRENT_TASK.md
TASK_HISTORY/
ARTIFACTS/
```

The workspace has the following purposes:

* **CURRENT_TASK.md**

  * The active task only.
  * Always represents the latest state.

* **TASK_HISTORY/**

  * Archive completed task summaries.
  * Never read automatically unless specifically relevant.

* **ARTIFACTS/**

  * Temporary files created during investigation.
  * Examples:

    * command outputs
    * generated configs
    * comparisons
    * notes
    * temporary scripts

---

# Starting a Task

When a new request begins:

1. Check whether `CURRENT_TASK.md` exists.

2. If it does not exist:

   * Create a new task.

3. If it exists:

   * Compare the stored request with the current request.

4. If it is clearly the same task:

   * Resume from the recorded state.

5. If it is a different task:

   * Move the previous task into `TASK_HISTORY/`.
   * Start a new `CURRENT_TASK.md`.

Do not mix unrelated tasks.

---

# CURRENT_TASK.md Format

Maintain the file in Markdown using the following structure.

```markdown
# Current Task

Updated:
<ISO timestamp>

Status:
Planning | Investigating | Implementing | Testing | Waiting | Completed | Blocked

Progress:
<0-100% estimate>

---

## Original Request

<User request, quoted or tightly paraphrased>

---

## Success Criteria

- Desired outcome
- Desired outcome
- Desired outcome

---

## Confirmed Facts

- Verified facts only.
- Never include assumptions.

---

## Working Hypotheses

- Possible explanations.
- Clearly distinguish these from facts.

---

## Assumptions

- Assumptions currently being used.
- Remove them if proven false.

---

## Files Modified

- path
- path

---

## Commands Executed

- command
- command

Only include commands that materially advance the task.

---

## Important Findings

Record discoveries that would be costly to rediscover.

Examples:

- exact error messages
- configuration values
- ports
- paths
- versions
- root causes

---

## Open Questions

Information still required.

---

## Next Steps

Ordered list of the next actions.

---

## Completion Summary

Populate only when the task is complete.

Include:

- what was accomplished
- important decisions
- remaining caveats
```

---

# Updating the Task State

Do **not** update after every tool call.

Update only when one of the following occurs:

* a milestone is reached
* a diagnosis changes
* a file is modified
* a command produces important information
* an error is discovered
* the implementation plan changes
* user requirements change
* testing completes
* the task finishes

Avoid unnecessary rewrites.

---

# Recovering Context

If you become uncertain about:

* what has already been done
* current progress
* previous conclusions
* remaining work

Stop.

Re-read `CURRENT_TASK.md`.

Use it as the authoritative record of the current task before continuing.

---

# Separation of Responsibilities

Never duplicate information across storage systems.

Use each system only for its intended purpose.

**Skills**

* Reusable workflows
* Best practices
* Procedures
* Techniques

**MEMORY.md**

* Durable project knowledge
* Long-term facts

**USER.md**

* User preferences
* Stable environment details
* Persistent configuration preferences

**CURRENT_TASK.md**

* Temporary progress
* Investigation state
* Current discoveries
* Next actions

---

# Completion

When the task is completed:

1. Update the completion summary.

2. Mark the status as `Completed`.

3. Archive the task into `TASK_HISTORY/`.

4. Create a fresh `CURRENT_TASK.md` only when a new unrelated task begins.

Do not retain stale task state indefinitely.

---

# Guiding Principles

* Treat `CURRENT_TASK.md` as the single source of truth for the active task.
* Distinguish facts from assumptions.
* Record only information that would be expensive to rediscover.
* Keep the document concise, current, and actionable.
* Prefer updating existing sections over adding unnecessary detail.
* Never use the task state as a substitute for long-term memory.
