# Picture tools

Page: `/tools`. Everyday jobs, no AI, so the result is exactly what the settings say. Nothing is stored: results come back in the response, or are written to a folder the person chose.

| tool | what it does |
| --- | --- |
| Convert | format (same / JPG / PNG / WebP), quality or "at most N KB", resize (percent or fit in a box, never enlarges), brightness / contrast / saturation / sharpen, metadata (remove all / only GPS location / keep). Many pictures at once, one request each, so progress is real |
| Collage | grid of 2 to 60 pictures: columns, cell shape, fill or show whole, gap, margin, background or transparent, JPG or PNG |
| Split | cut one picture into rows x columns tiles (no pixel lost), zip of tiles |
| Colours | main colours of a picture, click to copy |

Details that matter: the camera's rotation flag is applied to the pixels before metadata is removed (so removing it never turns a photo sideways), the colour profile is always kept, transparency becomes a chosen colour when saving as JPG, and the loaded picture is never modified between requests.

## Saving outside the app

`save_to` (tools) writes the results into a folder on the computer that runs the app instead of returning them. Requests from other computers get 403. Names are never overwritten (`name-2.png`). Upscale jobs can be kept in a folder of your choice too: see `JOB_LOCATIONS.md`.

API: `POST /api/tools/{convert,collage,split,palette}`.
