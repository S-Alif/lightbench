# Where jobs are stored

Each job is one folder:

```
<job folder>/
  job.json    settings + results (the history record)
  out/        the finished files
  thumbs/     previews for the history cards
  in/         uploads, removed as soon as each file is processed
```

By default it is `data/jobs/<id>/`. In the New job page, "Where to save" lets you choose another root folder: the job then lives at `<your folder>/<id>/`, laid out exactly like `data/jobs`. The whole job is saved there (results, previews and the history record), nothing is stored twice, and it still shows in History. This only works on the computer that runs the app.

## data/job-locations.json

History follows this file, it does not scan a folder. It is a JSON array with one object per job:

```json
[
  {
    "id": "3f9c1a7b2d4e",
    "path": "/home/you/Pictures/Lightbench/3f9c1a7b2d4e",
    "created": 1795765320.5
  }
]
```

- **Objects, not bare strings**, so a field can be added later without breaking anything. Keys the app does not know are kept when it rewrites the file, and so are entries that are not objects.
- `path` is written absolute. A relative path typed by hand is read from the `data` folder; `~` means your home folder.
- **Existing installs:** the first launch adds every folder already in `data/jobs/` to the file. Nothing is moved. Folders copied into `data/jobs/` later are added the same way.
- **Edit it by hand while the app runs:** it is re-read when it changes (and whenever History is opened).
- **Broken file:** never overwritten. It is renamed to `job-locations.json.broken-<time>` and the list is rebuilt from `data/jobs/`.

## When a folder can't be reached

(unplugged drive, renamed or deleted folder, wrong path) the job shows in History as a "Can't reach this job" card that can't be opened, with the reason and the path. Fix the path in the file or reconnect the drive and press "Check again". The trash button only removes it from the list; no files are touched. Nothing else is affected.

## Deleting a job

- A job in `data/jobs/`: its folder is deleted.
- A job in a folder you chose: only the files the job created are deleted (results, previews, `job.json`). The folder is removed only if it is then empty, so anything else you put there is kept.
- An unreachable job: only the list entry is removed.
