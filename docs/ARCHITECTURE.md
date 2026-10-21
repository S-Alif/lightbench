# Architecture

## Rules that keep the project safe to extend

1. **Dependencies point one way.** `api` -> `services` -> `core`. Code in `core` never imports from `api` or `services`.
2. **Only `backend/config.py` reads paths and environment variables.** Everything else imports from it.
3. **One place per concern.** A new feature gets its own module in `core/`, its own route file in `api/routes/`, and its own folder in `frontend/src/features/`.
4. **`components/` never imports from `pages/` or `features/`.** Pages use features, features use components.

## Backend (`backend/`)

| Folder / file | What lives there |
| --- | --- |
| `main.py` | creates the Starlette app, mounts `api_routes` and the built frontend |
| `config.py` | `DATA_DIR`, `JOBS_DIR`, `MODELS_DIR`, `FONT_DIR`, `STATIC_DIR` |
| `api/router.py` | every url in one list |
| `api/routes/` | `system`, `models`, `jobs`, `files`, one module per group of endpoints |
| `api/deps.py` | the shared `JobManager` instance |
| `api/helpers.py` | error responses, safe file names, local-request check, job lookup |
| `api/spa.py` | static files with the index.html fallback for client side routes |
| `services/jobs/models.py` | `Item` and `Job`, and how they are saved to `job.json` |
| `services/jobs/manager.py` | `JobManager`: one worker thread, history loading, cancel, delete |
| `core/pipeline.py` | `JobOptions`, then upscale -> watermark -> save for an image or a video |
| `core/upscaler.py` | `Upscaler`: tiled inference with out-of-memory retry |
| `core/models/registry.py` | built-in model catalog, download, architecture detection (no torch) |
| `core/models/architectures.py` | `RRDBNet`, `SRVGGNetCompact` |
| `core/models/loader.py` | reads weight files, inspects custom models, builds the network |
| `core/media/` | `video.py` (ffmpeg pipes), `thumbnails.py`, `watermark.py`, `types.py` |
| `core/editing/operations.py` | `validate_edit` and `apply_edit`: rotate, then crop (images only) |

## Frontend (`frontend/src/`)

| Folder | What lives there |
| --- | --- |
| `api/client.js` | every call to the backend |
| `lib/` | `format.js`, `media.js`, `models.js`, `clipboard.js` |
| `hooks/` | `useRoute.js` (`useHashRoute`, `navigateTo`), `usePersistentState.js` (`useStored`) |
| `components/ui/` | buttons, badges, modal, toast, form fields |
| `components/cards/` | `CardShell`, `PickedCard`, `ResultCard`, `JobCard` |
| `components/layout/` | `Device`, `Banner` |
| `components/jobs/` | progress `Overlay`, `DeleteDialog` |
| `features/editor/` | `CropEditor` (opened from a picked image's "Crop / rotate" button), `cropPresets.js`, `editMath.js` |
| `features/settings/` | settings panel, defaults, controls, watermark preview |
| `pages/` | `NewJobPage`, `HistoryPage`, `JobDetailPage` |

## How a job flows

1. The browser posts files and options to `POST /api/jobs` (`api/routes/jobs.py`).
2. The route validates the options (`core/pipeline.JobOptions`), saves the uploads into `data/jobs/<id>/in/` and hands the job to `JobManager`.
3. The worker thread runs each file through `core/pipeline.py`: edit (`core/editing`), upscale (`core/upscaler.py`), watermark (`core/media/watermark.py`), save.
4. Progress is kept in memory and polled by the browser from `GET /api/jobs/{id}`. The finished state is written to `job.json`.

## Edits

The optional form field `edits` on `POST /api/jobs` is a JSON list with one entry per file, in the same order (`null` for no edit). An entry is `{"rotate": 0|90|180|270, "crop": {"x","y","width","height"} | null}`. Rotation is clockwise and happens first. Crop values are fractions (0 to 1) of the rotated image, so the browser preview and the output agree at any resolution. The edit is stored on the item in `job.json`.

## API

| Method | Url | Purpose |
| --- | --- | --- |
| GET | `/api/system` | device, ffmpeg and folder info |
| GET | `/api/models` | built-in and custom models |
| GET, POST | `/api/jobs` | list jobs, create a job |
| GET, DELETE | `/api/jobs/{id}` | one job, delete a job |
| POST | `/api/jobs/{id}/cancel` | cancel a running job |
| GET | `/api/jobs/{id}/zip` | all results as a .zip |
| POST | `/api/jobs/{id}/open-folder` | open the output folder (local machine only) |
| GET | `/api/jobs/{id}/items/{item}/file` | a result (`?inline=1` for previews) |
| POST | `/api/jobs/{id}/items/{item}/edit` | crop / rotate a finished image (`{"edit": ...}`); saved as a new job, the result is left as it is |
| GET | `/api/jobs/{id}/items/{item}/thumb` | a thumbnail |
