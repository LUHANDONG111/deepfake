# Original Video Name Design

## Goal

Show the uploaded video's original filename in the user's detection history and use that filename in the delete confirmation dialog.

## Backend

Add `TaskSession.original_filename` as a nullable string column. The upload endpoint stores the sanitized uploaded filename in this column, and task payloads include `original_filename` for list and detail responses.

For existing SQLite databases, startup compatibility code adds the column when it is missing. Older rows may have `NULL`; clients should fall back to the task id when no original filename is present.

## Frontend

The history table gains an "Original Video" column populated from `row.original_filename`. The delete confirmation text receives `name`, using the original filename when available and the task id as a fallback.

## Testing

Backend API tests cover upload persistence and task payload serialization. Frontend verification uses the existing Vite build.
