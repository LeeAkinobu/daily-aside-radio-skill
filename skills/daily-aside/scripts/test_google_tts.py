#!/usr/bin/env python3
"""Mock-only Google client tests; never read actual environment credentials."""
import base64, json, pathlib, tempfile, unittest, wave
from unittest.mock import patch
import google_tts as g
import radio

KEY='synthetic-test-key-not-a-credential'

def episode():
    return {'title':'Synthetic QA','date':'2026-10-09','segments':['word '*180]*5,
            'sources':[{'label':'Fixture','url':'https://example.com/','checkedAt':'2026-10-09T00:00:00Z'}]}

def reply(directory):
    p=pathlib.Path(directory)/'synthetic.wav'
    with wave.open(str(p),'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(b'\x01\x00'*100)
    return {'candidates':[{'finishReason':'STOP','content':{'parts':[{'inlineData':{'mimeType':'audio/wav','data':base64.b64encode(p.read_bytes()).decode()}}]}}]}

class GoogleTests(unittest.TestCase):
    def call(self,d,send,**kw):
        args=dict(root=pathlib.Path(d)/'cache',e=episode(),model='gemini-3.8-flash-tts',voice='VerifiedTestVoice',index=0,
                  key_provider=lambda:KEY,input_price=.5,output_price=9,budget=1,approved=True,send=send)
        args.update(kw); return g.generate(**args)

    def test_generate_and_reuse_without_secret_or_network(self):
        with tempfile.TemporaryDirectory() as d:
            calls=[]; data=reply(d)
            result=self.call(d,lambda m,k,b:(calls.append((m,k,b)) or data))
            self.assertEqual(result['newRequests'],1); self.assertEqual(len(calls),1)
            self.assertEqual(calls[0][2]['generationConfig']['maxOutputTokens'],4096)
            def forbidden(*args): self.fail('Cached path accessed credentials or network')
            result=self.call(d,forbidden,key_provider=forbidden)
            self.assertEqual(result['newRequests'],0)
            for p in (pathlib.Path(d)/'cache').rglob('*.json'): self.assertNotIn(KEY,p.read_text())

    def test_approval_before_key_access(self):
        with tempfile.TemporaryDirectory() as d:
            def forbidden(*args): self.fail('Unapproved call used credential or network')
            with self.assertRaises(ValueError): self.call(d,forbidden,approved=False,key_provider=forbidden)

    def test_budget_before_key_access(self):
        with tempfile.TemporaryDirectory() as d:
            def forbidden(*args): self.fail('Over-budget call used credential or network')
            with self.assertRaises(ValueError): self.call(d,forbidden,budget=.001,key_provider=forbidden)

    def test_unknown_failure_is_not_retried(self):
        with tempfile.TemporaryDirectory() as d:
            calls=[]
            def failed(*args): calls.append(1); raise ValueError('Synthetic connection loss')
            with self.assertRaises(ValueError): self.call(d,failed)
            with self.assertRaises(ValueError): self.call(d,failed)
            self.assertEqual(len(calls),1)
            data=reply(d); result=self.call(d,lambda *args:data,retry_unknown=True)
            self.assertAlmostEqual(result['estimatedTotalUsd'],2*result['estimatedRequestUsd'])

    def test_bad_response_keeps_reservation(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError): self.call(d,lambda *args:{'candidates':[]})
            directory=radio.cache_dir(pathlib.Path(d)/'cache',episode(),'gemini-3.8-flash-tts','VerifiedTestVoice')
            self.assertEqual(radio.chunk_state(directory,0),'unknown')
            self.assertEqual(len(radio.read_json(directory/'attempts.json')),1)

    def test_manual_unpriced_attempts_block_automatic_budget(self):
        with tempfile.TemporaryDirectory() as d:
            radio.reserve(pathlib.Path(d)/'cache',episode(),'gemini-3.8-flash-tts','VerifiedTestVoice',0)
            with self.assertRaises(ValueError): self.call(d,lambda *args:None,retry_unknown=True)

    def test_budget_shared_across_revisions_and_voices(self):
        with tempfile.TemporaryDirectory() as d:
            data=reply(d)
            self.call(d,lambda *args:data,budget=.05,budget_id='one-approved-episode')
            def forbidden(*args): self.fail('Revision exceeded shared budget')
            with self.assertRaises(ValueError):
                self.call(d,forbidden,budget=.05,voice='DifferentVoice',budget_id='one-approved-episode',key_provider=forbidden)
            changed=episode(); changed['segments'][0]=changed['segments'][0].replace('word','term',1)
            with self.assertRaises(ValueError):
                self.call(d,forbidden,budget=.05,e=changed,budget_id='one-approved-episode',key_provider=forbidden)

    def test_unpaid_service_requires_public_only_text(self):
        with tempfile.TemporaryDirectory() as d:
            def forbidden(*args): self.fail('Unpaid service accessed personal text or credentials')
            with self.assertRaises(ValueError): self.call(d,forbidden,service_tier='unpaid',key_provider=forbidden)
            e=episode(); e['config']={'contentClass':'public'}; data=reply(d)
            result=self.call(d,lambda *args:data,e=e,service_tier='unpaid')
            self.assertEqual(result['newRequests'],1)

    def test_transport_json_uses_fixed_provider(self):
        with tempfile.TemporaryDirectory() as d:
            payload=json.dumps(reply(d)).encode(); requests=[]
            class Response:
                def __enter__(self): return self
                def __exit__(self,*args): pass
                def read(self,limit): return payload
            class Opener:
                def open(self,request,timeout): requests.append((request,timeout)); return Response()
            with patch.object(g.urllib.request,'build_opener',return_value=Opener()):
                result=g.transport('gemini-3.8-flash-tts',KEY,{'mock':'request'})
            self.assertEqual(result['candidates'][0]['finishReason'],'STOP')
            self.assertEqual(requests[0][0].full_url,'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash-tts:generateContent')
            self.assertNotIn(KEY,requests[0][0].full_url)
            self.assertEqual(requests[0][1],120)

    def test_redirect_rejected_and_host_cannot_be_injected(self):
        with self.assertRaises(ValueError): g.NoRedirects().redirect_request(None,None,302,'',None,'https://example.com/')
        with self.assertRaises(ValueError): g.transport('https://example.com/',KEY,{})

if __name__=='__main__': unittest.main(verbosity=2)
