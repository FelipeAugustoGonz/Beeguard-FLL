"""BeeGuard V1: padronização e descritores; não realiza diagnóstico."""
import hashlib
import math
from pathlib import Path

import numpy as np
from scipy.fft import dct
from scipy.io import wavfile
from scipy.signal import resample_poly, stft

RATE = 16000
WINDOW = RATE * 10
VERSION = 'beeguard-features-1'


def load_audio(path):
    rate, raw = wavfile.read(path)
    if rate <= 0 or raw.size == 0 or raw.ndim not in (1, 2):
        raise ValueError('WAV vazio ou formato inválido')
    if raw.dtype.kind == 'u' and raw.dtype.itemsize == 1:
        audio = (raw.astype(np.float64) - 128) / 128
    elif raw.dtype.kind == 'i':
        audio = raw.astype(np.float64) / (2 ** (raw.dtype.itemsize * 8 - 1))
    elif raw.dtype.kind == 'f':
        audio = raw.astype(np.float64)
    else:
        raise ValueError(f'Tipo PCM não suportado: {raw.dtype}')
    if not np.isfinite(audio).all():
        raise ValueError('Samples NaN/Inf')
    # Medir clipping antes da média dos canais e da reamostragem.
    source_clipping = float(np.mean(np.abs(audio) >= 0.999))
    channels = 1 if audio.ndim == 1 else audio.shape[1]
    if audio.ndim == 2:
        audio = audio.mean(axis=1)
    if rate != RATE:
        divisor = math.gcd(rate, RATE)
        audio = resample_poly(audio, RATE // divisor, rate // divisor)
    return audio, {'original_rate': rate, 'original_channels': channels,
                   'source_clipping_ratio': source_clipping}


def quality(audio):
    rms = float(np.sqrt(np.mean(audio ** 2)))
    clipping = float(np.mean(np.abs(audio) >= 0.999))
    quiet = float(np.mean(np.abs(audio) < 1e-4))
    reasons = []
    if rms < 1e-4:
        reasons.append('volume_muito_baixo')
    if clipping > 0.01:
        reasons.append('clipping')
    return {'rms': rms, 'clipping_ratio': clipping, 'quiet_sample_ratio': quiet,
            'quality_status': 'review' if reasons else 'pass',
            'quality_reasons': ';'.join(reasons)}


def features(audio):
    if len(audio) != WINDOW:
        raise ValueError('Esperada janela de 10 s a 16000 Hz')
    _, _, z = stft(audio, RATE, nperseg=512, noverlap=256,
                   boundary=None, padded=False)
    power = np.abs(z) ** 2
    freq = np.fft.rfftfreq(512, 1 / RATE)
    total = np.maximum(power.sum(axis=0), 1e-20)
    probs = power / total
    centroid = (freq[:, None] * probs).sum(axis=0)
    spread = np.sqrt(((freq[:, None] - centroid) ** 2 * probs).sum(axis=0))
    entropy = -(probs * np.log(np.maximum(probs, 1e-20))).sum(axis=0) / np.log(len(freq))
    rolloff = freq[np.argmax(np.cumsum(probs, axis=0) >= 0.85, axis=0)]
    flatness = np.exp(np.log(np.maximum(power, 1e-20)).mean(axis=0)) / np.maximum(power.mean(axis=0), 1e-20)
    # 40 filtros Mel triangulares; MFCC 0..12, média e desvio temporal.
    mel = lambda hz: 2595 * np.log10(1 + hz / 700)
    hz = lambda m: 700 * (10 ** (m / 2595) - 1)
    edges = hz(np.linspace(mel(0), mel(RATE / 2), 42))
    bank = np.zeros((40, len(freq)))
    for i in range(40):
        bank[i] = np.maximum(0, np.minimum((freq - edges[i]) / (edges[i+1] - edges[i]),
                                          (edges[i+2] - freq) / (edges[i+2] - edges[i+1])))
    coeff = dct(np.log(np.maximum(bank @ power, 1e-20)), type=2, axis=0, norm='ortho')[:13]
    result = {'feature_version': VERSION, 'rms': float(np.sqrt(np.mean(audio ** 2))),
              'zero_crossing_rate': float(np.mean(np.signbit(audio[1:]) != np.signbit(audio[:-1]))),
              'dominant_frequency_hz': float(freq[1 + np.argmax(power.mean(axis=1)[1:])]),
              'band_122_515_ratio': float((power[(freq >= 122) & (freq <= 515)].sum(axis=0) / total).mean())}
    for name, value in [('centroid_hz', centroid), ('spread_hz', spread), ('entropy', entropy),
                        ('rolloff_hz', rolloff), ('flatness', flatness)]:
        result[name + '_mean'] = float(value.mean())
        result[name + '_std'] = float(value.std())
    for i, values in enumerate(coeff):
        result[f'mfcc_{i:02}_mean'] = float(values.mean())
        result[f'mfcc_{i:02}_std'] = float(values.std())
    if not all(np.isfinite(v) for v in result.values() if isinstance(v, float)):
        raise ValueError('Features não finitas')
    return result


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()
