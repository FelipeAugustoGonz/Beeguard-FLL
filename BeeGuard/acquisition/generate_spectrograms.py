"""Gera um PNG de espectrograma para cada WAV válido em recordings/."""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.io import wavfile
from scipy.signal import spectrogram

INPUT_FOLDER = Path("recordings")
OUTPUT_FOLDER = Path("spectrograms")


def main():
    files = sorted(INPUT_FOLDER.glob("*.wav"))
    if not files:
        print(f"Nenhum WAV encontrado em {INPUT_FOLDER.resolve()}")
        return

    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    for path in files:
        try:
            rate, audio = wavfile.read(path)
            if audio.ndim != 1 or audio.dtype != np.int16:
                raise ValueError("esperado WAV PCM 16-bit mono")
            if rate != 16000:
                raise ValueError(f"sample rate inesperado: {rate} Hz")
            if not audio.size:
                raise ValueError("arquivo sem samples")

            audio = audio.astype(np.float32) / 32768.0
            freq, times, power = spectrogram(
                audio, fs=rate, window="hann", nperseg=512,
                noverlap=384, scaling="spectrum", mode="psd"
            )
            db = 10 * np.log10(np.maximum(power, 1e-12))
            output = OUTPUT_FOLDER / f"{path.stem}_spectrogram.png"

            fig, ax = plt.subplots(figsize=(10, 5))
            plot = ax.pcolormesh(times, freq, db, shading="auto", cmap="magma")
            ax.set(title=path.name, xlabel="Tempo (s)", ylabel="Frequência (Hz)")
            fig.colorbar(plot, ax=ax, label="Potência (dB)")
            fig.tight_layout()
            fig.savefig(output, dpi=150)
            plt.close(fig)
            print(f"OK: {path} -> {output}")
        except (OSError, ValueError) as exc:
            print(f"ERRO: {path}: {exc}")


if __name__ == "__main__":
    main()
