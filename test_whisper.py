import sounddevice as sd
from scipy.io.wavfile import write
import whisper

fs = 16000  # Sample rate (Hz)
seconds = 10  # Duration of recording (change as needed)

print("Recording... Please speak into your microphone.")
recording = sd.rec(int(seconds * fs), samplerate=fs, channels=1, dtype='int16')
sd.wait()  # Wait until recording is finished
write("output.wav", fs, recording)  # Save as WAV file
print("Recording finished and saved as output.wav.")

# Load Whisper model
print("Loading Whisper model...")
model = whisper.load_model("base")  # You can use "small", "medium", or "large" for more accuracy
print("Transcribing audio...")
result = model.transcribe("output.wav")
print("Transcribed text:")
print(result["text"])