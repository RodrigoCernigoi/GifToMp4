from pathlib import Path
from queue import Queue
from threading import Barrier
from tempfile import TemporaryDirectory
import time
import unittest

from gif2mp4.batch import BatchConversionService, create_jobs
from gif2mp4.models import ConversionEvent, JobStatus


class FakeConverter:
    def convert(self, source: Path, destination: Path, overwrite: bool) -> None:
        time.sleep(0.01)


class ConcurrentFakeConverter:
    def __init__(self) -> None:
        self._barrier = Barrier(2)

    def convert(self, source: Path, destination: Path, overwrite: bool) -> None:
        self._barrier.wait(timeout=2)


class BatchConversionTests(unittest.TestCase):
    def test_create_jobs_avoids_duplicate_output_names(self) -> None:
        sources = [Path("first\\clip.gif"), Path("second\\clip.gif")]

        jobs = create_jobs(sources, Path("output"))

        self.assertEqual(
            [job.destination.name for job in jobs],
            ["clip.mp4", "clip (2).mp4"],
        )

    def test_batch_emits_success_and_skipped_events(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "animation.gif"
            source.touch()
            output_directory = root / "output"
            output_directory.mkdir()
            existing_output = output_directory / "animation.mp4"
            existing_output.touch()
            jobs = create_jobs([source], output_directory)
            events: Queue[ConversionEvent] = Queue()
            service = BatchConversionService(FakeConverter())
            try:
                futures = service.submit(jobs, False, events)
                for future in futures:
                    future.result(timeout=2)
            finally:
                service.shutdown()

            event = events.get_nowait()
            self.assertEqual(event.status, JobStatus.RUNNING)
            self.assertEqual(events.get_nowait().status, JobStatus.SKIPPED)
            self.assertTrue(events.empty())

    def test_batch_converts_two_jobs_concurrently(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            jobs = create_jobs(
                [Path("first.gif"), Path("second.gif")],
                root,
            )
            events: Queue[ConversionEvent] = Queue()
            service = BatchConversionService(ConcurrentFakeConverter(), max_workers=2)
            try:
                futures = service.submit(jobs, False, events)
                for future in futures:
                    future.result(timeout=3)
            finally:
                service.shutdown()

            statuses = [events.get_nowait().status for _ in range(events.qsize())]
            self.assertEqual(statuses.count(JobStatus.RUNNING), 2)
            self.assertEqual(statuses.count(JobStatus.SUCCEEDED), 2)


if __name__ == "__main__":
    unittest.main()
