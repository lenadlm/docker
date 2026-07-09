# Enhance Existing Task Notes Protocol (Do Not Replace)

You already have an established Task Notes Protocol located at:

`notes/task_notes.md`

This protocol is the authoritative workflow for maintaining task continuity.

Do **NOT** replace it.

Do **NOT** create an alternative note-taking system.

Instead, extend and integrate it into a scalable knowledge architecture that minimizes built-in memory usage while maximizing continuity across sessions.

---

# Primary Principles

## 1. Task Notes remain the source of truth

`notes/task_notes.md` is the canonical record for:

* current work
* progress
* completed tasks
* blockers
* pending actions
* assumptions
* session continuity

Never duplicate its contents elsewhere.

---

## 2. Built-in Memory is NOT a knowledge base

Treat built-in memory as a lightweight index.

Its purpose is ONLY to remember:

* permanent user preferences
* long-term behavioural preferences
* locations of documentation
* high-level workflow rules

Never store:

* troubleshooting history
* project documentation
* command outputs
* research
* configuration
* implementation details
* session history
* temporary decisions

Whenever new information exceeds a few sentences, it belongs in documentation instead of memory.

---

# Existing Documentation First

Before answering any technical question:

1. Read `notes/task_notes.md`.

2. Determine whether the answer already exists.

3. If additional project documentation exists, consult it.

4. Reuse existing knowledge before asking the user again.

Avoid asking questions that have already been answered in previous sessions.

---

# Create a Knowledge Repository

Without changing the existing Task Notes workflow, maintain a separate long-term knowledge repository.

Recommended structure:

```text
notes/
│
├── task_notes.md          # Existing workflow (authoritative)
│
├── projects/
│   ├── homelab.md
│   ├── docker.md
│   ├── opnsense.md
│   ├── work.md
│   ├── ai.md
│   └── misc.md
│
├── knowledge/
│   ├── linux.md
│   ├── networking.md
│   ├── containers.md
│   ├── automation.md
│   ├── troubleshooting.md
│   └── best_practices.md
│
└── archive/
```

Do not duplicate information between files.

Each piece of information should have exactly one authoritative location.

---

# Knowledge Classification

Whenever new information is learned, classify it before saving.

## Temporary

Examples:

* today's task
* debugging progress
* current blocker

Store only in:

`task_notes.md`

---

## Project Knowledge

Examples:

* architecture
* configuration
* deployment
* design decisions
* implementation notes

Store in:

`notes/projects/<project>.md`

---

## Reusable Technical Knowledge

Examples:

* Docker best practices
* Linux commands
* OPNsense procedures
* coding standards
* networking concepts

Store in:

`notes/knowledge/*.md`

This knowledge should be reusable across multiple projects.

---

## Permanent User Preferences

Examples:

* preferred shell
* preferred editor
* preferred documentation style
* preferred coding style
* communication preferences

Store only in built-in memory.

Also mirror them in a readable preferences document if appropriate.

---

# Automatic Knowledge Promotion

During work:

Temporary discoveries remain in Task Notes.

When they become stable:

Move them into the appropriate project document.

When they become generally reusable:

Move them into the Knowledge repository.

Remove obsolete temporary notes after promotion.

Avoid maintaining the same information in multiple files.

---

# Memory Compression Policy

When built-in memory exceeds approximately 70% utilisation:

Automatically:

* remove duplicate memories
* merge similar preferences
* shorten verbose entries
* remove obsolete preferences
* replace detailed memories with references to documentation

The objective is to keep built-in memory as small as possible.

---

# Session Workflow

At the beginning of every session:

1. Read `notes/task_notes.md`.

2. Determine the active project.

3. Load only the relevant project documentation.

4. Load only the necessary reusable knowledge files.

Avoid loading unrelated projects.

---

At the end of every session:

Update `task_notes.md`.

If stable knowledge was created:

Move it into the appropriate project or knowledge document.

If temporary notes are no longer needed:

Remove or archive them.

---

# Documentation Standards

All project documentation should include:

* Purpose
* Current Status
* Architecture
* Configuration
* Decisions
* Outstanding Issues
* Lessons Learned
* References

Knowledge documents should contain only reusable information.

Task Notes should never become an encyclopedia.

---

# Behavioural Rules

Always prefer existing documentation over asking repeated questions.

Avoid duplicate documentation.

Avoid storing temporary information in memory.

Prefer promoting stable knowledge into Markdown.

Keep project knowledge separate from reusable knowledge.

Maintain concise, well-organized documentation.

Treat Task Notes as the working notebook and the Knowledge Repository as the long-term reference library.

---

# Success Criteria

The system should provide:

* seamless continuity across sessions
* minimal built-in memory usage
* zero duplication of information
* reusable project documentation
* reusable technical knowledge
* fast retrieval of previous decisions
* automatic promotion of stable knowledge
* automatic pruning of obsolete temporary information

The built-in memory should function only as a lightweight index, while `notes/task_notes.md` remains the operational notebook and the surrounding Markdown repository becomes the authoritative long-term knowledge base.
