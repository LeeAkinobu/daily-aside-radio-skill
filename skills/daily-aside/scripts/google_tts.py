#!/usr/bin/env python3
"""User-run Gemini TTS client. Tests inject a mock transport; no automatic retries."""
import argparse, datetime, json, math, os, pathlib, re, sys, tempfile, urllib.error, urllib.request
import radio

MAX_OUTPUT_TOKENS=4096
MAX_RESPONSE_BYTES=12_000_000

class NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Provider redirect rejected; credentials were not forwarded.')

def request_body(e,voice,index):
    return {'contents':[{'parts':[{'text':e['segments'][index],'speech_metadata':{'style':radio.delivery_style(e)}}]}],
            'generationConfig':{'temperature':1,'maxOutputTokens':MAX_OUTPUT_TOKENS,'responseModalities':['AUDIO'],
            'speechConfig':{'voiceConfig':{'prebuiltVoiceConfig':{'voiceName':voice}}}}}

def transport(model,key,body):
    """Fixed HTTPS provider; no key in URL/logs; no redirects or retries."""
    if not re.fullmatch(r'gemini-[a-z0-9.-]+-tts',model): raise ValueError('Invalid Gemini TTS model identifier.')
    if not isinstance(key,str) or not key or len(key)>4096 or re.search(r'[^\x21-\x7e]',key):
        raise ValueError('Provider credential is missing or malformed.')
    url=f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
    request=urllib.request.Request(url,data=json.dumps(body).encode('utf-8'),headers={'Content-Type':'application/json','x-goog-api-key':key},method='POST')
    try:
        with urllib.request.build_opener(NoRedirects()).open(request,timeout=120) as response:
            raw=response.read(MAX_RESPONSE_BYTES+1)
        if len(raw)>MAX_RESPONSE_BYTES: raise ValueError('Provider response exceeds the size limit.')
        return json.loads(raw)
    except urllib.error.HTTPError as exc:
        raise ValueError(f'Provider returned HTTP {exc.code}. No retry was made; this attempt may have been billed.') from None
    except (urllib.error.URLError,TimeoutError,ConnectionError,OSError,json.JSONDecodeError):
        raise ValueError('Provider response is unknown or invalid. No retry was made; inspect the attempt before authorizing another.') from None

def generate(root,e,model,voice,index,key_provider,input_price,output_price,budget,approved=False,retry_unknown=False,send=transport,budget_id='default',service_tier='paid'):
    """Execute one approved chunk, reserving estimated cost before the provider call."""
    if not approved: raise ValueError('Explicit send-and-charge approval is required.')
    if service_tier not in ('paid','unpaid'): raise ValueError('Confirm whether the Google service is paid or unpaid.')
    content_class=e.get('config',{}).get('contentClass','personal')
    if content_class not in ('public','personal','confidential'): raise ValueError('Unknown contentClass.')
    if service_tier=='unpaid' and content_class!='public':
        raise ValueError('Do not send personal or confidential information to unpaid Gemini services. Use public-only text or an appropriately approved paid service.')
    if not 0<=index<5: raise ValueError('Chunk index must be 0–4.')
    if not re.fullmatch(r'gemini-[a-z0-9.-]+-tts',model): raise ValueError('Invalid Gemini TTS model identifier.')
    if not isinstance(voice,str) or not voice.strip() or len(voice)>120: raise ValueError('Choose a verified supported voice.')
    if not all(isinstance(n,(int,float)) and math.isfinite(n) and n>0 for n in (input_price,output_price,budget)):
        raise ValueError('Current positive per-million-token prices and a positive total estimated USD limit are required.')
    if not isinstance(budget_id,str) or not budget_id.strip() or len(budget_id)>120: raise ValueError('A stable approved budget ID is required.')
    directory=radio.cache_dir(root,e,model,voice)
    budget_directory=pathlib.Path(root)/'budgets'/radio.digest(budget_id.encode('utf-8'))
    budget_directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    body=request_body(e,voice,index)
    # UTF-8 bytes plus ample request overhead form a conservative input estimate.
    # This is an estimate, not a Google account-wide or guaranteed billing cap.
    estimated=(len(json.dumps(body,ensure_ascii=False).encode('utf-8'))+2048)*input_price/1_000_000+MAX_OUTPUT_TOKENS*output_price/1_000_000
    with radio.CacheLock(budget_directory),radio.CacheLock(directory):
        state=radio.chunk_state(directory,index)
        if state=='ready': return {'chunk':index,'state':'ready','reused':True,'newRequests':0}
        if state=='unknown' and not retry_unknown: raise ValueError('Prior request is unknown. Obtain retry approval and pass --retry-unknown.')
        if (directory/f'part-{index}.wav').exists() or (directory/f'part-{index}.json').exists():
            raise ValueError('Partial cache files need inspection; do not overwrite them.')
        ledger=directory/'attempts.json'; attempts=radio.read_json(ledger) if ledger.exists() else []
        if any('estimatedUsd' not in a for a in attempts):
            raise ValueError('Earlier manual attempts have unrecorded costs. Reconcile their billing before using the automatic client.')
        if any(a.get('budgetId')!=budget_id for a in attempts):
            raise ValueError('This edition belongs to another approved budget ID. Keep the original ID and reconcile prior charges.')
        budget_ledger=budget_directory/'attempts.json'
        budget_attempts=radio.read_json(budget_ledger) if budget_ledger.exists() else []
        if not isinstance(budget_attempts,list) or any(not isinstance(a,dict) or not isinstance(a.get('estimatedUsd'),(int,float)) or not math.isfinite(a['estimatedUsd']) or a['estimatedUsd']<0 for a in budget_attempts):
            raise ValueError('Budget ledger is invalid; reconcile it before generation.')
        spent=sum(a['estimatedUsd'] for a in budget_attempts)
        if spent+estimated>budget+1e-12:
            raise ValueError('The local estimated total would exceed the approved USD limit. No request was made.')
        key=key_provider()
        if not isinstance(key,str) or not key or len(key)>4096 or re.search(r'[^\x21-\x7e]',key):
            raise ValueError('Provider credential is missing or malformed. No request was made.')
        attempt={'chunk':index,'reservedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 'attempt':1+sum(a['chunk']==index for a in attempts),'estimatedUsd':estimated,
                 'inputUsdPerMillion':input_price,'outputUsdPerMillion':output_price,'state':'unknown',
                 'editionHash':radio.edition_hash(e,model,voice),'budgetId':budget_id}
        attempts.append(attempt); budget_attempts.append(attempt)
        radio.write_json(budget_ledger,budget_attempts); radio.write_json(ledger,attempts)
        # Persist before transmission. Exceptions retain unknown state and estimated cost.
        response=send(model,key,body)
        key=None
        with tempfile.TemporaryDirectory(dir=directory) as temp:
            provisional=pathlib.Path(temp)/'audio.wav'; radio.decode_response(response,provisional)
            sha=radio.digest(provisional.read_bytes()); duration=radio.inspect_wav(provisional)
            os.replace(provisional,directory/f'part-{index}.wav')
            radio.write_json(directory/f'part-{index}.json',{'sha256':sha,'seconds':duration})
        attempt['state']='ready'; radio.write_json(ledger,attempts); radio.write_json(budget_ledger,budget_attempts)
        return {'chunk':index,'state':'ready','reused':False,'newRequests':1,'estimatedRequestUsd':estimated,'estimatedTotalUsd':spent+estimated}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('episode','cache','model','voice'): p.add_argument('--'+name,required=True)
    selection=p.add_mutually_exclusive_group(required=True)
    selection.add_argument('--chunk',type=int)
    selection.add_argument('--all',action='store_true',help='Generate missing chunks in order and reuse successful chunks')
    p.add_argument('--service-tier',required=True,choices=['paid','unpaid'],help='Confirm the actual Google service/account tier; unpaid requires public-only text')
    p.add_argument('--budget-id',required=True,help='Reuse the same approved episode budget ID across text/model/voice revisions')
    p.add_argument('--input-usd-per-million',type=float,required=True)
    p.add_argument('--output-usd-per-million',type=float,required=True)
    p.add_argument('--max-estimated-total-usd',type=float,required=True)
    p.add_argument('--pricing-checked-at',required=True,help='YYYY-MM-DD; verify current official pricing within 30 days')
    p.add_argument('--approve-send-and-charge',action='store_true',help='Confirm approval for this text, Google, voice/model and episode budget')
    p.add_argument('--retry-unknown',action='store_true',help='Only after approval of possible duplicate charges')
    a=p.parse_args()
    checked=datetime.date.fromisoformat(a.pricing_checked_at)
    age=(datetime.datetime.now(datetime.timezone.utc).date()-checked).days
    if not 0<=age<=30: raise ValueError('Check current official pricing and use a date within the last 30 days.')
    if a.all and a.retry_unknown: raise ValueError('Retry only an explicitly selected --chunk; do not retry all unknown requests together.')
    e=radio.read_json(a.episode)
    for index in (range(5) if a.all else [a.chunk]):
        result=generate(a.cache,e,a.model,a.voice,index,
                        lambda:os.environ.get('GEMINI_API_KEY'),a.input_usd_per_million,a.output_usd_per_million,
                        a.max_estimated_total_usd,a.approve_send_and_charge,a.retry_unknown,budget_id=a.budget_id,service_tier=a.service_tier)
        print(json.dumps(result),flush=True)

if __name__=='__main__':
    try: main()
    except (ValueError,OSError,KeyError,TypeError,EOFError,radio.wave.Error) as exc:
        print(f'Error: {exc}',file=sys.stderr); sys.exit(1)
