"""POST /api/tools/*: convert, collage, split and palette. Nothing is stored, results go back in the response
(or, on the computer that runs the app, into the folder the person picked)."""
from __future__ import annotations

import json
from urllib.parse import quote

from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse, Response

from ...services import tools as tools_service
from ..helpers import error_response, is_local_request, safe_name


async def _read_form(request):
    form = await request.form()
    raw_options = json.loads(form.get("options") or "{}")
    if not isinstance(raw_options, dict):
        raise ValueError("options must be an object")
    save_to = raw_options.pop("save_to", None) or None
    if save_to and not is_local_request(request):
        raise PermissionError("Saving to a folder only works on the computer that runs the app.")
    return form, raw_options, save_to


def _answer(output):
    if output.saved is not None:
        return JSONResponse({"saved": output.saved, "width": output.width, "height": output.height, "note": output.note,
                             "bytes": len(output.data), "ext": output.ext})
    headers = {"X-Width": str(output.width), "X-Height": str(output.height), "X-Ext": output.ext,
               "X-Note": output.note.encode("ascii", "replace").decode(),
               "Content-Disposition": f"attachment; filename*=UTF-8''{quote(output.name)}",
               "Access-Control-Expose-Headers": "X-Width, X-Height, X-Ext, X-Note"}
    return Response(output.data, media_type=output.mime, headers=headers)


async def _single(request, work):
    try:
        form, raw_options, save_to = await _read_form(request)
        upload = form.get("file")
        if not hasattr(upload, "read"):
            return error_response("No image uploaded")
        output = await run_in_threadpool(work, await upload.read(), safe_name(upload.filename or "image"), raw_options, save_to)
    except PermissionError as denied:
        return error_response(str(denied), 403)
    except (ValueError, TypeError) as bad_input:
        return error_response(str(bad_input))
    except OSError:
        return error_response("That file could not be read as an image.", 415)
    return _answer(output)


async def convert(request):
    return await _single(request, tools_service.convert)


async def split(request):
    return await _single(request, tools_service.split)


async def collage(request):
    try:
        form, raw_options, save_to = await _read_form(request)
        uploads = [upload for upload in form.getlist("files") if hasattr(upload, "read")]
        files = [(safe_name(upload.filename or "image"), await upload.read()) for upload in uploads]
        output = await run_in_threadpool(tools_service.collage, files, raw_options, save_to)
    except PermissionError as denied:
        return error_response(str(denied), 403)
    except (ValueError, TypeError) as bad_input:
        return error_response(str(bad_input))
    except OSError:
        return error_response("One of the files could not be read as an image.", 415)
    return _answer(output)


async def palette(request):
    try:
        form, raw_options, _ = await _read_form(request)
        upload = form.get("file")
        if not hasattr(upload, "read"):
            return error_response("No image uploaded")
        colours = await run_in_threadpool(tools_service.palette, await upload.read(), raw_options.get("count", 6))
    except (ValueError, TypeError) as bad_input:
        return error_response(str(bad_input))
    except OSError:
        return error_response("That file could not be read as an image.", 415)
    return JSONResponse({"colours": colours})
