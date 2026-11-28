import io
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

from backend.services.jobs import JobManager, locations as locations_module
from backend.services.jobs import manager as manager_module
from backend.services.jobs import models as models_module


class Sandbox:
    """a throw-away data folder, with the app's paths pointed at it."""
    def __enter__(self):
        self.folder = tempfile.TemporaryDirectory()
        self.data = Path(self.folder.name) / "data"
        self.jobs_dir = self.data / "jobs"
        self.file = self.data / "job-locations.json"
        self.patches = [mock.patch.object(manager_module, "DATA_DIR", self.data), mock.patch.object(manager_module, "JOBS_DIR", self.jobs_dir),
                        mock.patch.object(manager_module, "LOCATIONS_FILE", self.file), mock.patch.object(models_module, "JOBS_DIR", self.jobs_dir)]
        for patch in self.patches:
            patch.start()
        return self

    def __exit__(self, *args):
        for patch in self.patches:
            patch.stop()
        self.folder.cleanup()

    def old_style_job(self, folder: Path, job_id: str, created: float = 1700000000.0) -> Path:
        """a job folder exactly as the version before job-locations.json wrote it."""
        (folder / "out").mkdir(parents=True)
        (folder / "thumbs").mkdir()
        (folder / "out" / "photo-x2.png").write_bytes(b"result")
        (folder / "thumbs" / "it1.jpg").write_bytes(b"thumb")
        item = {"id": "it1", "name": "photo.png", "kind": "image", "status": "done", "progress": None, "message": None, "out_name": "photo-x2.png",
                "error": None, "size": 6, "src_size": 3, "w": 10, "h": 10, "duration": 0, "thumb": True, "edit": None}
        (folder / "job.json").write_text(json.dumps({"version": 1, "id": job_id, "created": created, "started": created, "finished": created + 5, "opts": {"scale": 2}, "items": [item]}))
        return folder

    def entries(self):
        return json.loads(self.file.read_text())


class LocationsFileTest(unittest.TestCase):
    def test_old_install_is_adopted_and_nothing_is_lost(self):
        with Sandbox() as box:
            first = box.old_style_job(box.jobs_dir / "aaaaaaaaaaaa", "aaaaaaaaaaaa", 1700000000.0)
            box.old_style_job(box.jobs_dir / "bbbbbbbbbbbb", "bbbbbbbbbbbb", 1700001000.0)
            (box.jobs_dir / "not-a-job").mkdir()
            manager = JobManager()
            self.assertEqual([job.id for job in manager.list()], ["bbbbbbbbbbbb", "aaaaaaaaaaaa"])
            self.assertEqual(manager.get("aaaaaaaaaaaa").items[0].status, "done")
            entries = box.entries()
            self.assertIsInstance(entries, list)
            self.assertTrue(all(isinstance(entry, dict) for entry in entries))
            self.assertEqual({entry["id"]: entry["path"] for entry in entries}["aaaaaaaaaaaa"], str(first))
            self.assertTrue(all(Path(entry["path"]).is_absolute() and {"id", "path", "created"} <= set(entry) for entry in entries))
            self.assertEqual(len(entries), 2)

    def test_unknown_keys_and_foreign_items_survive_rewrites(self):
        with Sandbox() as box:
            box.old_style_job(box.jobs_dir / "aaaaaaaaaaaa", "aaaaaaaaaaaa")
            box.data.mkdir(exist_ok=True)
            box.file.write_text(json.dumps([{"id": "aaaaaaaaaaaa", "path": str(box.jobs_dir / "aaaaaaaaaaaa"), "created": 1.0, "label": "holiday", "future": {"a": 1}}, "just a note"]))
            manager = JobManager()
            manager.locations.register("cccccccccccc", box.data / "x", 5.0)   # forces a rewrite
            saved = box.entries()
            kept = next(entry for entry in saved if entry["id"] == "aaaaaaaaaaaa")
            self.assertEqual((kept["label"], kept["future"], kept["created"]), ("holiday", {"a": 1}, 1.0))
            self.assertIn("just a note", saved)

    def test_a_broken_file_is_kept_aside_and_rebuilt(self):
        with Sandbox() as box:
            box.old_style_job(box.jobs_dir / "aaaaaaaaaaaa", "aaaaaaaaaaaa")
            box.data.mkdir(exist_ok=True)
            box.file.write_text("{ this is not json")
            JobManager()
            self.assertEqual(len(list(box.data.glob("job-locations.json.broken-*"))), 1)
            self.assertEqual([entry["id"] for entry in box.entries()], ["aaaaaaaaaaaa"])

    def test_relative_and_home_paths_are_understood(self):
        with Sandbox() as box:
            table = locations_module.Locations(box.file, box.data)
            self.assertEqual(table.path_of({"id": "x", "path": "jobs/x"}), box.data / "jobs" / "x")
            self.assertTrue(table.path_of({"id": "x", "path": "~/somewhere"}).is_absolute())


class UnreachableTest(unittest.TestCase):
    def test_missing_folder_becomes_a_card_not_a_crash_and_comes_back(self):
        with Sandbox() as box:
            drive = Path(box.folder.name) / "drive" / "job1"
            box.data.mkdir(exist_ok=True)
            box.file.write_text(json.dumps([{"id": "dddddddddddd", "path": str(drive), "created": 9.0}]))
            manager = JobManager()
            self.assertEqual(manager.list(), [])
            lost = manager.unreachable()
            self.assertEqual((lost[0]["id"], lost[0]["reason"], lost[0]["path"]), ("dddddddddddd", "Folder not found", str(drive)))
            self.assertIsNone(manager.get("dddddddddddd"))
            box.old_style_job(drive, "dddddddddddd")                     # drive plugged in
            self.assertEqual([job.id for job in manager.list()], ["dddddddddddd"])
            self.assertEqual(manager.unreachable(), [])

    def test_fixing_the_path_by_hand_while_the_app_runs(self):
        with Sandbox() as box:
            box.data.mkdir(exist_ok=True)
            box.file.write_text(json.dumps([{"id": "eeeeeeeeeeee", "path": str(box.data / "nowhere"), "created": 1.0}]))
            manager = JobManager()
            self.assertEqual(len(manager.unreachable()), 1)
            new_home = box.old_style_job(Path(box.folder.name) / "moved", "eeeeeeeeeeee")
            time.sleep(0.01)
            box.file.write_text(json.dumps([{"id": "eeeeeeeeeeee", "path": str(new_home), "created": 1.0, "extra": True}]) + "\n")
            self.assertEqual([job.id for job in manager.list()], ["eeeeeeeeeeee"])
            self.assertEqual(manager.get("eeeeeeeeeeee").dir, new_home)

    def test_a_folder_holding_another_job_or_none_is_flagged(self):
        with Sandbox() as box:
            other = box.old_style_job(Path(box.folder.name) / "other", "ffffffffffff")
            empty = Path(box.folder.name) / "empty"
            empty.mkdir()
            box.data.mkdir(exist_ok=True)
            box.file.write_text(json.dumps([{"id": "111111111111", "path": str(other), "created": 1.0}, {"id": "222222222222", "path": str(empty), "created": 2.0}]))
            reasons = {entry["id"]: entry["reason"] for entry in JobManager().unreachable()}
            self.assertEqual(reasons, {"111111111111": "That folder holds a different job", "222222222222": "No Lightbench job in that folder"})

    def test_removing_an_unreachable_card_touches_no_files(self):
        with Sandbox() as box:
            keep = Path(box.folder.name) / "keep"
            keep.mkdir()
            (keep / "precious.txt").write_text("hi")
            box.data.mkdir(exist_ok=True)
            box.file.write_text(json.dumps([{"id": "333333333333", "path": str(keep), "created": 1.0}]))
            manager = JobManager()
            manager.delete("333333333333")
            self.assertEqual((box.entries(), (keep / "precious.txt").read_text()), ([], "hi"))


class DeleteTest(unittest.TestCase):
    def test_default_folder_job_is_removed_completely(self):
        with Sandbox() as box:
            folder = box.old_style_job(box.jobs_dir / "aaaaaaaaaaaa", "aaaaaaaaaaaa")
            manager = JobManager()
            manager.delete("aaaaaaaaaaaa")
            self.assertFalse(folder.exists())
            self.assertEqual(box.entries(), [])

    def test_job_in_a_chosen_folder_leaves_everything_it_did_not_create(self):
        with Sandbox() as box:
            folder = box.old_style_job(Path(box.folder.name) / "Pictures" / "run1", "aaaaaaaaaaaa")
            (folder / "out" / "mine.txt").write_text("not from lightbench")
            (folder / "notes.txt").write_text("also mine")
            box.data.mkdir(exist_ok=True)
            box.file.write_text(json.dumps([{"id": "aaaaaaaaaaaa", "path": str(folder), "created": 1.0}]))
            manager = JobManager()
            manager.delete("aaaaaaaaaaaa")
            self.assertFalse((folder / "job.json").exists() or (folder / "out" / "photo-x2.png").exists() or (folder / "thumbs").exists())
            self.assertEqual(((folder / "out" / "mine.txt").read_text(), (folder / "notes.txt").read_text()), ("not from lightbench", "also mine"))
            self.assertEqual(box.entries(), [])

    def test_empty_chosen_folder_is_tidied_away(self):
        with Sandbox() as box:
            folder = box.old_style_job(Path(box.folder.name) / "Pictures" / "run1", "aaaaaaaaaaaa")
            box.data.mkdir(exist_ok=True)
            box.file.write_text(json.dumps([{"id": "aaaaaaaaaaaa", "path": str(folder), "created": 1.0}]))
            JobManager().delete("aaaaaaaaaaaa")
            self.assertFalse(folder.exists())


class LocalRequestTest(unittest.TestCase):
    def check(self, client_host, server_host="0.0.0.0"):
        from types import SimpleNamespace
        from backend.api.helpers import is_local_request
        client = SimpleNamespace(host=client_host) if client_host else None
        return is_local_request(SimpleNamespace(client=client, scope={"server": (server_host, 8000)}))

    def test_same_computer_in_every_spelling(self):
        for host in ("127.0.0.1", "127.0.1.1", "::1", "::ffff:127.0.0.1", "localhost"):
            self.assertTrue(self.check(host), host)
        self.assertTrue(self.check("192.168.1.20", server_host="192.168.1.20"))   # opened through the computer's own address

    def test_other_computers_are_not_local(self):
        self.assertFalse(self.check("192.168.1.99", server_host="192.168.1.20"))
        self.assertFalse(self.check(None))


class EndToEndTest(unittest.TestCase):
    def test_a_job_kept_in_a_chosen_folder_runs_and_is_listed_from_there(self):
        from starlette.testclient import TestClient
        from backend.api import helpers
        from backend.api.routes import jobs as jobs_routes
        from backend.main import app
        with Sandbox() as box:
            manager = JobManager()
            chosen = Path(box.folder.name) / "My Pictures"
            buffer = io.BytesIO()
            Image.new("RGB", (40, 30), (200, 10, 10)).save(buffer, "PNG")
            with mock.patch.object(jobs_routes, "manager", manager), mock.patch.object(helpers, "manager", manager):
                client = TestClient(app)
                post = lambda options: client.post("/api/jobs", files=[("files", ("a.png", buffer.getvalue(), "image/png"))], data={"options": json.dumps(options)})
                self.assertEqual(post({"scale": 1, "fmt": "png", "location": str(chosen)}).status_code, 403)   # not the local computer
                with mock.patch.object(jobs_routes, "is_local_request", lambda request: True):
                    created = post({"scale": 1, "fmt": "png", "location": str(chosen)})
                    self.assertEqual(created.status_code, 200, created.text)
                    job_id = created.json()["id"]
                    for _ in range(100):
                        state = client.get(f"/api/jobs/{job_id}").json()
                        if state["status"] not in ("queued", "running"):
                            break
                        time.sleep(0.1)
                    self.assertEqual(state["status"], "done", state)
                    folder = next(chosen.iterdir())
                    self.assertEqual(folder.name, job_id)
                    for _ in range(50):                       # the worker tidies up (removes in/) just after the job reads as done
                        names = sorted(path.name for path in folder.iterdir())
                        if names == ["job.json", "out", "thumbs"]:
                            break
                        time.sleep(0.1)
                    self.assertEqual(names, ["job.json", "out", "thumbs"])
                    self.assertEqual(box.entries()[0]["path"], str(folder))
                    self.assertEqual(list(box.jobs_dir.iterdir()), [])             # nothing stored in the app's own folder
                    self.assertNotIn("location", json.loads((folder / "job.json").read_text())["opts"])
                    self.assertEqual(client.get(f"/api/jobs/{job_id}/items/{state['items'][0]['id']}/thumb").status_code, 200)
                    # a restart finds it again through the list
                    again = JobManager()
                    self.assertEqual([job.id for job in again.list()], [job_id])
                    # the drive goes away: History shows a card, other routes explain
                    folder.rename(folder.with_name("renamed"))
                    listing = client.get("/api/jobs").json()
                    self.assertEqual((listing["jobs"], listing["unreachable"][0]["id"]), ([], job_id))
                    self.assertEqual(client.get(f"/api/jobs/{job_id}").status_code, 409)
                    self.assertEqual(client.delete(f"/api/jobs/{job_id}").status_code, 200)
                    self.assertTrue((folder.with_name("renamed") / "out").is_dir())   # forgetting never deletes files


if __name__ == "__main__":
    unittest.main()
