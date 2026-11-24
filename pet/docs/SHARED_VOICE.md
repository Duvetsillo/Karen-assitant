# One original Karen voice

## Neural online option

The explicit **Natural rápida · Dalia (en línea)** setting uses Microsoft's
Spanish Mexico neural voice through `edge-tts`. It sends reply text to that
speech service and returns MP3 to the pet. It does not change the original
shared voice or WhatsApp. If the service fails, the reply remains visible.

## Respuestas continuas

Una respuesta normal se sintetiza como una sola pieza. Solo se divide cuando supera
el límite de 4096 caracteres del motor. El botón de micrófono interrumpe la voz
y permite dictar otra orden de inmediato.

## 1.5.3: optional fast local voice

Select **Rápida local · Kokoro (otro timbre)** in Voice to prioritize latency.
This is a distinct fixed synthetic timbre, not a clone of the Qwen reference.
The original shared voice stays selectable and WhatsApp is unchanged. There is
no automatic fallback or silent migration between voices.

Bring your own `voice-runtime` Python environment with `kokoro-onnx` and
`soundfile`, `voice-models/kokoro-v1.0.onnx`, `voice-models/voices-v1.0.bin`, and
FFmpeg with Rubber Band for delivery presets. The application downloads none
of these. A CPU worker reuses the model and exits after two idle minutes.
No GPU, API key or external speech service is required. The same delivery
presets and real energy-driven mouth animation work with this option.

## 1.5.2: first audio and layout

The pet starts with a short natural phrase (at most 64 characters), then prepares
one following phrase during playback. The queue stays bounded and cancellation
aborts the pet's own synthesis request without cancelling a Gateway action.
Replies remain visible while their audio is preparing or playing. The status
and reply share a vertical column, including at 50% size.

With local speech enabled, microphone capture and message submission request
authenticated `/prepare` on Karen's own loopback voice service. It loads the
same pinned reference without synthesizing text, overlapping startup with the
user's command and the assistant's response. The model may remain in GPU memory
for ten minutes after preparation; idle inference consumes no generation CPU.
Low-power mode and muted speech skip preparation. Other voice clients retain
their settings. This extension is advertised through a health capability and
does not add or alter any OpenClaw endpoint.

This reduces time to the first phrase and some gaps between phrases. It is not
true audio streaming or an instantaneous TTS engine. New phrases still require
local inference; cold startup and cached repeats must be measured separately.
The stable FP32 path, CPU codec and original voice identity remain in use.

## 1.5: delivery styles and addressed-name activation

Voice settings now offer Original, Serene, Warm, Serious, Bright and Gentle irony.
Serene is the default delivery for the pet and the updated Karen Local client.
The same pinned speaker reference remains in use. The presets apply restrained
tempo, pitch and EQ adjustments with FFmpeg's formant-preserving Rubber Band
filter. They are prosody presets, not a claim of neural emotion instruction
support: Qwen Base does not expose that API. The words and contextual emotion
come from the existing assistant. WhatsApp requests default to neutral delivery,
so existing notes retain their prior processing and provider configuration.

The native client requests and verifies the selected style. An old service that
ignores it produces an update error, rather than pretending the style worked.
Health requests remain read-only; enabled local voice can start the service
when preparing a command or synthesizing an utterance.
The native process explicitly uses the resource directory as its working folder,
and recognition errors include a bounded launch error code without stderr logs.
Windows speech also works without an optional resource directory, using an
existing executable directory instead. Packaging reuses the installed Electron
distribution to avoid an extra archive extraction.

Enable local recognition and **Activar al decir Karen o Caren** to opt into a
continuously open microphone. This implementation uses offline transcription of
voice-activity-gated segments, not an uncalibrated ONNX wake model. Quiet windows
are discarded without inference. Only an addressed name at the start of a phrase
(optionally after Hola/Oye/Hey/OK) activates it. An unrelated mention such as
"el vídeo de Karen" does not. Both spellings are accepted. A command following
the name is retained; the name alone opens a ten-second command window. ASR can
mishear words, especially poor synthetic audio, noise or distant microphones;
this is not speaker authentication or guaranteed instantaneous wake detection.

An indicator shows when the pet is listening locally. Say only **Karen**;
**Caren** is an accepted spelling from recognition, not a second required word.
**Pausar escucha** closes the microphone; **Activar escucha** restores it.
**Detener** cancels the current response or capture while preserving the chosen
wake setting. A microphone error stays visible with a retry control. Input is
closed during the pet's playback, manual capture and PC-audio capture. Stale
capture callbacks cannot reopen a paused detector. Nothing before activation
is sent to OpenClaw or written to a recording file. Recognition keeps one CPU
model warm between utterances and releases the worker after two idle minutes.

## Original Karen application

The local Python application can consume `python/dialogue_style.py`,
`python/wake_word.py` and the same `shared_voice_client.synthesize(..., style=...)`.
The original installation updated in this session uses `karen_personality.py` as
its adapter. Its settings expose a mature, serene persona, delivery styles,
useful-suggestion and gentle-sarcasm switches, transcript/ONNX/manual activation,
and optional startup listening. These are explicit preferences; they do not infer
the user's private emotions. The Ollama client's existing system message carries
the personality preferences. The separate personalized remote API continues to
own its own persona. The pet still uses OpenClaw's existing conversation logic;
its delivery selector does not secretly rewrite Gateway instructions.

When running both clients, enable continuous listening in the interface you
intend to address. They are separate audio clients; no cross-process microphone
ownership or cross-client echo cancellation is claimed. Startup listening in
Karen Local remains optional. No Gateway restart, WhatsApp message or provider
reconfiguration is required for these features.

Karen Local, OpenClaw WhatsApp notes and the desktop pet can use one fixed,
original reference. Qwen VoiceDesign creates the identity once; Qwen Base
0.6B uses its speaker embedding for subsequent utterances. No human reference
is required. Every client uses the same authenticated loopback service.

The service checks the profile ID and reference SHA256 on both requests and
responses. It refuses a different identity instead of falling back to another
voice. Sampling settings are fixed in the profile. Different sentences have
different prosody; WhatsApp's Opus compression also changes the waveform.
"Same voice" means the same fixed identity, not identical bytes for every text.

## Resources belong to each operator

No model, reference audio, active profile or credential is bundled or published.
Each operator downloads the models and creates their own identity on their
own hardware. The service uses CUDA; the validated Windows path targets an
NVIDIA GPU with 6 GB VRAM. Available memory depends on other applications.
An unavailable GPU produces an error, never a different voice.

On Windows, install Python 3.11 and a compatible NVIDIA driver, then:

```powershell
.\scripts\setup-shared-voice.ps1 -VoiceDirectory D:\KarenVoice
& D:\KarenVoice\expressive-runtime\Scripts\python.exe .\python\design_voice.py --root D:\KarenVoice
# Listen to voice-models/karen-original-v1/reference.wav, then activate it:
& D:\KarenVoice\expressive-runtime\Scripts\python.exe .\python\design_voice.py --root D:\KarenVoice --activate
```

Generation can take several minutes and runs once. Existing profiles are never
silently regenerated. Preserve `voice-models/karen-original-v1/` and
`voice-models/active-voice.json` to retain the identity after reinstalling. The
local `.expressive-token` is a private, per-installation credential; never commit
or share it. Model weights are Apache-2.0 under their published model cards.

The default design asks for a mature adult voice in a medium-low register.
For an intentional revision, use a new `--profile` ID. Activation of a different
identity requires `--activate --replace-active --profile NEW-ID`; it preserves
the previous reference and a copy of its active pointer. Invalid activation
restores the old pointer. Reuse the new profile across all clients together.

In the pet, choose the same resource directory in Voice settings, select
"Voz original compartida de Karen", enable reading replies, and test playback.
The service starts on demand in a hidden process. Health checks do not start
inference. After two idle minutes it releases model GPU memory; a bounded RAM
cache can reuse recent audio. Text and audio are not written to logs or disk.
The pet's default remains Windows TTS until its operator chooses shared voice.

Version 1.4.1 keeps final replies that arrive during transcription or playback
in a bounded queue (eight pending replies), rather than dropping them. It reads
up to 4096 characters per reply in short phrases, omitting code blocks and URLs.
Each phrase finishes playback before the next one starts. The visible status
distinguishes preparing audio from speaking; the mouth, antennae, glow and body
react to actual playback energy. Stop, a new recording, or disabling voice clears
pending replies. An interrupted or failed Gateway turn is not spoken.
Diagnostics refresh when the selected folder changes; choose the resource folder
in Voice settings rather than setting an environment variable unnecessarily.

## Karen Local and WhatsApp

Python desktop clients can import `shared_voice_client.synthesize(root, text,
cancelled_event)` from this repository's `python/` directory. An active profile
is read from the resource root. All clients should use that same root.

For OpenClaw, use its documented `tts-local-cli` provider. FFmpeg must be
installed in the resource root or on PATH. This public adapter generates an
Ogg/Opus voice note without sending it:

```powershell
python .\python\voice_note.py --root D:\KarenVoice --text "Hola, soy Karen." --output .\karen.opus
```

Configure `tts.providers.tts-local-cli.command` with your Python executable and
`args` with your absolute `voice_note.py` path, `--root`, your resource directory,
`--output`, `{{OutputPath}}`. Omit the `{{Text}}` argument: OpenClaw then supplies
UTF-8 through stdin, keeping utterances out of process arguments.
Set `outputFormat` to `opus`.
Keep the desired existing `tts.auto` mode; `inbound` responds with audio after
inbound voice notes. This is not a live WhatsApp call.

To prevent a different provider from substituting its default voice, use a
persona with `provider: "tts-local-cli"`, `fallbackPolicy: "fail"`, and a single
`providers` binding `{ "tts-local-cli": {} }`. Select it through `tts.persona`
and account for any local `/tts persona` preference. Leave model overrides
disabled. Consult the installed OpenClaw schema before changing configuration;
no Gateway restart is required for these settings in the verified version.

The Python service can run on a CUDA Linux server; its client chooses
`expressive-runtime/bin/python` there. Install the equivalent pinned Python
dependencies and FFmpeg yourself. It binds only to loopback, not the LAN or
public internet. Browser/headless pet mode continues to support text and
animations; it does not expose desktop voice RPCs. A remote shared deployment
requires your own authenticated transport and remains outside this setup.

## Verification and limits

Run `npm test`, `python -m unittest discover -s tests -p test_voice_profile.py`,
and `npm run build`. Tests cover reference replacement, path traversal,
identity mismatch, authentication rejection and cancellation. These checks do
not prove model quality; real synthesis, decoding and transcription are also
required. `tts.convert` with `channel: "whatsapp"` can verify OpenClaw note
generation without sending a message.

Reference-code continuation on the tested Turing GPU produced invalid audio.
The supported runtime uses the fixed speaker embedding, FP32, eager attention
and a CPU audio codec. Keeping the codec off the GPU leaves VRAM for the pet
and other Windows applications. Do not switch conditioning or precision without repeating real
audio verification. There is no streaming inference yet; the client waits for
each generated phrase, and latency depends on text length and hardware.

Primary references: [Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS),
[OpenClaw personas](https://docs.openclaw.ai/tools/tts/personas), and
[OpenClaw TTS fields](https://docs.openclaw.ai/tools/tts/field-reference).
