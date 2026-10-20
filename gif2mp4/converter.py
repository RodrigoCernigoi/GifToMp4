import os
import subprocess
import tempfile
from pathlib import Path

import imageio_ffmpeg


class ConversionError(Exception):
    """A GIF could not be converted to MP4."""


class FFmpegConverter:
    def convert(self, source: Path, destination: Path, overwrite: bool) -> None:
        if not source.is_file():
            raise ConversionError(f"Arquivo de entrada não encontrado: {source}")

        reserved_destination = False
        temporary_output: Path | None = None
        try:
            if not overwrite:
                descriptor = os.open(
                    destination,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    0o600,
                )
                os.close(descriptor)
                reserved_destination = True

            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{destination.stem}.",
                suffix=".tmp.mp4",
                dir=destination.parent,
            )
            os.close(descriptor)
            temporary_output = Path(temporary_name)

            command = [
                imageio_ffmpeg.get_ffmpeg_exe(),
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(source),
                "-vf",
                "scale=trunc(iw/2)*2:trunc(ih/2)*2:flags=lanczos,format=yuv420p",
                "-c:v",
                "libx264",
                "-movflags",
                "+faststart",
                str(temporary_output),
            ]
            subprocess.run(command, check=True, capture_output=True, text=True)
            os.replace(temporary_output, destination)
            reserved_destination = False
        except FileExistsError:
            raise
        except subprocess.CalledProcessError as error:
            detail = error.stderr.strip() if error.stderr else "Erro desconhecido do FFmpeg."
            raise ConversionError(detail) from error
        except OSError as error:
            raise ConversionError(str(error)) from error
        finally:
            if temporary_output is not None:
                temporary_output.unlink(missing_ok=True)
            if reserved_destination:
                destination.unlink(missing_ok=True)
