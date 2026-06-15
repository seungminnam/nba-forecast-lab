# Dashboard Portfolio Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the first dashboard screen communicate the verified forecasting
story immediately while preserving honest historical-snapshot labeling.

**Architecture:** Extract the default replay scenario into one
`FEATURED_SERIES` constant, reuse the existing replay application workflow for
a cached hero forecast, and apply presentation-only polish around the existing
four-tab product. No model, data, or simulation contract changes.

**Tech Stack:** Streamlit, Altair, pytest AppTest, HTML/CSS

---

### Task 1: Hero Forecast Contract

**Files:**
- Modify: `tests/test_streamlit_app.py`
- Modify: `streamlit_app.py`

- [x] Write failing AppTest assertions for the historical forecast card,
  factual performance badges, fallback behavior, and shared widget defaults.
- [x] Run focused tests and verify they fail for missing polish behavior.
- [x] Add `FEATURED_SERIES` and cached snapshot/model/replay helpers.
- [x] Render the featured historical forecast card and separate performance
  badges without claiming the snapshot is live.
- [x] Reuse `FEATURED_SERIES` for Replay-tab defaults.
- [x] Run focused AppTest tests.

### Task 2: Visual Finish

**Files:**
- Modify: `tests/test_streamlit_app.py`
- Modify: `streamlit_app.py`

- [x] Write failing assertions for semantic notice icons and footer content.
- [x] Apply a shared dark Altair chart configuration.
- [x] Add semantic notice icons and a factual GitHub/snapshot footer.
- [x] Run focused AppTest tests.

### Task 3: Documentation and Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/runbook.md`
- Modify: `docs/superpowers/plans/2026-06-15-dashboard-polish.md`

- [x] Document the featured historical forecast and snapshot disclosure.
- [x] Keep the Live Demo section honest until a public URL is confirmed.
- [x] Run `ruff check .`, `mypy src`, `pytest`, and `git diff --check`.
- [x] Visually verify the local dashboard.
- [x] Audit generated files and public claims.
- [ ] Commit, push, and open a Draft PR.
