import wave
import struct

# Parameters for the silent WAV file
samplerate = 44100  # samples per second
duration = 1        # seconds
n_samples = int(samplerate * duration)
n_channels = 1
sample_width = 2  # bytes per sample (16-bit)
comptype = "NONE"
compname = "not compressed"

# Create the WAV file
with wave.open("jules-scratch/verification/silent.wav", "w") as wav_file:
    wav_file.setparams((n_channels, sample_width, samplerate, n_samples, comptype, compname))
    # Write silent frames
    for _ in range(n_samples):
        wav_file.writeframes(struct.pack('h', 0))

print("Silent WAV file created at jules-scratch/verification/silent.wav")
