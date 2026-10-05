"""Cria manifesto sem inventar inspeções/rótulos."""
import argparse
import csv
import os
from pathlib import Path

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--source', required=True)
    p.add_argument('--hive-id', default='', help='Somente se TODOS os arquivos forem da mesma colmeia')
    a = p.parse_args()
    folder, output = Path(a.input).resolve(), Path(a.output).resolve()
    files = sorted(folder.rglob('*.wav'))
    if not files:
        p.error('Nenhum WAV encontrado')
    if output.exists():
        p.error('Manifesto já existe')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['file', 'source', 'hive_id', 'timestamp', 'frames_bees', 'label_source', 'inspection_id'])
        for path in files:
            w.writerow([os.path.relpath(path, output.parent), a.source, a.hive_id, '', '', '', ''])
    print(f'{len(files)} arquivos indexados; nenhum rótulo foi atribuído.')
