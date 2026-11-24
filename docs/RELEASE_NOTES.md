Cambios posteriores a 1.6.8 (sin versión publicada): modos manuales Normal,
Gaming y No molestar en Sistema y menú de bandeja. Los perfiles aplican un
overlay en tiempo de ejecución y conservan todas las preferencias existentes.
Gaming reduce renderizado y presencia visual sin desactivar voz configurada.
No molestar también silencia respuesta automática y pausa escucha continua;
los controles manuales siguen disponibles. No hay detección automática de
juegos ni alertas críticas todavía. Pruebas de contrato y de audio cubren
restauración y silencio; falta observar consumo real con un juego abierto.

`/memoria preparar PROYECTO | CONSULTA` muestra hasta tres recuerdos confirmados y públicos. `/memoria enviar` exige aprobación explícita y consume esa vista previa una vez; no la duplica en Core. Una desconexión invalida la preparación. Contratos WebSocket automatizados cubren el flujo; falta prueba con OpenClaw real.

Al caer el Gateway,
Desktop Pet retira la respuesta local pendiente antes de reconectar. Los eventos
tardíos de esa respuesta no se muestran ni se guardan en Karen Core, y no
liberan una respuesta nueva. Un contrato WebSocket local prueba la secuencia;
falta validarla con una caída real de OpenClaw.

Karen Desktop Pet 1.6.8 starts manual dictation even if OpenClaw cannot confirm
that it stopped an earlier reply. A failed abort no longer leaves the local
conversation marked busy. Manual recording and speech playback keep continuous
listening paused until they finish, avoiding a competing microphone reopen.
The installed STT, live Gateway response, neural synthesis and native capture
were checked separately; a real spoken command still depends on the selected
Windows microphone and its input level.
Transient microphone opening failures retry twice. A disconnected track during
manual dictation discards partial audio and shows an error. A cancelled older
transcription cannot clear the processing state of a newer response. These paths
have automated regression tests; physical disconnection remains to validate.
Late OpenClaw events and send acknowledgements from a locally cancelled run no
longer release or replace a newer run. Contract tests cover both event orders.
Histories and model changes now check the connection generation before applying
results, so an old Gateway cannot populate a new session or receive its patch.
An opt-in Karen Core SQLite v1 bridge can write final OpenClaw turns to Karen
classic's conversation archive. Set KAREN_CORE_DB to its existing absolute path;
see docs/KAREN_CORE.md. This is local, one-way continuity only.

Karen Desktop Pet 1.6.7 recovers wake listening after one or two transient
recognition failures instead of disabling it at the first error. A persistent
failure still stops listening and offers a manual retry. Recognition now
distinguishes missing dependencies, model load failure, invalid audio and
processing failure without recording audio or exception text. The pet strips
Electron's remote-method wrapper from error messages and can expand the lower
error strip to show the full message. Synthetic installed STT and wake recovery
tests verify these paths; the intermittent user microphone failure has not
been reproduced with the synthetic audio fixture.

Karen Desktop Pet 1.6.6 keeps Karen's face visible while showing replies.
The reply appears as a single-line strip below the character; pressing it
opens the full conversation. Error notices use the same lower area, and the
voice/listening indicator becomes compact at small pet sizes. Native layout
checks cover 50%, 100% and 200% scale during voice preparation and playback.

Karen Desktop Pet 1.6.5 adds Lucero and Flor while keeping the three existing
looks. All five now have visible hands and legs, and Karen lifts the hand on
the side of a desktop pointing target. The gesture ends with the marker and
respects reduced motion. Local speech recognition now names the exact missing
runtime, model or app worker path instead of reporting every path failure as
missing resources. The installed 1.6.4 build successfully transcribed a
synthetic sentence with the user's configured local resources; the intermittent
failure in the screenshot was not reproduced by that test.

Karen Desktop Pet 1.6.4 adds a temporary desktop pointing gesture. In
Percepción, choose a screen and review a screenshot, then tap the preview to
mark a point locally or explicitly ask Karen to locate an object in it. Voice
commands such as “Karen, señala el video en mi pantalla” use a recently
reviewed screen and take a fresh screenshot for the configured vision model.
The marker lasts eight seconds, lets mouse clicks through, and never clicks
another app. Karen only points when the model returns a valid location.
Edge neural speech now retries once after a transient synthesis failure and
allows more time for long replies; text remains available if both attempts fail.

Karen Desktop Pet 1.6.3 makes speech gestures follow real output audio energy.
The body leans and rises, fins respond, and the arms alternate on audio peaks
instead of repeating a fixed loop. Gestures decay between peaks and
stop as soon as speech stops. Reduced-motion and disabled-animation settings
still suppress body movement while keeping readable lip motion. Voice synthesis,
timing and profile remain unchanged.

Karen Desktop Pet 1.6.2 shows Karen's selected expression while her voice is
being prepared, instead of hiding it behind a neutral thinking face until audio
starts. Body and halo color ease into an emotional state and retarget smoothly
when interrupted; reduced-motion mode keeps the face readable with a faster
color change. Quoted Markdown lines and inline code no longer select Karen's
emotion, so a quoted user complaint does not make her look angry. The existing
single-clip voice playback and voice profile remain unchanged.

Karen Desktop Pet 1.6.1 adds six contextual expressions: laughter, anger,
sadness, surprise, pride and curiosity. The character changes eyes, brows,
mouth, fins, arms, tint and movement while preserving real audio lip motion.
Reply text selects a brief expression; technical states still reflect actual
listening, thinking, speaking and errors. Reduced-motion preferences remove
large movements while retaining readable facial expressions. The shared Karen
personality now permits situational humor, disagreement and expressive language
without claiming literal human feelings or attributing private emotions to the
user. No voice model, reference audio or credentials change.

Karen Desktop Pet 1.5.3 adds an explicit fast CPU voice using optional local
Kokoro resources. It uses another fixed timbre and does not replace the original
shared voice or change WhatsApp. A persistent worker avoids reloading between
phrases; delivery presets and real audio animation remain available.

Karen Desktop Pet 1.5.2 reduces the first audio wait with a shorter opening
phrase, one phrase of synthesis ahead of playback, and authenticated preparation
of the original voice while listening to a command or waiting for its reply.
Preparation retains the model for up to ten idle minutes and is skipped when
speech is muted or low-power mode is enabled. No voice identity is replaced.

The voice status and reply bubble now share a vertical layout instead of
overlapping absolute positions. Replies remain visible throughout preparation
and playback. Native tests cover the layout at 50%, 100% and 200% size.

Karen Desktop Pet 1.5.1 fixes Stop silently disabling addressed-name activation.
Stopping a response or capture preserves the user's listening preference.
An idle indicator now shows paused listening, offers an activation button and
keeps microphone errors visible with a retry control. Say only "Karen";
recognition also accepts the spelling "Caren". No slash is pronounced.

Karen Desktop Pet 1.5.0 adds offline addressed-name activation for Karen/Caren,
with explicit continuous-listening controls and a visible microphone indicator.
It preserves a command after the name and opens a ten-second command window
after the name alone. Listening closes during playback, manual recording and
PC-audio capture. Recognition uses one warm CPU worker with bounded input and
idle shutdown; launch errors now identify missing resources and safe error codes.
Native voice processes explicitly start in the configured resource directory.

Six delivery styles preserve the original pinned identity: original, serene,
warm, serious, bright and gentle irony. These use restrained FFmpeg prosody
adjustments, not unsupported Qwen Base emotion instructions. Existing WhatsApp
notes retain neutral processing. The shared Python modules also support the
original Karen application's explicit personality and activation preferences.
No voice reference, credential or model is bundled or regenerated.

Karen Desktop Pet 1.4.2 adds quick voice controls on the pet. Toggle spoken
replies or replay the last completed reply without another Gateway/model request.
The microphone reflects recording state and is disabled until recognition is
configured. The toolbar remains available during capture/playback, and its hidden
state no longer intercepts clicks through transparent areas.
Capture and voice show elapsed time; a long local synthesis has a clear waiting
message. The compact layout stays readable at 50% size. A resize also redraws
the pet once when Windows has paused its background animation, preserving the
character without keeping a hidden render loop active.

Karen Desktop Pet 1.4.1 fixes automatic spoken replies that arrive before
transcription finishes or while an earlier reply is playing. Final replies wait
in a bounded queue and are read once. Stopping capture or disabling voice clears
the queue. Aborted and failed Gateway turns are not read as new replies.
Replies play in short phrases instead of waiting for the entire synthesis.
An explicit preparing-audio status remains visible while the original model
generates a phrase. This is sequential phrase playback, not streaming inference;
the local CUDA engine can still take tens of seconds or longer under load.
The mouth, antennae, glow and gentle body movement follow real audio energy,
with reduced-motion support. Late Gateway completion events no longer replace
the speaking animation. Voice diagnostics refresh when the resource folder
changes, report authentication errors and distinguish an idle service from
missing resources. No voice identity, model or credentials are changed.

Karen Desktop Pet 1.4 adds an optional shared original voice. The native pet,
Python desktop client and OpenClaw's local CLI TTS provider can use one fixed
reference and authenticated service. Profile IDs and reference hashes are
verified; failures do not silently substitute another voice. The native client
starts the service on demand and diagnostics report the selected profile.
See docs/SHARED_VOICE.md for operator-owned setup, CUDA requirements and limits.
No models, private voice references or credentials are included.
Startup with a saved custom accent also waits for Pixi initialization before
destroying its previous renderer, keeping the pet and settings visible.

Karen Desktop Pet 1.3 added a Perception panel: Windows WASAPI loopback recording,
offline speech transcription and reviewed screen/window snapshots sent through
OpenClaw's real image attachment protocol. System audio transcripts are reviewed
before sending. The included recognizer handles spoken words, not music or
general environmental sound understanding.

Voice settings now include a real playback test, a resource-folder picker and
microphone controls. Configure your own optional Python 3.11, faster-whisper
small model and PyAudioWPatch with scripts/setup-voice.ps1. No models or private
resources are bundled. Windows TTS uses installed system voices.

Capture has visible status and a stop control, a 60-second recording limit, and
stops on hide, lock, suspend or application exit. Screen images are previewed
before explicit submission; there is no automatic screen monitoring. OpenClaw
and its provider may retain submitted content. A vision-capable model is required.

Windows retains the native transparent pet and system voice. Node 24 and Docker
self-hosting support text and animations.

Credentials, personal profiles, recordings and models are not included. Bring
your own OpenClaw configuration. Server mode supports text and animations; TTS,
STT and Windows desktop controls are not available on a headless server.
Each operator supplies and pays for their own infrastructure and model providers.
There is no maintainer-hosted API or shared account included with the application.

The Windows installer is not Authenticode-signed. Verify SHA256SUMS.txt and use
only releases from this repository. A real OpenClaw deployment still requires
your own Gateway authentication and device pairing when required.
