"""Local cancellable audio pipeline; no recordings are written to disk."""
import asyncio
from collections import deque
import io
import math
from pathlib import Path
import re
import threading
import time

import numpy as np
from core_resources import ResourceBusy, microphone_guard
import sounddevice as sd

BASE = Path(__file__).resolve().parent
RATE = 16000
CHUNK = 1280


class WakeDetector:
    def __init__(self, path, threshold=0.5, confirmations=2):
        from openwakeword.model import Model
        path = Path(path)
        if not path.is_absolute():
            path = BASE / path
        if not path.is_file():
            raise FileNotFoundError(f"Modelo ONNX no encontrado: {path.name}")
        self.model = Model(wakeword_models=[str(path)], inference_framework="onnx")
        self.name = path.stem
        self.threshold = threshold
        self.confirmations = confirmations
        self.rearm()

    def rearm(self):
        # Flush stale feature context by feeding fresh input, without reset artifacts.
        self.warmup = 40
        self.hits = 0

    def predict(self, audio):
        score = float(self.model.predict(audio)[self.name])
        if self.warmup:
            self.warmup -= 1
            return False, score
        self.hits = self.hits + 1 if score >= self.threshold else 0
        return self.hits >= self.confirmations, score


def rms(audio):
    samples = audio.astype(np.float32) / 32768
    return float(np.sqrt(np.mean(samples * samples))) if samples.size else 0.0


def speech_is_local(config):
    return config.tts_engine in {'kokoro', 'qwen3'} or (BASE / 'voice-models/active-voice.json').is_file()


class SpeechPlayer:
    def __init__(self, turn=None):
        self.turn = turn
        self.cancelled = turn.audio_cancelled if turn else threading.Event()

    def stop(self):
        if self.turn:
            self.turn.interrupt(cancel_generation=False)
        else:
            self.cancelled.set()

    async def _synthesize(self, text, config):
        import edge_tts
        output = bytearray()
        communicate = edge_tts.Communicate(
            text, config.voice, rate=config.voice_rate, pitch=config.voice_pitch,
            connect_timeout=10, receive_timeout=20,
        )
        async for chunk in communicate.stream():
            if self.cancelled.is_set():
                return b""
            if chunk["type"] == "audio":
                output.extend(chunk["data"])
        return bytes(output)

    async def synthesize(self, text, config):
        task = asyncio.create_task(self._synthesize(text, config))
        started = time.monotonic()
        try:
            while not task.done():
                if self.cancelled.is_set():
                    task.cancel()
                    return b""
                if time.monotonic() - started > 45:
                    task.cancel()
                    raise TimeoutError("La sÃ­ntesis de voz superÃ³ 45 segundos")
                await asyncio.sleep(0.05)
            return await task
        finally:
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    def encode(self, text, config):
        from speech_text import spoken_text
        text = spoken_text(text)
        if (BASE / 'voice-models/active-voice.json').is_file() or config.tts_engine == 'qwen3':
            from expressive_voice import synthesize
            encoded = synthesize(text, self.cancelled, style=config.voice_style)
        elif config.tts_engine == 'kokoro':
            from voice_local import synthesize
            encoded = synthesize(text, config.local_voice, config.voice_rate, self.cancelled, config.local_pitch_semitones)
        else:
            try:
                encoded = asyncio.run(self.synthesize(text, config))
            except Exception:
                if self.cancelled.is_set():
                    return b''
                from voice_local import synthesize
                encoded = synthesize(text, config.local_voice, config.voice_rate, self.cancelled, config.local_pitch_semitones)
        return encoded

    def play_encoded(self, encoded, state):
        import soundfile as sf
        if not encoded or self.cancelled.is_set():
            return False
        audio, sample_rate = sf.read(io.BytesIO(encoded), dtype="float32", always_2d=True)
        state("Hablando")
        # Own the output stream; stop does not interfere with another application's audio.
        with sd.OutputStream(samplerate=sample_rate, channels=audio.shape[1], dtype="float32") as stream:
            for start in range(0, len(audio), 1024):
                if self.cancelled.is_set():
                    stream.abort()
                    return False
                stream.write(audio[start:start + 1024])
                if self.turn:
                    self.turn.audio_started()
        return not self.cancelled.is_set()

    def speak(self, text, config, state):
        state('Preparando voz')
        self.play_encoded(self.encode(text, config), state)

    def speak_parts(self, parts, config, state):
        """Prefetch the next sentence while the current one is playing."""
        import queue
        ready = queue.Queue(maxsize=2)
        def put(value):
            while not self.cancelled.is_set():
                try:
                    ready.put(value, timeout=.05)
                    return
                except queue.Full:
                    pass
        def produce():
            try:
                while not self.cancelled.is_set():
                    try:
                        text = parts.get(timeout=.05)
                    except queue.Empty:
                        continue
                    if text is None:
                        break
                    encoded = self.encode(text, config)
                    if self.turn and encoded:
                        self.turn.receipt(text, 'synthesized')
                    put((text, encoded))
            except Exception as exc:
                put(exc)
            finally:
                put(None)
        threading.Thread(target=produce, daemon=True).start()
        state('Preparando voz')
        while not self.cancelled.is_set():
            try:
                encoded = ready.get(timeout=.05)
            except queue.Empty:
                continue
            if isinstance(encoded, Exception):
                raise encoded
            if encoded is None:
                return
            text, audio = encoded
            if self.play_encoded(audio, state) and self.turn:
                self.turn.receipt(text, 'played')


class VoiceListener:
    def __init__(self, config, device, stop, busy, submit, state, log, device_changed=None):
        self.config, self.device = config, device
        self.stop, self.busy = stop, busy
        self.submit, self.state, self.log = submit, state, log
        self.device_changed = device_changed
        self.detector = None
        self.whisper = None

    def _refresh_default_device(self):
        """Follow the OS default after a PortAudio failure, never an explicit choice."""
        if getattr(self.config, 'input_device', None) is not None:
            return
        try:
            devices = sd.query_devices()
            index = int(sd.default.device[0])
            if 0 <= index < len(devices) and devices[index]['max_input_channels'] > 0:
                if index != self.device:
                    self.device = index
                    self.log('Micrófono predeterminado actualizado; reintentando la escucha.')
                    if self.device_changed:
                        self.device_changed(index, devices[index]['name'])
        except (sd.PortAudioError, ValueError, TypeError, IndexError, KeyError):
            pass

    def _record(self, stream, initial):
        chunks = list(initial)
        silence = 0
        heard = any(rms(chunk) >= self.config.rms_threshold for chunk in chunks)
        silence_limit = math.ceil(self.config.end_silence_seconds * RATE / CHUNK)
        for _ in range(int(self.config.command_seconds * RATE / CHUNK)):
            if self.stop.is_set() or self.busy.is_set():
                return None
            raw, overflow = stream.read(CHUNK)
            if overflow:
                self.log("La captura perdiÃ³ audio; comprueba el dispositivo.")
            audio = np.frombuffer(raw, dtype=np.int16).copy()
            chunks.append(audio)
            if rms(audio) >= self.config.rms_threshold:
                heard = True
                silence = 0
            else:
                silence += 1
            if heard and silence >= silence_limit:
                break
        return np.concatenate(chunks)

    def transcribe(self, audio):
        if self.stop.is_set() or not any(rms(audio[start:start + CHUNK]) >= self.config.rms_threshold for start in range(0, len(audio), CHUNK)):
            return ""
        if self.config.stt_engine in {'faster-small', 'faster-turbo'}:
            from voice_local import transcribe
            return transcribe(audio, self.stop, self.config.stt_engine)
        import whisper
        if self.whisper is None:
            # Do not download a model in the background without telling the user.
            cached = Path.home() / ".cache" / "whisper" / (self.config.whisper_model + ".pt")
            if not cached.is_file():
                raise FileNotFoundError(f"Whisper {self.config.whisper_model} no estÃ¡ descargado; elige tiny o base disponible")
            self.whisper = whisper.load_model(str(cached))
        result = self.whisper.transcribe(audio.astype(np.float32) / 32768, language="es", fp16=False)
        return result["text"].strip()

    def run(self):
        from karen_personality import wake_command
        transcript_wake = self.config.wake_word_enabled and self.config.wake_mode == 'transcript'
        armed_until = 0.0
        input_failures = 0
        stt_failures = 0
        if self.config.wake_word_enabled and not transcript_wake:
            self.state("Cargando activaciÃ³n")
            try:
                self.detector = WakeDetector(self.config.wake_model, self.config.wake_word_threshold, self.config.wake_confirmations)
            except Exception as exc:
                self.log(f"ONNX no disponible: {exc}. Cambia a modo manual y vuelve a activar el micrÃ³fono.")
                self.state("Error")
                return
        while not self.stop.is_set():
            if self.busy.is_set():
                self.stop.wait(0.08)
                continue
            if self.detector:
                self.detector.rearm()
            command_window = transcript_wake and time.monotonic() < armed_until
            self.state('Escuchando Karen/Caren' if transcript_wake and not command_window else 'Preparando escucha' if self.detector else 'Escuchando comando')
            recorded = None
            # Close microphone while transcribing, generating or speaking.
            try:
                with microphone_guard(), sd.RawInputStream(samplerate=RATE, blocksize=CHUNK, channels=1, dtype="int16", device=self.device) as stream:
                    history = deque(maxlen=10)
                    while not self.stop.is_set() and not self.busy.is_set():
                        raw, overflow = stream.read(CHUNK)
                        if overflow:
                            history.clear()
                            if self.detector:
                                self.detector.rearm()
                            continue
                        audio = np.frombuffer(raw, dtype=np.int16).copy()
                        history.append(audio)
                        warming = self.detector and self.detector.warmup == 1
                        triggered = self.detector.predict(audio)[0] if self.detector else rms(audio) >= self.config.rms_threshold
                        if warming and not self.busy.is_set():
                            self.state("Escuchando Karen")
                        if triggered:
                            self.state("Grabando comando")
                            recorded = self._record(stream, history)
                            break
                if input_failures and not self.stop.is_set():
                    self.log('Micrófono recuperado; la escucha vuelve a estar disponible.')
                input_failures = 0
            except ResourceBusy:
                self.state('Micrófono ocupado por otra interfaz')
                self.stop.wait(2)
                continue
            except sd.PortAudioError as exc:
                if self.stop.is_set():
                    return
                input_failures += 1
                self._refresh_default_device()
                if input_failures == 3:
                    self.log(f"Micrófono no disponible tras 3 intentos: {exc}. Reintentando cada 10 segundos como máximo.")
                    self.state("Error")
                elif input_failures < 3:
                    self.state("Recuperando micrófono")
                    self.log(f"Error de entrada de audio; reintento {input_failures + 1}: {exc}")
                self.stop.wait(min(10, input_failures))
                continue
            if recorded is None or self.stop.is_set() or self.busy.is_set():
                continue
            self.busy.set()
            self.state("Transcribiendo")
            try:
                text = self.transcribe(recorded)
                stt_failures = 0
                if self.stop.is_set():
                    self.busy.clear()
                    return
                if transcript_wake and not command_window:
                    command = wake_command(text)
                    if command is None:
                        self.busy.clear()
                        continue
                    if not command:
                        armed_until = time.monotonic() + 10
                        self.state('Escuchando comando')
                        self.busy.clear()
                        continue
                    text = command
                elif self.detector:
                    command = wake_command(text)
                    if command is not None:
                        text = command
                armed_until = 0.0
                if text:
                    self.log(f"Voz: {text}")
                    self.submit(text)
                else:
                    self.busy.clear()
            except FileNotFoundError:
                self.busy.clear()
                self.state('Error')
                self.log('Modelo de reconocimiento no disponible. Configura un modelo instalado y reactiva la escucha.')
                return
            except (OSError, TimeoutError, ValueError) as exc:
                self.busy.clear()
                stt_failures += 1
                self.state('Recuperando reconocimiento' if stt_failures < 3 else 'Error')
                self.log(f'La transcripción falló ({type(exc).__name__}); reintento {stt_failures}.')
                self.stop.wait(min(10, stt_failures))
                continue
            except Exception:
                self.busy.clear()
                raise
            # submit keeps busy set until generation and playback finish.
            while self.busy.is_set() and not self.stop.is_set():
                self.stop.wait(0.08)
            self.stop.wait(0.35)  # Let loudspeaker echoes settle before opening the input.
