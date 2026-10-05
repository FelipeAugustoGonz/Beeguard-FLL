"""Recebe frames BeeGuard (BGAR + versão + uint32 samples + PCM16 + BEND)."""
import struct
import time
import wave
from pathlib import Path

import serial
from serial import SerialException

# Troque COM3 pela porta indicada no Arduino IDE (por exemplo COM4 ou COM5).
SERIAL_PORT = "COM13"
BAUD_RATE = 921600
OUTPUT_FOLDER = Path("recordings")
SAMPLE_RATE = 16000
MAGIC = b"BGAR\x01"
END = b"BEND"


def read_exact(port, size):
    data = bytearray()
    while len(data) < size:
        part = port.read(size - len(data))
        if not part:
            raise TimeoutError("ESP32 desconectado ou transmissão incompleta")
        data.extend(part)
    return bytes(data)


def wait_header(port):
    matched = 0
    while True:
        b = port.read(1)
        if not b:
            continue
        matched = matched + 1 if b[0] == MAGIC[matched] else int(b[0] == MAGIC[0])
        if matched == len(MAGIC):
            return struct.unpack("<I", read_exact(port, 4))[0]


def next_name():
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    i = 1
    while (OUTPUT_FOLDER / f"recording_{i:03}.wav").exists():
        i += 1
    return OUTPUT_FOLDER / f"recording_{i:03}.wav"


def main():
    print("====================================\n🐝 BeeGuard AI Audio Recorder\n====================================")
    print(f"Porta: {SERIAL_PORT}\nSample rate: {SAMPLE_RATE} Hz\nFormato: PCM 16-bit mono\n")
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    try:
        with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2) as port:
            time.sleep(2)  # Aguarda reinício comum das placas ao abrir a serial.
            print("Aguardando ESP32...")
            while True:
                count = wait_header(port)
                if not 0 < count <= SAMPLE_RATE * 60:
                    print(f"Frame ignorado: quantidade inesperada de samples ({count}).")
                    continue
                print(f"\nGravação recebida...\nDuração: {count / SAMPLE_RATE:.2f} segundos\nSamples: {count}")
                pcm = read_exact(port, count * 2)
                if read_exact(port, len(END)) != END:
                    print("Transmissão corrompida; gravação descartada.")
                    continue
                path = next_name()
                with wave.open(str(path), "wb") as wav:
                    wav.setnchannels(1)
                    wav.setsampwidth(2)
                    wav.setframerate(SAMPLE_RATE)
                    wav.writeframes(pcm)
                samples = (value[0] for value in struct.iter_unpack("<h", pcm))
                low = high = next(samples)
                for value in samples:
                    low, high = min(low, value), max(high, value)
                print(f"✓ Áudio recebido\n✓ WAV salvo\nArquivo: {path}")
                print(f"Verificação: {SAMPLE_RATE} Hz, mono, {count} samples, {count / SAMPLE_RATE:.2f} s, amplitude [{low}, {high}]")
                print("\nAguardando próxima gravação...")
    except KeyboardInterrupt:
        print("\nColetor encerrado pelo usuário.")
    except (SerialException, OSError) as exc:
        print(f"Erro de porta serial ({SERIAL_PORT}): {exc}")
    except TimeoutError as exc:
        print(f"Erro: {exc}. Nenhum WAV incompleto foi salvo.")


if __name__ == "__main__":
    main()
