import csv
import tempfile
import unittest
from pathlib import Path
import numpy as np
from scipy.io import wavfile
from audio_pipeline import load_audio, quality, features, WINDOW
from prepare_dataset import prepare
from extract_features import extract

class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
    def tearDown(self):
        self.tmp.cleanup()
    def tone(self, name='tone.wav', seconds=20, rate=16000, stereo=False):
        t = np.arange(seconds * rate) / rate
        x = np.round(10000 * np.sin(2*np.pi*250*t)).astype(np.int16)
        if stereo:
            x = np.column_stack([x,x])
        path = self.root / name
        wavfile.write(path, rate, x)
        return path
    def manifest(self, files, **extra):
        path = self.root / 'manifest.csv'
        fields = ['file','source','hive_id','frames_bees','label_source','inspection_id']
        with path.open('w', newline='') as f:
            w = csv.DictWriter(f,fieldnames=fields)
            w.writeheader()
            for item in files:
                w.writerow(dict(file=item.name, source='synthetic_test', hive_id='TEST_ONLY', **extra))
        return path
    def test_resampling_and_features(self):
        x, meta = load_audio(self.tone(seconds=10,rate=48000,stereo=True))
        self.assertEqual(len(x), WINDOW)
        self.assertEqual(meta['original_channels'],2)
        desc=features(x)
        self.assertLess(abs(desc['dominant_frequency_hz']-250),32)
        self.assertGreater(desc['band_122_515_ratio'],0.99)
        self.assertEqual(len([k for k in desc if k.startswith('mfcc')]),26)
    def test_windows_duplicates_tail_and_extract(self):
        path=self.tone(seconds=21)
        manifest=self.manifest([path,path])
        rows, report=prepare(manifest,self.root/'prepared',limit=0)
        self.assertEqual(len(rows),2)
        self.assertEqual(report[0]['tail_seconds'],1)
        self.assertEqual(report[1]['status'],'duplicate')
        self.assertEqual(rows[0]['frames_bees'],'')
        feats=extract(self.root/'prepared/metadata.csv',self.root/'features.csv')
        self.assertEqual(len(feats),2)
        self.assertEqual(feats[0]['recording_id'],feats[1]['recording_id'])
    def test_short_and_corrupt(self):
        path=self.tone(seconds=1)
        bad=self.root/'bad.wav'
        bad.write_bytes(b'not a wave')
        rows, report=prepare(self.manifest([path,bad]),self.root/'prepared')
        self.assertEqual(rows,[])
        self.assertTrue(all(r['status']=='error' for r in report))
    def test_quality_silence_clipping(self):
        self.assertEqual(quality(np.zeros(WINDOW))['quality_status'],'review')
        self.assertEqual(quality(np.ones(WINDOW))['quality_status'],'review')
    def test_labels_require_provenance(self):
        rows,report=prepare(self.manifest([self.tone()],frames_bees='17'), self.root/'prepared')
        self.assertEqual(rows,[])
        self.assertEqual(report[0]['status'],'error')
    def test_nonfinite_rejected(self):
        path=self.root/'nan.wav'
        wavfile.write(path,16000,np.full(WINDOW,np.nan,dtype=np.float32))
        with self.assertRaises(ValueError): load_audio(path)
    def test_preserve_outputs_and_limit(self):
        m=self.manifest([self.tone(seconds=30)])
        rows,report=prepare(m,self.root/'prepared',limit=1)
        self.assertEqual(len(rows),1)
        self.assertEqual(report[0]['skipped_full_windows'],2)
        with self.assertRaises(ValueError): prepare(m,self.root/'prepared')

if __name__=='__main__': unittest.main()
