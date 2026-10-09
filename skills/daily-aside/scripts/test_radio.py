#!/usr/bin/env python3
"""Offline regression tests. No credentials or network access."""
import array, base64, importlib.util, json, pathlib, tempfile, unittest, wave

spec=importlib.util.spec_from_file_location('radio',pathlib.Path(__file__).with_name('radio.py'))
r=importlib.util.module_from_spec(spec); spec.loader.exec_module(r)

def episode(language='en'):
    text='word '*180 if language=='en' else 'あ'*420
    return {'title':'Synthetic test only','date':'2026-10-09','config':{'language':language},'segments':[text]*5,
            'sources':[{'label':'Reserved example domain, fixture only','url':'https://example.com/','checkedAt':'2026-10-09T00:00:00Z'}]}

def wav(path):
    with wave.open(str(path),'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(b'\x01\x00'*6000)
    return pathlib.Path(path).read_bytes()

def response(raw,mime='audio/wav',finish='STOP'):
    return {'candidates':[{'finishReason':finish,'content':{'parts':[{'inlineData':{'mimeType':mime,'data':base64.b64encode(raw).decode()}}]}}]}

class RadioTests(unittest.TestCase):
    def test_language_budgets(self):
        self.assertEqual(r.validate_episode(episode())['count'],900)
        self.assertEqual(r.validate_episode(episode('ja'))['count'],2100)
        e=episode('ja'); e['config']['language']='en'
        with self.assertRaises(ValueError): r.validate_episode(e)
        e=episode(); e['config']['language']='fr'
        with self.assertRaises(ValueError): r.validate_episode(e)
        e['config']['speechBudget']={'unit':'words','min':850,'max':1050}
        r.validate_episode(e)

    def test_editorial_validation(self):
        for modify in (lambda e:e['segments'].pop(), lambda e:e['segments'].__setitem__(0,'<script>x</script>'+e['segments'][0]), lambda e:e.update(date='2026-02-31'), lambda e:e['sources'][0].update(checkedAt='2026-10-09T00:00:00'), lambda e:e['sources'][0].update(url='https://name:password@example.com/'), lambda e:e['sources'][0].update(url='https://example.com/?api_key=SYNTHETIC_TEST_TOKEN'), lambda e:e['sources'][0].update(url='https://example.com/#authorization=SYNTHETIC_TEST_TOKEN'), lambda e:e['sources'][0].update(url='https://example.com/#route?api%5Fkey%3DSYNTHETIC_TEST_TOKEN')):
            e=episode(); modify(e)
            with self.assertRaises(ValueError): r.validate_episode(e)

    def test_identity_config_changes(self):
        e=episode(); a=r.edition_hash(e,'model','voice')
        for field,value in [('deliveryStyle','Brisk'),('language','en-GB'),('locale','en-GB')]:
            b=episode(); b['config'][field]=value
            self.assertNotEqual(a,r.edition_hash(b,'model','voice'))
        self.assertNotEqual(a,r.edition_hash(e,'different','voice'))
        self.assertNotEqual(a,r.edition_hash(e,'model','different'))
        b=episode(); b['config']['programmeName']='Display only'; self.assertEqual(a,r.edition_hash(b,'model','voice'))

    def test_wav_and_streaming_pcm_import(self):
        with tempfile.TemporaryDirectory() as d:
            d=pathlib.Path(d); raw=wav(d/'original.wav')
            r.decode_response(response(raw),d/'decoded.wav')
            self.assertEqual(r.inspect_wav(d/'decoded.wav'),.25)
            events=[response(b'\x00\x00'*3000,'audio/L16;codec=pcm;rate=24000',''),response(b'\x00\x00'*3000,'audio/L16;codec=pcm;rate=24000')]
            r.decode_response(events,d/'stream.wav')
            self.assertEqual(r.inspect_wav(d/'stream.wav'),.25)

    def test_bad_responses_not_accepted(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'out.wav'
            for resp in [response(b'bad'),response(b'\x00','audio/L16;codec=pcm;rate=24000'),response(b'\x00\x00','audio/L16;rate=48000'),response(b'\x00\x00','audio/L16;rate=24000','MAX_TOKENS'),response(b'\x00\x00','audio/L16;rate=24000','')]:
                with self.assertRaises((ValueError,wave.Error)): r.decode_response(resp,p)

    def test_durable_attempts_and_cache(self):
        with tempfile.TemporaryDirectory() as d:
            d=pathlib.Path(d); e=episode(); raw=wav(d/'source.wav')
            with self.assertRaises(ValueError): r.cache_import(d/'cache',e,'model','voice',0,response(raw))
            a=r.reserve(d/'cache',e,'model','voice',0); self.assertEqual(a['attempt'],1)
            with self.assertRaises(ValueError): r.reserve(d/'cache',e,'model','voice',0)
            self.assertEqual(r.reserve(d/'cache',e,'model','voice',0,True)['attempt'],2)
            r.cache_import(d/'cache',e,'model','voice',0,response(raw))
            with self.assertRaises(ValueError): r.reserve(d/'cache',e,'model','voice',0,True)
            for i in range(1,5): r.cache_import(d/'cache',e,'model','voice',i,wav_path=d/'source.wav')
            parts=r.cached_parts(d/'cache',e,'model','voice'); self.assertEqual(len(parts),5)
            parts[2].write_bytes(b'corrupt')
            with self.assertRaises(ValueError): r.cached_parts(d/'cache',e,'model','voice')

    def test_request_plan_is_offline_and_preserves_identity(self):
        with tempfile.TemporaryDirectory() as d:
            d=pathlib.Path(d); e=episode()
            p=r.prepare(d/'cache',e,'model','voice',d/'requests')
            self.assertEqual(p['paidRequests'],0); self.assertEqual(p['states'],['missing']*5)
            req=r.read_json(d/'requests/request-0.json')
            self.assertEqual(req['contents'][0]['parts'][0]['text'],e['segments'][0])
            self.assertEqual(req['generationConfig']['speechConfig']['voiceConfig']['prebuiltVoiceConfig']['voiceName'],'voice')
            with self.assertRaises(ValueError): r.prepare(d/'cache',e,'model','voice',d/'requests')

    def test_lock_prevents_parallel_reservation(self):
        with tempfile.TemporaryDirectory() as d:
            e=episode(); directory=r.cache_dir(d,e,'model','voice')
            with r.CacheLock(directory):
                with self.assertRaises(ValueError): r.reserve(d,e,'model','voice',0)

    def test_envelope(self):
        c={'gaps':[[20,25],[40,45],[60,65],[80,85]],'outroStart':100,'fadeStart':113,'duration':118}
        self.assertEqual(r.bed_gain(0,c),0)
        self.assertEqual(r.bed_gain(5,c),1)
        self.assertAlmostEqual(r.bed_gain(15,c),10**(-8/20))
        self.assertEqual(r.bed_gain(23,c),1)
        self.assertEqual(r.bed_gain(115.5,c),.5)
        self.assertEqual(r.bed_gain(118,c),0)

    def test_full_offline_mix(self):
        with tempfile.TemporaryDirectory() as d:
            out=pathlib.Path(d)/'mix'; cues=r.dry_run(out)
            self.assertEqual(cues['duration'],49.25)
            self.assertEqual(len(cues['gaps']),4)
            self.assertTrue(all(abs(b-a-5)<1e-8 for a,b in cues['gaps']))
            self.assertEqual(cues['duration']-cues['outroStart'],18)
            self.assertEqual(cues['duration']-cues['fadeStart'],5)
            for name in ('episode.wav','episode.mp3','mix.json','credits.txt','dry-run.json'): self.assertTrue((out/name).is_file())
            audio=r.run(['ffmpeg','-v','error','-i',str(out/'episode.mp3'),'-f','f32le','pipe:1'])
            samples=array.array('f'); samples.frombytes(audio)
            self.assertLess(max(abs(x) for x in samples),1)
            with self.assertRaises(ValueError): r.dry_run(out)

    def test_mp3_bgm_loops_to_exact_duration(self):
        # Regression: -stream_loop on an MP3 bed lost ~46 ms per loop and failed with 'BGM ended unexpectedly'.
        with tempfile.TemporaryDirectory() as d:
            d=pathlib.Path(d); parts=[]
            for i in range(5):
                wav(d/f'{i}.wav'); parts.append(d/f'{i}.wav')
            r.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=440:sample_rate=48000:duration=1.5','-ac','2','-c:a','libmp3lame','-b:a','64k',str(d/'bed.mp3')])
            credit={'title':'Synthetic MP3 bed','creator':'Generated locally','source':'ffmpeg sine','license':'No external music used','changes':'Looped, ducked, faded; test fixture only'}
            cues=r.render(parts,d/'bed.mp3',d/'mix',credit)
            self.assertEqual(cues['duration'],49.25)
            info=json.loads(r.run(['ffprobe','-v','error','-show_entries','format=duration','-of','json',str(d/'mix/episode.wav')]))
            self.assertAlmostEqual(float(info['format']['duration']),49.25,places=3)
            audio=r.run(['ffmpeg','-v','error','-i',str(d/'mix/episode.wav'),'-ss','40','-t','4','-f','f32le','pipe:1'])
            samples=array.array('f'); samples.frombytes(audio)
            self.assertGreater(max(abs(x) for x in samples),0.01)  # music bed present in the outro, not silence

if __name__=='__main__': unittest.main(verbosity=2)
