"""Main-thread target selection with asynchronous, coalesced discovery."""
import tkinter as tk
from dataclasses import replace
from catalog import CatalogSource
from ha_control import CONFIG_PATH


class TargetControls:
    def source_from_fields(self):
        if getattr(self, 'core2', None):
            return CatalogSource(self.core2.models.endpoint, 'ollama', '')
        return CatalogSource(self.fields['server'].get().strip(), self.fields['backend'].get(), self.fields['api_key'].get().strip())

    def select_profile(self, event=None):
        from config import PROFILES
        values = PROFILES.get(self.profile.get())
        if not values:
            return
        for key, value in values.items():
            field = self.fields[key]
            field.configure(state='normal')
            field.delete(0, tk.END)
            field.insert(0, value)
        self.load_catalog()

    def schedule_catalog(self, event=None):
        self.catalog_token += 1
        self.catalog_ready = False
        self.send_button.configure(state='normal' if CONFIG_PATH.exists() else 'disabled')
        self.fields['model'].configure(state='disabled')
        self.catalog_status.configure(text='Nodo cambiado · consultando modelos…')
        if self.catalog_after:
            self.root.after_cancel(self.catalog_after)
        self.catalog_after = self.root.after(400, self.load_catalog)

    def load_catalog(self, force=False):
        if self.closed.is_set():
            return
        if self.catalog_after:
            self.root.after_cancel(self.catalog_after)
            self.catalog_after = None
        self.catalog_token += 1
        token, source = self.catalog_token, self.source_from_fields()
        self.catalog_ready = False
        self.send_button.configure(state='normal' if CONFIG_PATH.exists() else 'disabled')
        self.fields['model'].configure(state='disabled')
        self.catalog_status.configure(text='Consultando el nodo…')
        self.broker.request(source, lambda result: self.ui_queue.put((self.finish_catalog, (token, source, result))), force=force)

    def finish_catalog(self, token, source, result):
        if token != self.catalog_token or source.key != self.source_from_fields().key:
            return
        self.catalog_source, self.catalog_result = source, result
        self.catalog_ready = result.status == 'ready'
        names = [m['name'] for m in result.models]
        if getattr(self, 'core2', None):
            from karen_core2.models import local_model
            names = [name for name in names if local_model(name)]
        field = self.fields['model']
        current = field.get()
        field.configure(values=names, state='normal')
        preferred = current if self.profile.get() == 'cloud' else self.model_choices.get(source.preference_key, current)
        field.set(preferred if preferred in names else names[0] if names else '')
        field.configure(state='readonly' if result.selectable and names else 'disabled')
        self.catalog_status.configure(text=result.message)
        if self.catalog_ready:
            self.apply_target()
        else:
            self.active_target.configure(text='Selecciona un nodo disponible para conversar.')
        self.set_state(self.current_state)
        self.refresh_benchmark_controls()

    def apply_target(self):
        from karen_app import KarenClient
        source = self.source_from_fields()
        model = self.fields['model'].get() or self.config.model
        if source.backend == 'ollama':
            self.model_choices[source.preference_key] = model
        config = replace(self.config, server=source.server, backend=source.backend, api_key=source.api_key, model=model, model_choices=dict(self.model_choices))
        old = self.config
        self.config = config
        if (old.server, old.backend, old.model, old.api_key) != (config.server, config.backend, config.model, config.api_key):
            self.client = KarenClient(config.server, config.api_key, config.model, config.backend, config.request_timeout, self.client.session_id)
            if getattr(self, 'core2', None):
                self.client.core2 = self.core2
            self.bind_conversation()
            self.last_failed_prompt = None
            self.retry_button.configure(state='disabled')
        remote = '\nCloud · las preguntas se envían a Ollama Cloud' if model.endswith('-cloud') and source.backend == 'ollama' else ''
        self.active_target.configure(text=f'Próxima respuesta\n{model if source.backend == "ollama" else "Personalidad Karen · modelo del servidor"}{remote}')

    def ensure_target(self):
        if self.catalog_source is None or self.source_from_fields().key != self.catalog_source.key:
            self.load_catalog()
            return False
        if not self.catalog_ready:
            return False
        if self.catalog_result.selectable and self.fields['model'].get() not in [m['name'] for m in self.catalog_result.models]:
            return False
        self.apply_target()
        return True

    def select_model(self, event=None):
        self.ensure_target()
        self.refresh_benchmark_controls()

    def test_api(self):
        self.load_catalog(force=True)
