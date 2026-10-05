"""Extrai features somente de janelas aprovadas nas verificações técnicas."""
import argparse
import csv
from pathlib import Path
from audio_pipeline import load_audio, features


def extract(metadata, output):
    metadata, output = Path(metadata).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError('Arquivo de saída já existe')
    rows = []
    with metadata.open(encoding='utf-8', newline='') as f:
        for row in csv.DictReader(f):
            if row['quality_status'] != 'pass':
                continue
            audio, _ = load_audio(metadata.parent / row['file'])
            rows.append({**row, **features(audio)})
    if not rows:
        raise ValueError('Nenhuma janela aprovada; consulte o relatório de qualidade')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return rows


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--metadata', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    print(f'{len(extract(a.metadata, a.output))} janelas com features salvas.')
