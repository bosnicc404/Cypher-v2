import asyncio, json, os, queue, subprocess, sys
import edge_tts
from pathlib import Path
import numpy as np, sounddevice as sd
from vosk import Model, KaldiRecognizer
from faster_whisper import WhisperModel

_whisper_model = WhisperModel("base", device="cpu")

# ---- config ----
WAKE_WORD = "cypher"
SAMPLE_RATE = 16000
VOSK_MODEL = "/home/bosnicc/code/ai/vosk-model-en-us-0.22"

# ---- TTS ----
async def speak(txt: str):
    tmp = "/tmp/tts.mp3"
    comm = edge_tts.Communicate(txt, voice="en-US-JennyNeural")
    with open(tmp, "wb") as f:
        async for ch in comm.stream():
            if ch["type"] == "audio": f.write(ch["data"])    
    subprocess.run(["ffplay", "-nodisp", "-autoexit", tmp], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# ---- wake-word detector ----
class WakeWord:
    def __init__(self, model_path=VOSK_MODEL, sr=SAMPLE_RATE):
        if not Path(model_path).exists(): raise FileNotFoundError
        self.rec = KaldiRecognizer(Model(model_path), sr)
        self.rec.SetWords(True)
        self.q = queue.Queue()
    def _cb(self, indata, frames, time, status):
        if status: print(f"[VAD] {status}", file=sys.stderr)
        self.q.put(bytes(indata))
    async def wait(self):
        with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=8000, dtype='int16', channels=1, callback=self._cb):
            print("[VAD] listening…")
            while True:
                data = await asyncio.get_event_loop().run_in_executor(None, self.q.get)
                if self.rec.AcceptWaveform(data):
                    r = json.loads(self.rec.Result())
                else:
                    r = json.loads(self.rec.PartialResult())
                if any(w in r.get("text", "").lower() or w in r.get("partial", "").lower()
                       for w in ["cypher", "cipher"]):
                    print(f"[VAD] '{WAKE_WORD}' detected!")
                    return

# ---- STT ----
def record_until_silence(sr=SAMPLE_RATE, silence_threshold=0.01, silence_duration=1.5):
    print("[STT] Listening for command...")
    audio_chunks = []
    silent_chunks = 0

    def callback(indata, frames, time, status):
        audio_chunks.append(indata.copy())

    with sd.InputStream(samplerate=sr, channels=1, dtype='float32', callback=callback):
        while True:
            sd.sleep(100)
            if len(audio_chunks) > 0:
                latest = audio_chunks[-1]
                if np.abs(latest).mean() < silence_threshold:
                    silent_chunks += 1
                else:
                    silent_chunks = 0
                if silent_chunks >= silence_duration * 10:
                    break

    return np.concatenate(audio_chunks).squeeze()

def transcribe(audio_np):
    segments, _ = _whisper_model.transcribe(audio_np, language='en')
    txt = " ".join([s.text for s in segments]).strip()
    print(f"[STT] Whisper says: {txt}")
    return txt