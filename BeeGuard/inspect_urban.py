"""Inspeciona os CSVs reais; extrai somente eventos explícitos de população de 2022."""
import csv
import json
import math
from pathlib import Path


def inspect(root, output):
    root, output = Path(root), Path(output)
    if output.exists():
        raise ValueError('Saída já existe')
    output.mkdir(parents=True)
    summary, labels = {}, []
    for year in (2021, 2022):
        path = root / f'inspections_{year}.csv'
        with path.open(encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            fields = reader.fieldnames
        summary[str(year)] = {'file':str(path), 'columns':fields, 'rows':len(rows),
            'hive_tags':sorted({r['Tag number'] for r in rows})}
        if year == 2022:
            required = {'Category','Action detail','Date','Tag number','Queen status'}
            if not required.issubset(fields):
                raise ValueError('Esquema 2022 diferente do esperado')
            for line, row in enumerate(rows, start=2):
                if row['Category'].strip().lower() != 'frames of bees':
                    continue
                value = float(row['Action detail'])
                if not math.isfinite(value) or value < 0:
                    raise ValueError(f'População inválida na linha {line}')
                labels.append({'inspection_id':f'urban_2022_line_{line}',
                    'hive_tag':row['Tag number'],'inspection_timestamp':row['Date'],
                    'frames_bees':value,'queen_status_original':row['Queen status'],
                    'label_source':f'inspections_2022.csv:line:{line}'})
    if labels:
        with (output/'population_inspections_2022.csv').open('w',encoding='utf-8',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(labels[0]))
            w.writeheader()
            w.writerows(labels)
    summary['explicit_population_events_2022']=len(labels)
    summary['warning']='Sem associação automática a WAVs. Tags físicas precisam ser mapeadas aos IDs de áudio. 2021 não foi somado automaticamente: caixas não observadas podem produzir rótulos incompletos.'
    (output/'inspection_summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
    return summary

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',default='data/raw/urban/annotations')
    p.add_argument('--output',default='data/metadata/urban_inspections')
    a=p.parse_args()
    print(json.dumps(inspect(a.input,a.output),indent=2,ensure_ascii=False))
