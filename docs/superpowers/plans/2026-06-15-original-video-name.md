# Original Video Name Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist and display each uploaded video's original filename in history and delete confirmations.

**Architecture:** Store the filename on `TaskSession`, expose it through existing task payloads, and render it in the Vue history table. Existing database compatibility follows the app's current startup column-add pattern.

**Tech Stack:** Flask, SQLAlchemy, SQLite, pytest, Vue 3, Element Plus, Vite.

---

### Task 1: Backend Persistence And Payload

**Files:**
- Modify: `backend/models.py`
- Modify: `backend/routes.py`
- Test: `backend/tests/test_api.py`

- [ ] **Step 1: Write failing tests**

Add assertions that uploading `sample video.mp4` stores `sample_video.mp4` in `TaskSession.original_filename` and that task list/detail payloads include `original_filename`.

- [ ] **Step 2: Run tests to verify failure**

Run: `python -m pytest backend/tests/test_api.py -q`
Expected: FAIL because `TaskSession` has no `original_filename`.

- [ ] **Step 3: Implement model and route changes**

Add `original_filename = db.Column(db.String(255), nullable=True)`, set it during upload from `secure_filename(file.filename)`, include it in `_task_payload`, and add startup SQLite column compatibility.

- [ ] **Step 4: Run backend tests**

Run: `python -m pytest backend/tests/test_api.py backend/tests/test_auth_admin.py -q`
Expected: PASS.

### Task 2: Frontend History Display

**Files:**
- Modify: `frontend/src/views/HistoryView.vue`
- Modify: `frontend/src/i18n/messages/en.js`
- Modify: `frontend/src/i18n/messages/zh.js`

- [ ] **Step 1: Add history column and delete label helper**

Insert an original filename column after Task ID and use `row.original_filename || row.id` for the delete confirmation parameter.

- [ ] **Step 2: Add i18n labels**

Add `common.originalVideo` and update history delete confirmation strings to use `{name}`.

- [ ] **Step 3: Run frontend build**

Run: `npm run build` from `frontend`
Expected: PASS.
