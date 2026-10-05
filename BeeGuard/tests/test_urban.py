import csv
import json
import tempfile
import unittest
from pathlib import Path
from inspect_urban import inspect

class UrbanTests(unittest.TestCase):
    def test_real_annotations_traceability(self):
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'inspections'
            result=inspect(root/'data/raw/urban/annotations',out)
            with (out/'population_inspections_2022.csv').open() as f:
                labels=list(csv.DictReader(f))
            with (root/'data/raw/urban/annotations/inspections_2022.csv').open() as f:
                original=list(csv.DictReader(f))
            self.assertEqual(result['explicit_population_events_2022'],34)
            for row in labels:
                line=int(row['label_source'].split(':')[-1])
                source=original[line-2]
                self.assertEqual(source['Category'],'frames of bees')
                self.assertEqual(float(source['Action detail']),float(row['frames_bees']))
                self.assertEqual(source['Tag number'],row['hive_tag'])
