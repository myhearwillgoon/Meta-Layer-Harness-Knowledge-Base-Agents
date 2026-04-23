# Knowledge Base

This directory contains the knowledge base Markdown files for the Meta Layer Harness system.

## Structure

```
knowledge-base/
├── people/          # Person profiles and informal notes
├── projects/        # Project documents and strategies
├── decisions/       # Meeting minutes, memos, research notes
├── vendors/         # External vendor information
└── policies/        # Company policies and guidelines
}
```

## Setup

1. **Obtain the knowledge base files** from the project administrator
2. **Place the 77 Markdown files** into the appropriate subdirectories
3. **Run the indexer** to build the search index:

```bash
python main.py
```

## File Naming Convention

- People: `{firstname}-{lastname}.md` or `lp-{name}.md` for LPs
- Projects: `{project-name}.md`
- Decisions: `{type}-{date}.md` (e.g., `investment-committee-2026-03-15.md`)
- Vendors: `vendor-{name}.md` or `external-{name}.md`
- Policies: `{topic}.md` (e.g., `risk-framework-2026.md`)

## Wiki Links

Files can reference each other using wiki link syntax:
```markdown
See [[btc-allocation-strategy]] for details.
Refer to [[alex-chen]] for approval.
```

The system will automatically parse these links and build a backlink graph.
