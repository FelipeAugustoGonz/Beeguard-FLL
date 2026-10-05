"""Manifesto explícito -> WAVs padronizados + metadados + relatório."""
import argparse
import csv
import json
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from audio_pipeline import load_audio, quality, sha256, RATE, WINDOW


def prepare(manifest, output, limit=12):
    manifest, output = Path(manifest).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError('Pasta de saída já existe. Use outro nome para preservar resultados.')
    with manifest.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        if not {'file', 'source', 'hive_id'}.issubset(reader.fieldnames or []):
            raise ValueError('Manifesto precisa de file,source,hive_id')
        entries = list(reader)
    output.mkdir(parents=True)
    rows, report, seen = [], [], set()
    for entry in entries:
        name = entry['file']
        try:
            if not name or not entry['source']:
                raise ValueError('file/source vazios')
            path = (manifest.parent / name).resolve()
            digest = sha256(path)
            if digest in seen:
                report.append({'file': name, 'status': 'duplicate', 'sha256': digest})
                continue
            audio, original = load_audio(path)
            count = len(audio) // WINDOW
            if count == 0:
                raise ValueError('Menos de 10 s; não será repetido nem preenchido')
            used = min(count, limit) if limit else count
            # Não inferir rótulos por arquivo, data ou nome de pasta.
            label = entry.get('frames_bees', '').strip()
            if label:
                if not np.isfinite(float(label)) or float(label) < 0:
                    raise ValueError('frames_bees deve ser finito e não negativo')
                if not entry.get('label_source', '').strip() or not entry.get('inspection_id', '').strip():
                    raise ValueError('Rótulo exige label_source e inspection_id rastreáveis')
            seen.add(digest)
            for i in range(used):
                chunk = audio[i*WINDOW:(i+1)*WINDOW]
                qc = quality(chunk)
                if original['source_clipping_ratio'] > 0.01:
                    qc['quality_status'] = 'review'
                    qc['quality_reasons'] += ';source_clipping'
                audio_id = f'{digest[:24]}_{i:05}'
                filename = audio_id + '.wav'
                pcm = np.round(np.clip(chunk, -1, 32767 / 32768) * 32768).astype(np.int16)
                wavfile.write(output / filename, RATE, pcm)
                rows.append(dict(audio_id=audio_id, file=filename, source=entry['source'],
                    hive_id=entry['hive_id'], recording_id=digest, source_file=name,
                    source_sha256=digest, start_seconds=i*10, duration_seconds=10,
                    sample_rate=RATE, timestamp=entry.get('timestamp', ''),
                    frames_bees=label, label_source=entry.get('label_source', ''),
                    inspection_id=entry.get('inspection_id', ''), **original, **qc))
            report.append({'file': name, 'status': 'processed', 'windows': used,
                           'skipped_full_windows': count-used, 'tail_seconds': (len(audio)%WINDOW)/RATE})
        except (OSError, ValueError) as exc:
            report.append({'file': name, 'status': 'error', 'reason': str(exc)})
    fields = list(rows[0]) if rows else ['audio_id', 'file', 'source', 'hive_id', 'quality_status']
    with (output / 'metadata.csv').open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    (output / 'report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    return rows, report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--max-windows-per-file', type=int, default=12, help='0 = todas; padrão 12')
    a = p.parse_args()
    if a.max_windows_per_file < 0:
        p.error('Limite não pode ser negativo')
    rows, report = prepare(a.manifest, a.output, a.max_windows_per_file)
    errors = sum(r['status'] == 'error' for r in report)
    print(f'{len(rows)} janelas; {errors} erros. Consulte metadata.csv e report.json.')
    if errors or not rows:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
