import tkinter as tk
from pathlib import Path
from queue import Empty, Queue
from tkinter import filedialog, messagebox, ttk

from gif2mp4.batch import BatchConversionService, create_jobs
from gif2mp4.converter import FFmpegConverter
from gif2mp4.models import ConversionEvent, JobStatus


class GifToMp4App:
    def __init__(self, root: tk.Tk) -> None:
        self._root = root
        self._service = BatchConversionService(FFmpegConverter(), max_workers=2)
        self._events: Queue[ConversionEvent] = Queue()
        self._sources: list[Path] = []
        self._row_ids: dict[Path, str] = {}
        self._is_converting = False
        self._completed_count = 0
        self._total_count = 0
        self._outcome_counts = {
            JobStatus.SUCCEEDED: 0,
            JobStatus.FAILED: 0,
            JobStatus.SKIPPED: 0,
        }

        self._build_interface()
        self._root.protocol("WM_DELETE_WINDOW", self._close)
        self._root.after(100, self._process_events)

    def _build_interface(self) -> None:
        container = ttk.Frame(self._root, padding=16)
        container.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            container,
            text="Conversor de GIF para MP4",
            font=("Segoe UI", 18, "bold"),
        ).pack(anchor=tk.W)
        ttk.Label(
            container,
            text="Adicione vários GIFs, escolha a pasta de destino e converta em lote.",
        ).pack(anchor=tk.W, pady=(2, 14))

        controls = ttk.Frame(container)
        controls.pack(fill=tk.X, pady=(0, 8))
        self._add_button = ttk.Button(
            controls, text="Adicionar GIFs...", command=self._select_sources
        )
        self._add_button.pack(side=tk.LEFT)
        self._remove_button = ttk.Button(
            controls, text="Remover selecionados", command=self._remove_selected
        )
        self._remove_button.pack(side=tk.LEFT, padx=(8, 0))
        self._clear_button = ttk.Button(
            controls, text="Limpar lista", command=self._clear_sources
        )
        self._clear_button.pack(side=tk.LEFT, padx=(8, 0))

        table_frame = ttk.Frame(container)
        table_frame.pack(fill=tk.BOTH, expand=True)
        self._table = ttk.Treeview(
            table_frame,
            columns=("file", "status", "detail"),
            show="headings",
            selectmode="extended",
        )
        self._table.heading("file", text="Arquivo")
        self._table.heading("status", text="Status")
        self._table.heading("detail", text="Detalhes")
        self._table.column("file", width=380, anchor=tk.W)
        self._table.column("status", width=110, anchor=tk.W)
        self._table.column("detail", width=330, anchor=tk.W)
        scrollbar = ttk.Scrollbar(
            table_frame, orient=tk.VERTICAL, command=self._table.yview
        )
        self._table.configure(yscrollcommand=scrollbar.set)
        self._table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        destination_frame = ttk.Frame(container)
        destination_frame.pack(fill=tk.X, pady=(12, 8))
        ttk.Label(destination_frame, text="Pasta de saída:").pack(side=tk.LEFT)
        self._destination = tk.StringVar()
        self._destination_entry = ttk.Entry(
            destination_frame, textvariable=self._destination, state="readonly"
        )
        self._destination_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
        self._destination_button = ttk.Button(
            destination_frame,
            text="Escolher...",
            command=self._select_destination,
        )
        self._destination_button.pack(side=tk.LEFT)

        footer = ttk.Frame(container)
        footer.pack(fill=tk.X, pady=(4, 0))
        self._overwrite = tk.BooleanVar(value=False)
        self._overwrite_check = ttk.Checkbutton(
            footer,
            text="Sobrescrever arquivos MP4 existentes",
            variable=self._overwrite,
        )
        self._overwrite_check.pack(side=tk.LEFT)
        self._convert_button = ttk.Button(
            footer,
            text="Converter",
            command=self._start_conversion,
        )
        self._convert_button.pack(side=tk.RIGHT)

        self._progress = ttk.Progressbar(container, mode="determinate", maximum=1)
        self._progress.pack(fill=tk.X, pady=(12, 4))
        self._status_text = tk.StringVar(value="Pronto.")
        ttk.Label(container, textvariable=self._status_text).pack(anchor=tk.W)

    def _select_sources(self) -> None:
        selected = filedialog.askopenfilenames(
            title="Selecione um ou mais arquivos GIF",
            filetypes=[("GIF", "*.gif"), ("Todos os arquivos", "*.*")],
        )
        known = {str(source).casefold() for source in self._sources}
        for filename in selected:
            source = Path(filename)
            normalized = str(source).casefold()
            if normalized not in known:
                self._sources.append(source)
                known.add(normalized)
                row_id = self._table.insert(
                    "", tk.END, values=(source.name, JobStatus.PENDING.value)
                )
                self._row_ids[source] = row_id
        self._status_text.set(f"{len(self._sources)} arquivo(s) na lista.")

    def _select_destination(self) -> None:
        selected = filedialog.askdirectory(title="Escolha a pasta de saída")
        if selected:
            self._destination.set(selected)

    def _remove_selected(self) -> None:
        selected_rows = set(self._table.selection())
        if not selected_rows:
            return
        self._sources = [
            source
            for source in self._sources
            if self._row_ids[source] not in selected_rows
        ]
        for row_id in selected_rows:
            self._table.delete(row_id)
        self._row_ids = {
            source: row_id
            for source, row_id in self._row_ids.items()
            if row_id not in selected_rows
        }
        self._status_text.set(f"{len(self._sources)} arquivo(s) na lista.")

    def _clear_sources(self) -> None:
        if self._is_converting:
            return
        self._sources.clear()
        self._row_ids.clear()
        self._table.delete(*self._table.get_children())
        self._progress.configure(value=0, maximum=1)
        self._status_text.set("Lista limpa.")

    def _start_conversion(self) -> None:
        if not self._sources:
            messagebox.showinfo("Nenhum GIF", "Adicione pelo menos um arquivo GIF.")
            return
        destination_text = self._destination.get()
        if not destination_text:
            messagebox.showinfo("Pasta de saída", "Escolha uma pasta de saída.")
            return

        jobs = create_jobs(self._sources, Path(destination_text))
        self._is_converting = True
        self._completed_count = 0
        self._total_count = len(jobs)
        self._outcome_counts = {
            JobStatus.SUCCEEDED: 0,
            JobStatus.FAILED: 0,
            JobStatus.SKIPPED: 0,
        }
        self._progress.configure(maximum=self._total_count, value=0)
        self._status_text.set(f"Convertendo 0 de {self._total_count} arquivo(s)...")
        self._set_controls_enabled(False)
        self._service.submit(jobs, self._overwrite.get(), self._events)

    def _process_events(self) -> None:
        while True:
            try:
                event = self._events.get_nowait()
            except Empty:
                break

            row_id = self._row_ids.get(event.source)
            if row_id is not None:
                self._table.set(row_id, "status", event.status.value)
                self._table.set(row_id, "detail", event.message)
            if event.status in (
                JobStatus.SUCCEEDED,
                JobStatus.FAILED,
                JobStatus.SKIPPED,
            ):
                self._completed_count += 1
                self._outcome_counts[event.status] += 1
                self._progress.configure(value=self._completed_count)
                self._status_text.set(
                    f"{self._completed_count} de {self._total_count} arquivo(s) "
                    f"processado(s). {event.message}"
                )

        if self._is_converting and self._completed_count == self._total_count:
            self._is_converting = False
            self._set_controls_enabled(True)
            self._status_text.set(
                f"Concluído: {self._outcome_counts[JobStatus.SUCCEEDED]} convertido(s), "
                f"{self._outcome_counts[JobStatus.SKIPPED]} ignorado(s), "
                f"{self._outcome_counts[JobStatus.FAILED]} com falha."
            )

        self._root.after(100, self._process_events)

    def _set_controls_enabled(self, enabled: bool) -> None:
        state = tk.NORMAL if enabled else tk.DISABLED
        for widget in (
            self._add_button,
            self._remove_button,
            self._clear_button,
            self._destination_button,
            self._overwrite_check,
            self._convert_button,
        ):
            widget.configure(state=state)

    def _close(self) -> None:
        self._service.shutdown()
        self._root.destroy()
