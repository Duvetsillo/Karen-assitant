import threading
import uuid
import json
from pathlib import Path


class BenchmarkControls:
    def connect_benchmark(self):
        self.benchmark_status.configure(text='Conectando con Aetherion…')
        def worker():
            try:
                from aetherion_adapter import AetherionAdapter
                gateway = AetherionAdapter()
                data = gateway.nodes()
                self.ui_queue.put((self.finish_benchmark_connect, (gateway, data, None)))
            except Exception as exc:
                message = str(exc) if isinstance(exc, RuntimeError) else 'Inicia la API de integración de Aetherion para crear su credencial local.'
                self.ui_queue.put((self.finish_benchmark_connect, (None, {}, message)))
        threading.Thread(target=worker, daemon=True).start()

    def finish_benchmark_connect(self, gateway, data, error):
        self.benchmark_gateway = gateway
        self.benchmark_nodes = {n['id'] for n in data.get('nodes', [])}
        if data.get('categories'):
            self.benchmark_category.configure(values=data['categories'])
        self.benchmark_status.configure(text=error or 'Aetherion conectado · inicio manual')
        self.refresh_benchmark_controls()

    def benchmark_node(self):
        from urllib.parse import urlparse
        parsed = urlparse(self.config.server)
        if parsed.scheme != 'http' or parsed.port != 11434 or parsed.path not in {'', '/'}:
            return None
        host = parsed.hostname
        return 'pc' if host in {'localhost', '127.0.0.1'} else 'homelab' if host == '192.168.100.66' else None

    def refresh_benchmark_controls(self):
        self.benchmark_selection.configure(text=f'Modelo para iniciar\n{self.config.model}\n{self.config.server}')
        eligible = self.catalog_ready and self.config.backend == 'ollama' and not self.config.model.endswith('-cloud') and self.benchmark_gateway and self.benchmark_node() in self.benchmark_nodes and not self.benchmark_running
        self.benchmark_start.configure(state='normal' if eligible else 'disabled')

    def start_benchmark(self):
        if not self.ensure_target() or self.benchmark_running or not self.benchmark_gateway:
            return
        node = self.benchmark_node()
        if node not in self.benchmark_nodes or self.config.backend != 'ollama' or self.config.model.endswith('-cloud'):
            return
        try:
            seconds = int(self.benchmark_budget.get())
            if not 10 <= seconds <= 300:
                raise ValueError()
        except ValueError:
            self.benchmark_status.configure(text='Duración: usa un entero de 10 a 300 segundos.')
            return
        payload = dict(request_id=str(uuid.uuid4()), node=node, model=self.config.model, category=self.benchmark_category.get(), temperature=0.0, context=4096, max_seconds=seconds, confirm=True)
        self.benchmark_running = True
        self.benchmark_model = self.config.model
        self.benchmark_job = None
        self.refresh_benchmark_controls()
        gateway = self.benchmark_gateway
        self.benchmark_status.configure(text='Enviando inicio explícito…')
        def worker():
            try:
                snapshot = gateway.start(payload)
                job = snapshot['id']
                self.ui_queue.put((self.finish_benchmark_update, (snapshot, None)))
                while not self.closed.wait(1.5):
                    snapshot = gateway.poll(job)
                    terminal = snapshot['status'] in {'completed', 'stopped', 'failed'}
                    result = gateway.results(job) if terminal else None
                    self.ui_queue.put((self.finish_benchmark_update, (snapshot, result)))
                    if terminal:
                        return
            except Exception as exc:
                self.ui_queue.put((self.finish_benchmark_error, (str(exc),)))
        threading.Thread(target=worker, daemon=True).start()

    def finish_benchmark_error(self, message):
        self.benchmark_running = False
        self.benchmark_status.configure(text=message)
        self.benchmark_cancel.configure(state='normal' if self.benchmark_job else 'disabled')
        self.refresh_benchmark_controls()

    def finish_benchmark_update(self, snapshot, result):
        self.benchmark_job = snapshot['id']
        phase = snapshot['status']
        done, total = snapshot.get('completed', 0), snapshot.get('total', 0)
        self.benchmark_progress.configure(value=100 * done / total if total else 0)
        self.benchmark_status.configure(text=f'{snapshot.get("model", self.benchmark_model)}\n{phase} · {done}/{total} tareas')
        terminal = phase in {'completed', 'stopped', 'failed'}
        self.benchmark_running = not terminal
        self.benchmark_cancel.configure(state='disabled' if terminal else 'normal')
        if result is not None:
            directory = Path(__file__).resolve().parent / 'benchmark-results'
            directory.mkdir(exist_ok=True)
            destination = directory / (str(uuid.UUID(snapshot['id'])) + '.json')
            destination.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
            errors = sum(bool(item.get('error')) for item in result.get('results', []))
            self.benchmark_result.configure(text=f'{len(result.get("results", []))} resultados · {errors} con error\nHardware medido: PC de la API.\nJSON original: {destination.name}')
        self.refresh_benchmark_controls()

    def cancel_benchmark(self):
        if not self.benchmark_job or not self.benchmark_gateway:
            return
        gateway, job = self.benchmark_gateway, self.benchmark_job
        self.benchmark_status.configure(text='Solicitando cancelación…')
        def worker():
            try:
                snapshot = gateway.cancel(job)
                self.ui_queue.put((self.finish_benchmark_update, (snapshot, None)))
            except Exception as exc:
                self.ui_queue.put((self.finish_benchmark_error, (str(exc),)))
        threading.Thread(target=worker, daemon=True).start()
