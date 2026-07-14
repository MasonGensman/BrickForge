# StudWorks Engineering Guide

## Project Mission

StudWorks transforms images into accurate, editable LEGO models and exports them seamlessly to BrickLink Studio for refinement.

StudWorks is **not** intended to replace BrickLink Studio.

The workflow is:

Image
→ Analysis
→ LEGO Model
→ Visualization
→ BrickLink Studio Export

BrickLink Studio remains the preferred environment for editing, instructions, and final refinement.

---

# Engineering Philosophy

Always favor:

- Maintainability
- Readability
- Simplicity
- Stability
- Incremental improvements

Avoid:

- Large rewrites without justification
- Unnecessary abstractions
- Premature optimization
- Scope creep

When improving existing code, preserve working behavior whenever practical.

---

# Development Workflow

Every feature is implemented as a numbered Package.

Each Package contains:

- Mission
- Scope
- Definition of Done
- Deliverables

Do not work outside the active package unless necessary.

If another subsystem must change, explain why.

---

# Coding Standards

- Follow existing project structure.
- Keep commits focused.
- Document significant design decisions.
- Remove dead code when appropriate.
- Do not duplicate functionality.
- Preserve public interfaces whenever practical.

---

# Quality Standards

Before considering work complete:

- Review your own implementation.
- Remove unnecessary complexity.
- Verify the project builds.
- Verify the package Definition of Done.
- Summarize every modified file.

---

# Current Active Package

Package_001.md