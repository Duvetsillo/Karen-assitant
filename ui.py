"""Desktop controls for the existing KAREN visual language."""
import tkinter as tk
from tkinter import ttk, scrolledtext
from pathlib import Path

import sounddevice as sd
from config import PROFILES

BG = "#EAF1ED"
PANEL = "#FFFFFF"
INPUT = "#F1F6F3"
TEXT = "#173D32"
MUTED = "#526C62"
ACCENT = "#146B55"


def build_ui(app):
    root = app.root
    root.configure(bg=BG)
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("TNotebook", background=PANEL, borderwidth=0)
    style.configure("TNotebook.Tab", background=INPUT, foreground=TEXT, padding=(9, 12), font=("Segoe UI", 10, "bold"))
    style.map("TNotebook.Tab", background=[("selected", PANEL), ("active", "#DFEEE6")], foreground=[("selected", ACCENT)])
    style.configure("TCombobox", fieldbackground=INPUT, background=INPUT, foreground=TEXT, arrowcolor=TEXT, padding=5)
    style.map("TCombobox", fieldbackground=[("readonly", INPUT)], foreground=[("readonly", TEXT), ("disabled", MUTED)])
    root.option_add("*TCombobox*Listbox.background", INPUT)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)

    header = tk.Frame(root, bg=ACCENT, padx=28, pady=16)
    header.pack(fill="x")
    tk.Label(header, text="Karen", bg=ACCENT, fg="#FFFFFF", font=("Bahnschrift", 28, "bold")).pack(side="left")
    tk.Label(header, text="Un espacio para pensar en voz alta.", bg=ACCENT, fg="#E4F4EC", font=("Segoe UI", 12)).pack(side='left', padx=28)
    app.status_label = tk.Label(header, text="Lista", bg="#0D493A", fg="#FFFFFF", font=("Segoe UI", 11), anchor="e", padx=16, pady=10)
    app.status_label.pack(side="right", padx=(20, 0))

    footer = tk.Label(root, text="Escucha local Â· La captura se pausa durante el procesamiento y la voz", bg=BG, fg=MUTED, font=("Segoe UI", 10), anchor="w", padx=24, pady=10)
    footer.pack(side='bottom', fill='x')

    main = tk.Frame(root, bg=BG, padx=20, pady=4)
    main.pack(fill="both", expand=True)
    main.columnconfigure(1, weight=1)
    main.rowconfigure(0, weight=1)
    left = tk.Frame(main, bg=PANEL, padx=20, pady=20, width=360)
    left.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
    left.grid_propagate(False)
    left.rowconfigure(0, weight=1)
    left.columnconfigure(0, weight=1)
    tabs = ttk.Notebook(left)
    tabs.grid(row=0, column=0, sticky="nsew")
    connection = tk.Frame(tabs, bg=PANEL, padx=4, pady=12)
    audio = tk.Frame(tabs, bg=PANEL, padx=4, pady=12)
    benchmark = tk.Frame(tabs, bg=PANEL, padx=4, pady=12)
    tabs.add(connection, text="Modelo")
    tabs.add(audio, text="Audio")
    tabs.add(benchmark, text="Pruebas")
    administration = tk.Frame(tabs, bg=PANEL, padx=4, pady=12)
    tabs.add(administration, text='Admin')
    app.tabs = tabs
    if getattr(app, 'core2', None):
        from karen_core2.panel import CorePanel
        app.core2_panel = CorePanel(tabs, app)
        tabs.add(app.core2_panel, text='Core 2')
    audio_host = audio
    audio_canvas = tk.Canvas(audio_host, bg=PANEL, highlightthickness=0)
    audio_scroll = ttk.Scrollbar(audio_host, orient='vertical', command=audio_canvas.yview)
    audio_scroll.pack(side='right', fill='y')
    audio_canvas.pack(side='left', fill='both', expand=True)
    audio_canvas.configure(yscrollcommand=audio_scroll.set)
    audio = tk.Frame(audio_canvas, bg=PANEL)
    audio_window = audio_canvas.create_window((0, 0), window=audio, anchor='nw')
    audio.bind('<Configure>', lambda event: audio_canvas.configure(scrollregion=audio_canvas.bbox('all')))
    audio_canvas.bind('<Configure>', lambda event: audio_canvas.itemconfigure(audio_window, width=event.width))
    audio_canvas.bind('<MouseWheel>', lambda event: audio_canvas.yview_scroll(-int(event.delta / 120), 'units'))
    def scrollable(host):
        canvas = tk.Canvas(host, bg=PANEL, highlightthickness=0)
        scrollbar = ttk.Scrollbar(host, orient='vertical', command=canvas.yview)
        scrollbar.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        canvas.configure(yscrollcommand=scrollbar.set)
        inner = tk.Frame(canvas, bg=PANEL)
        window = canvas.create_window((0, 0), window=inner, anchor='nw')
        inner.bind('<Configure>', lambda event: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda event: canvas.itemconfigure(window, width=event.width))
        canvas.bind('<MouseWheel>', lambda event: canvas.yview_scroll(-int(event.delta / 120), 'units'))
        return inner
    connection = scrollable(connection)
    benchmark = scrollable(benchmark)
    administration = scrollable(administration)
    app.fields = {}

    def label(parent, text):
        tk.Label(parent, text=text, bg=PANEL, fg=MUTED, font=("Segoe UI", 10), anchor="w").pack(fill="x", pady=(6, 4))

    def field(parent, text, key, choices=None):
        label(parent, text)
        widget = ttk.Combobox(parent, values=choices, font=("Segoe UI", 10)) if choices is not None else tk.Entry(parent, bg=INPUT, fg=TEXT, insertbackground=TEXT, relief="flat", highlightthickness=1, highlightbackground="#9DB9AC", highlightcolor=ACCENT, font=("Segoe UI", 10))
        value = getattr(app.config, key, "")
        widget.insert(0, "" if value is None else str(value))
        if key == "api_key":
            widget.configure(show="*")
        widget.pack(fill="x", ipady=3)
        app.fields[key] = widget
        return widget

    def button(parent, text, command, primary=False):
        widget = tk.Button(parent, text=text, command=command, bg=ACCENT if primary else INPUT, fg=BG if primary else TEXT, activebackground="#0F5845" if primary else "#DFEEE6", activeforeground=BG if primary else TEXT, relief="flat", padx=12, pady=9, font=("Segoe UI", 10, "bold"), highlightthickness=1, highlightbackground="#9DB9AC", takefocus=True)
        widget.configure(cursor="hand2", highlightcolor=ACCENT, disabledforeground="#74857D")
        def hover(event):
            if str(widget['state']) != 'disabled':
                widget.configure(bg="#0F5845" if primary else "#DFEEE6")
        def leave(event):
            if str(widget['state']) != 'disabled':
                widget.configure(bg=ACCENT if primary else INPUT)
        widget.bind('<Enter>', hover)
        widget.bind('<Leave>', leave)
        return widget

    app.admin_enabled = tk.BooleanVar(value=True)
    tk.Checkbutton(administration, text='Agente de administración · Ollama', variable=app.admin_enabled,
                   bg=PANEL, fg=TEXT, selectcolor=INPUT, font=('Segoe UI', 10)).pack(anchor='w', pady=(6, 10))
    tk.Label(administration, text='Tareas habituales directas. Cambios críticos y scripts requieren aprobación. El agente necesita Ollama con herramientas.',
             bg=PANEL, fg=MUTED, wraplength=270, justify='left', font=('Segoe UI', 10)).pack(fill='x')
    tk.Label(administration, text='Los datos consultados se envían al modelo seleccionado.', bg=PANEL, fg=MUTED,
             wraplength=270, justify='left', font=('Segoe UI', 10)).pack(fill='x', pady=(6, 0))
    app.admin_scope = tk.Label(administration, bg=PANEL, fg=TEXT, wraplength=270, justify='left', font=('Segoe UI', 10))
    app.admin_scope.pack(fill='x', pady=(12, 8))
    app.refresh_admin_scope()
    for title, prompt in [('Procesos y consumo', '/admin Lista los procesos de mi PC y resume el consumo.'),
                          ('Servicios de Windows', '/admin Lista los servicios de Windows.'),
                          ('Aplicaciones instaladas', '/admin Lista las aplicaciones instaladas.'),
                          ('Conexiones de red', '/admin Revisa las conexiones de red de mi PC.')]:
        button(administration, title, lambda value=prompt: app.send_prompt(value)).pack(fill='x', pady=3)
    button(administration, 'Ver registro de operaciones', app.show_admin_audit).pack(fill='x', pady=(10, 3))
    button(administration, 'Reabrir con privilegios · UAC', app.request_admin_elevation).pack(fill='x', pady=3)
    label(administration, 'Gmail · lectura y borrado protegido')
    app.gmail_account = ttk.Combobox(administration, values=['dayvermoreta@gmail.com','dayvermoreta21@gmail.com'],state='readonly',font=('Segoe UI',10))
    app.gmail_account.set('dayvermoreta@gmail.com')
    app.gmail_account.pack(fill='x')
    button(administration,'Permitir mover correos a papelera · Google',app.authorize_gmail_trash).pack(fill='x',pady=5)
    label(administration, 'Autorizar otro destino')
    app.admin_target_kind = ttk.Combobox(administration, values=['Alias SSH', 'Subred IPv4'], state='readonly', font=('Segoe UI', 10))
    app.admin_target_kind.set('Alias SSH')
    app.admin_target_kind.pack(fill='x')
    label(administration, 'Alias o subred')
    app.admin_target_value = tk.Entry(administration, bg=INPUT, fg=TEXT, font=('Segoe UI', 10))
    app.admin_target_value.pack(fill='x', ipady=4, pady=(6, 4))
    tk.Label(administration, text='SSH: alias ya configurado. Red: CIDR privado, máximo /24. Descubrir un equipo no autoriza acceso a él.',
             bg=PANEL, fg=MUTED, wraplength=270, justify='left', font=('Segoe UI', 10)).pack(fill='x', pady=4)
    button(administration, 'Autorizar destino', app.authorize_admin_target).pack(fill='x', pady=4)

    label(connection, "Nodo")
    app.profile = ttk.Combobox(connection, values=list(PROFILES), state="readonly", font=("Segoe UI", 10))
    current = next((name for name, values in PROFILES.items() if (name != 'cloud' or app.config.model.endswith('-cloud')) and all(getattr(app.config, k) == v for k, v in values.items() if k != 'model')), "Personalizado")
    app.profile.set(current)
    app.profile.pack(fill="x")
    if getattr(app, 'core2', None):
        app.profile.configure(values=['pc'])
        app.profile.set('pc')
    app.profile.bind("<<ComboboxSelected>>", app.select_profile)
    field(connection, "Servidor", "server")
    field(connection, "API", "backend", ["ollama", "karen"])
    app.fields["backend"].configure(state="readonly")
    app.fields["backend"].bind("<<ComboboxSelected>>", app.schedule_catalog)
    app.fields["server"].bind("<KeyRelease>", app.schedule_catalog)
    app.fields["server"].bind("<FocusOut>", app.schedule_catalog)
    field(connection, "Modelo de este nodo", "model", [app.config.model])
    app.fields["model"].configure(state="disabled")
    app.fields["model"].bind("<<ComboboxSelected>>", app.select_model)
    app.catalog_status = tk.Label(connection, text="Cargando catÃ¡logoâ€¦", wraplength=290, justify="left", bg=PANEL, fg=MUTED, font=("Segoe UI", 10))
    app.catalog_status.pack(anchor="w", pady=(6, 0))
    app.active_target = tk.Label(connection, text="Esperando nodo/modelo", wraplength=290, justify="left", bg=PANEL, fg=TEXT, font=("Segoe UI", 10))
    app.active_target.pack(anchor="w", pady=(6, 0))
    field(connection, "API key Â· solo esta sesiÃ³n", "api_key")
    app.fields["api_key"].bind("<KeyRelease>", app.schedule_catalog)
    app.test_button = button(connection, "Refrescar catÃ¡logo / salud", app.test_api)
    app.test_button.pack(fill="x", pady=(18, 0))

    tk.Label(benchmark, text="Aetherion", bg=PANEL, fg=TEXT, font=("Segoe UI", 13, "bold"), anchor="w").pack(fill="x", pady=(8, 12))
    app.benchmark_selection = tk.Label(benchmark, text="Modelo pendiente", wraplength=290, justify="left", bg=PANEL, fg=MUTED, font=("Segoe UI", 10))
    app.benchmark_selection.pack(fill="x")
    app.benchmark_status = tk.Label(benchmark, text="API de integraciÃ³n pendiente de conexiÃ³n", wraplength=290, justify="left", bg=PANEL, fg=MUTED, font=("Segoe UI", 10))
    app.benchmark_status.pack(fill="x", pady=(16, 12))
    connect_button = button(benchmark, 'Conectar Aetherion', app.connect_benchmark)
    connect_button.pack(fill='x', pady=(0, 12))
    label(benchmark, 'CategorÃ­a de la prueba')
    app.benchmark_category = ttk.Combobox(benchmark, values=['general', 'coding', 'math', 'json', 'spanish'], state='readonly')
    app.benchmark_category.set('spanish')
    app.benchmark_category.pack(fill='x')
    label(benchmark, 'LÃ­mite de tiempo Â· segundos')
    app.benchmark_budget = tk.Entry(benchmark, bg=INPUT, fg=TEXT, insertbackground=TEXT, relief='flat', font=('Segoe UI', 11))
    app.benchmark_budget.insert(0, '60')
    app.benchmark_budget.pack(fill='x', ipady=5, pady=(0, 12))
    app.benchmark_progress = ttk.Progressbar(benchmark, maximum=100)
    app.benchmark_progress.pack(fill="x", pady=(0, 12))
    app.benchmark_start = button(benchmark, "Iniciar benchmark", app.start_benchmark)
    app.benchmark_start.configure(state="disabled")
    app.benchmark_start.pack(fill="x")
    app.benchmark_cancel = button(benchmark, "Cancelar benchmark", app.cancel_benchmark)
    app.benchmark_cancel.configure(state="disabled")
    app.benchmark_cancel.pack(fill="x", pady=(8, 12))
    app.benchmark_result = tk.Label(benchmark, text="Sin resultados. Elegir un modelo no inicia pruebas.", wraplength=290, justify="left", bg=PANEL, fg=MUTED, font=("Segoe UI", 10))
    app.benchmark_result.pack(fill="x")

    label(audio, "MicrÃ³fono")
    try:
        app.device_choices = {f"{i} Â· {d['name']}": i for i, d in enumerate(sd.query_devices()) if d["max_input_channels"] > 0}
    except sd.PortAudioError:
        app.device_choices = {}
    app.device_selector = ttk.Combobox(audio, state="readonly", values=["Predeterminado"] + list(app.device_choices), font=("Segoe UI", 10))
    app.device_selector.set(next((name for name, index in app.device_choices.items() if index == app.mic_index), "Predeterminado"))
    app.device_selector.pack(fill="x")
    label(audio, "ActivaciÃ³n")
    app.activation = ttk.Combobox(audio, state="readonly", values=["Karen/Caren: transcripcion local", "Karen: ONNX", "Manual: sin palabra clave"], font=("Segoe UI", 10))
    app.activation.set(("Karen/Caren: transcripcion local" if app.config.wake_mode == "transcript" else "Karen: ONNX") if app.config.wake_word_enabled else "Manual: sin palabra clave")
    app.activation.pack(fill="x")
    field(audio, "TranscripciÃ³n Whisper", "whisper_model", ["tiny", "base", "small", "medium", "large"])
    field(audio, 'Motor de reconocimiento', 'stt_engine', ['faster-turbo', 'faster-small', 'whisper'])
    fixed_voice = (Path(__file__).resolve().parent / 'voice-models/active-voice.json').is_file()
    field(audio, 'Voz original compartida' if fixed_voice else 'Motor de voz', 'tts_engine', ['qwen3'] if fixed_voice else ['qwen3', 'kokoro', 'edge'])
    field(audio, 'Voz local Kokoro', 'local_voice', ['ef_karen', 'ef_dora', 'em_alex', 'em_santa'])
    field(audio, "Voz Edge TTS", "voice", ["es-MX-DaliaNeural", "es-ES-ElviraNeural", "es-CO-SalomeNeural", "es-AR-ElenaNeural"])
    row = tk.Frame(audio, bg=PANEL)
    row.pack(fill="x")
    field(row, "Velocidad (ej. -1%)", "voice_rate")
    if fixed_voice:
        for key in ('tts_engine', 'local_voice', 'voice', 'voice_rate'):
            app.fields[key].configure(state='disabled')
    field(row, "Sensibilidad ONNX (0â€“1)", "wake_word_threshold")
    app.tts_enabled = tk.BooleanVar(value=app.config.tts_enabled)
    tk.Checkbutton(audio, text="Leer respuestas en voz alta", variable=app.tts_enabled, bg=PANEL, fg=TEXT, selectcolor=INPUT, activebackground=PANEL, activeforeground=TEXT, font=("Segoe UI", 10)).pack(anchor="w", pady=(12, 4))
    voice_note = "Voz original compartida con WhatsApp y el PET. El perfil fijo conserva el mismo timbre; los ajustes de otras voces no se aplican." if fixed_voice else "Edge TTS necesita internet. ONNX requiere un detector configurado."
    tk.Label(audio, text=voice_note, wraplength=290, justify="left", bg=PANEL, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w")
    from karen_personality import STYLE_LABELS
    app.voice_style_labels = STYLE_LABELS
    field(audio, 'Estilo de voz y personalidad', 'voice_style', list(STYLE_LABELS.values()))
    app.fields['voice_style'].set(STYLE_LABELS[app.config.voice_style])
    app.fields['voice_style'].configure(state='readonly')
    for key, text in [('allow_suggestions', 'Sugerencias utiles cuando aporten valor'), ('allow_sarcasm', 'Sarcasmo suave y ocasional'), ('wake_auto_start', 'Escuchar Karen/Caren al abrir la aplicacion')]:
        variable = tk.BooleanVar(value=getattr(app.config, key))
        setattr(app, key, variable)
        tk.Checkbutton(audio, text=text, variable=variable, bg=PANEL, fg=TEXT, selectcolor=INPUT, activebackground=PANEL, activeforeground=TEXT, font=('Segoe UI', 10)).pack(anchor='w', pady=3)
    tk.Label(audio, text='El estilo conserva la voz original. La escucha usa transcripcion local; solo las ordenes dirigidas a Karen/Caren se envian al asistente.', wraplength=290, justify='left', bg=PANEL, fg=MUTED, font=('Segoe UI', 10)).pack(anchor='w', pady=(4, 8))
    label(audio, 'Calendario y administraciÃ³n')
    button(audio, 'Vincular calendario iCloud', app.connect_icloud).pack(fill='x', pady=(6, 4))
    button(audio, 'Consultar estado del PC', lambda: app.send_prompt('Revisa el estado de mi PC')).pack(fill='x', pady=4)
    button(audio, 'Escanear mi red', lambda: app.send_prompt('Escanea mi red')).pack(fill='x', pady=4)
    button(audio, 'Reiniciar Gateway', app.restart_gateway).pack(fill='x', pady=4)

    bottom = tk.Frame(left, bg=PANEL)
    bottom.grid(row=1, column=0, sticky="ew", pady=(16, 0))
    app.save_button = button(bottom, "Guardar ajustes", app.save_config)
    app.save_button.pack(fill="x")
    app.mic_label = tk.Label(bottom, text="", bg=PANEL, fg=MUTED, wraplength=300, justify="left", font=("Segoe UI", 10))
    app.mic_label.pack(fill="x", pady=(12, 8))
    app.mic_button = button(bottom, "Activar micrÃ³fono", app.toggle_microphone, True)
    app.mic_button.pack(fill="x")

    right = tk.Frame(main, bg=PANEL, padx=18, pady=16)
    right.grid(row=0, column=1, sticky="nsew")
    right.rowconfigure(2, weight=1)
    right.columnconfigure(0, weight=1)
    toolbar = tk.Frame(right, bg=PANEL)
    toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 12))
    conversation_bar = tk.Frame(toolbar, bg=PANEL)
    conversation_bar.pack(side='bottom', fill='x', pady=(10, 0))
    app.conversation_selector = ttk.Combobox(conversation_bar, state='readonly', font=('Segoe UI', 10))
    app.conversation_selector.pack(side='left', fill='x', expand=True)
    app.conversation_selector.bind('<<ComboboxSelected>>', lambda event: app.change_conversation())
    button(conversation_bar, 'Nuevo chat', lambda: app.change_conversation(new=True)).pack(side='right', padx=(8, 0))
    tk.Label(toolbar, text="ConversaciÃ³n", bg=PANEL, fg=TEXT, font=("Segoe UI", 15, "bold")).pack(side="left")
    app.stop_voice_button = button(toolbar, "Detener voz", app.stop_voice)
    app.stop_voice_button.pack(side="right")
    app.stop_voice_button.configure(state="disabled")
    app.cancel_generation_button = button(toolbar, "Cancelar generación", app.cancel_generation)
    app.cancel_generation_button.pack(side="right", padx=(8, 0))
    app.cancel_generation_button.configure(state="disabled")
    app.cancel_task_button = button(toolbar, "Cancelar tarea", app.cancel_active_task)
    app.cancel_task_button.pack(side="right", padx=(8, 0))
    app.cancel_task_button.configure(state="disabled")
    app.retry_button = button(toolbar, "Reintentar", app.retry_last_prompt)
    app.retry_button.pack(side="right", padx=(8, 8))
    app.retry_button.configure(state="disabled")
    app.welcome = tk.Frame(right, bg="#E8F4ED", padx=24, pady=24)
    app.welcome.grid(row=1, column=0, sticky="ew", pady=(0, 18))
    tk.Label(app.welcome, text="Â¿QuÃ© tienes en mente?", bg="#E8F4ED", fg=TEXT, font=("Bahnschrift", 26, "bold"), anchor="w").pack(fill="x")
    tk.Label(app.welcome, text="Habla con Karen o escribe tu mensaje. TÃº eliges el modelo.", bg="#E8F4ED", fg=MUTED, font=("Segoe UI", 11), anchor="w").pack(fill="x", pady=(8, 18))
    suggestions = tk.Frame(app.welcome, bg="#E8F4ED")
    suggestions.pack(fill="x")
    def prepare_prompt(text):
        app.prompt.delete(0, tk.END)
        app.prompt.insert(0, text)
        app.prompt.focus_set()
    for title, prompt in [('Saludar', 'Hola, Karen.'), ('Ordenar una idea', 'AyÃºdame a ordenar una idea.'), ('Resolver una duda', 'Quiero resolver una duda.')]:
        chip = button(suggestions, title, lambda value=prompt: prepare_prompt(value))
        chip.pack(side="left", padx=(0, 8))
    app.chat = scrolledtext.ScrolledText(right, bg="#FFFFFF", fg=TEXT, insertbackground=TEXT, relief="flat", wrap="word", font=("Segoe UI", 13), padx=24, pady=24, width=45, state="disabled")
    app.chat.grid(row=2, column=0, sticky="nsew")
    app.chat.tag_configure("role", foreground=ACCENT, font=("Bahnschrift", 11, "bold"), spacing1=16, spacing3=8)
    app.chat.tag_configure("body", spacing3=18, lmargin1=4, lmargin2=4)
    app.chat.vbar.configure(background=INPUT, troughcolor=BG, activebackground=ACCENT)
    input_wrap = tk.Frame(right, bg=PANEL)
    input_wrap.grid(row=3, column=0, sticky="ew", pady=(14, 0))
    input_wrap.columnconfigure(0, weight=1)
    app.prompt = tk.Entry(input_wrap, bg=INPUT, fg=TEXT, insertbackground=TEXT, relief="flat", highlightthickness=1, highlightbackground="#9DB9AC", highlightcolor=ACCENT, font=("Segoe UI", 11))
    app.prompt.grid(row=1, column=0, sticky="ew", ipady=9)
    app.prompt.bind("<Return>", lambda event: app.send_prompt())
    tk.Label(input_wrap, text="Tu mensaje", bg=PANEL, fg=MUTED, anchor="w", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w", pady=(0, 6))
    app.send_button = button(input_wrap, "Enviar", app.send_prompt, True)
    app.send_button.grid(row=1, column=1, padx=(10, 0))
    app.stream_preview = tk.Label(input_wrap, text="", bg=PANEL, fg=TEXT,
                                  wraplength=680, justify="left", anchor="w", font=("Segoe UI", 10))
    app.stream_preview.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))
    app.stream_preview.grid_remove()

    def keep_focus_visible(event):
        widget = event.widget
        parent = widget
        while parent is not root and getattr(parent, 'master', None) is not None:
            if isinstance(parent.master, tk.Canvas):
                canvas, inner = parent.master, parent
                canvas.update_idletasks()
                top = widget.winfo_rooty() - inner.winfo_rooty()
                bottom = top + widget.winfo_height()
                visible_top = canvas.canvasy(0)
                height = canvas.winfo_height()
                total = max(inner.winfo_height(), 1)
                if top < visible_top:
                    canvas.yview_moveto(max(0, top / total))
                elif bottom > visible_top + height:
                    canvas.yview_moveto(max(0, (bottom - height + 8) / total))
                break
            parent = parent.master
    root.bind('<FocusIn>', keep_focus_visible, add='+')
    root.bind('<Control-l>', lambda event: app.prompt.focus_set())
