from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from queue import Queue

from gif2mp4.converter import ConversionError, FFmpegConverter
from gif2mp4.models import ConversionEvent, ConversionJob, JobStatus


def create_jobs(sources: list[Path], output_directory: Path) -> list[ConversionJob]:
    jobs: list[ConversionJob] = []
    reserved_names: set[str] = set()

    for source in sources:
        base_name = f"{source.stem}.mp4"
        candidate = base_name
        suffix = 2
        while candidate.casefold() in reserved_names:
            candidate = f"{source.stem} ({suffix}).mp4"
            suffix += 1
        reserved_names.add(candidate.casefold())
        jobs.append(ConversionJob(source=source, destination=output_directory / candidate))

    return jobs


class BatchConversionService:
    def __init__(self, converter: FFmpegConverter, max_workers: int = 2) -> None:
        self._converter = converter
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def submit(
        self,
        jobs: list[ConversionJob],
        overwrite: bool,
        events: Queue[ConversionEvent],
    ) -> list[Future[None]]:
        return [
            self._executor.submit(self._convert_one, job, overwrite, events)
            for job in jobs
        ]

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)

    def _convert_one(
        self,
        job: ConversionJob,
        overwrite: bool,
        events: Queue[ConversionEvent],
    ) -> None:
        events.put(ConversionEvent(job.source, JobStatus.RUNNING, "Convertendo..."))
        if job.destination.exists() and not overwrite:
            events.put(
                ConversionEvent(
                    job.source,
                    JobStatus.SKIPPED,
                    "O arquivo de destino já existe.",
                )
            )
            return

        try:
            self._converter.convert(job.source, job.destination, overwrite)
        except FileExistsError:
            events.put(
                ConversionEvent(
                    job.source,
                    JobStatus.SKIPPED,
                    "O arquivo de destino já existe.",
                )
            )
        except (ConversionError, OSError) as error:
            events.put(ConversionEvent(job.source, JobStatus.FAILED, str(error)))
        else:
            events.put(ConversionEvent(job.source, JobStatus.SUCCEEDED, "Concluído."))
