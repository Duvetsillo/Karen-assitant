"""Optional Tkinter planning panel inside the existing Karen window."""
import json
import threading
import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox
import webbrowser


class CorePanel(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg='#FFFFFF', padx=6, pady=10)
        self.app, self.runtime = app, app.core2
        self.identity = None
        self.worker = None
        tk.Label(self, text='Plan y resultados', bg='#FFFFFF', fg='#173D32', font=('Segoe UI', 13, 'bold')).pack(anchor='w')
        tk.Label(self, text='Los pasos muestran decisiones y evidencia; no razonamiento interno del modelo.', bg='#FFFFFF', fg='#526C62', wraplength=285, justify='left').pack(fill='x', pady=(6, 10))
        self.goal = tk.Entry(self, font=('Segoe UI', 11))
        self.goal.insert(0, 'Diagnostica mi PC')
        self.goal.pack(fill='x', ipady=5)
        for text, command in [('Preparar plan', self.prepare), ('Ejecutar / reanudar', self.run),
                              ('Cancelar plan', self.cancel), ('Importar conocimiento', self.import_knowledge),
                              ('Ver documentos locales', self.list_knowledge)]:
            tk.Button(self, text=text, command=command, bg='#F1F6F3', fg='#146B55', relief='flat', font=('Segoe UI', 10)).pack(fill='x', pady=3)
        more = tk.Menubutton(self, text='Más acciones', bg='#F1F6F3', fg='#146B55', relief='flat',
                             font=('Segoe UI', 10), takefocus=True, direction='below')
        menu = tk.Menu(more, tearoff=False)
        for text, command in [('Recordar procedimiento verificado', self.remember),
                              ('Actualizar estado y memoria', self.refresh), ('Analizar ventana una vez', self.perceive),
                              ('Pausar percepción', lambda: self.runtime.vision.pause()),
                              ('Abrir interfaz Jarvis', lambda: webbrowser.open('http://127.0.0.1:18793/jarvis'))]:
            menu.add_command(label=text, command=command)
        more.configure(menu=menu)
        more.pack(fill='x', pady=3)
        self.output = scrolledtext.ScrolledText(self, wrap='word', height=16, font=('Segoe UI', 10), bg='#F1F6F3', fg='#173D32')
        self.output.pack(fill='both', expand=True, pady=10)
        self.output.insert('end', 'Core 2 local. Prepara un plan para revisar sus subtareas antes de ejecutarlas.\n')
        self.runtime.on_update = lambda plan: app.ui_queue.put((self.show, (plan,)))

    def show(self, value):
        if isinstance(value, dict) and 'steps' in value:
            self.identity = value['id']
            value = self.runtime.render(value)
        elif not isinstance(value, str):
            value = json.dumps(value, ensure_ascii=False, indent=2)
        self.output.delete('1.0', 'end')
        self.output.insert('end', value)

    def background(self, work):
        if self.worker and self.worker.is_alive():
            return
        def run():
            try:
                result = work()
            except Exception as exc:
                result = 'No se completó: ' + type(exc).__name__ + '. Revisa conexión, parámetros y permisos.'
            if not self.app.closed.is_set():
                self.app.ui_queue.put((self.show, (result,)))
        self.worker = threading.Thread(target=run, daemon=True)
        self.worker.start()

    def prepare(self):
        goal = self.goal.get().strip()
        if goal:
            self.background(lambda: self.runtime.create_plan(goal))

    def run(self):
        if self.identity:
            self.background(lambda: self.runtime.run(self.identity, resume=True))

    def cancel(self):
        if self.identity:
            # Cancellation must not wait behind the executing worker.
            threading.Thread(target=self.runtime.plans.cancel, args=(self.identity,), daemon=True).start()

    def remember(self):
        if self.identity:
            self.background(lambda: self.runtime.memory.record_procedure(self.runtime.plans.inspect(self.identity)))

    def refresh(self):
        self.background(lambda: {'core': self.runtime.status(), 'memories': self.runtime.memory.retrieve('Karen')})

    def list_knowledge(self):
        self.background(lambda: {'documents': self.runtime.knowledge.list('Karen'),
                                'help': 'Revisa con /conocimiento revisar ID. Autoriza contexto con /conocimiento aprobar ID. Elimina con /conocimiento eliminar ID.'})

    def import_knowledge(self):
        if self.worker and self.worker.is_alive():
            self.show('Espera a que termine la operación actual antes de importar un documento.')
            return
        filename = filedialog.askopenfilename(parent=self, title='Importar conocimiento local',
            filetypes=[('Documentos de texto', '*.txt *.md *.json *.csv *.html *.htm')])
        if not filename:
            return
        if not messagebox.askokcancel('Guardar documento local',
                'Se extraerá y guardará el contenido en la base local. No importes contraseñas ni credenciales. '
                'El documento no se usará en respuestas hasta que lo revises y apruebes. ¿Continuar?', parent=self):
            return
        sensitive = messagebox.askyesnocancel('Privacidad del documento',
                '¿Contiene información personal sensible? Sí autoriza guardarla como sensible; quedará excluida '
                'del contexto automático. Cancelar abandona la importación.', parent=self)
        if sensitive is None:
            return
        def work():
            result = self.runtime.knowledge.import_file('Karen', filename, sensitive=sensitive, allow_sensitive=sensitive)
            result['next_step'] = 'Revisa con /conocimiento revisar ' + result['id'] + '. Los documentos sensibles se gestionan con knowledge_cli.py --allow-sensitive.'
            return result
        self.background(work)

    def perceive(self):
        def capture():
            self.runtime.vision.pause(False)
            try:
                return self.runtime.vision.analyze()
            except Exception:
                self.runtime.vision.pause()
                raise
        self.background(capture)
