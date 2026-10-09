#!/usr/bin/env python3
"""Local-only radio validation, cached TTS response import, and offline mixing."""
import argparse, array, hashlib, json, math, os, pathlib, re, shutil, subprocess, sys, tempfile, wave

RATE = 48000
STYLE = 'A calm, warm radio host with a little gentle wit. Speak naturally and leave room to breathe.'

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))

def digest(data):
    return hashlib.sha256(data).hexdigest()

def read_json(path):
    path=pathlib.Path(path)
    if path.stat().st_size>16_000_000: raise ValueError('JSON input exceeds the size limit.')
    return json.loads(path.read_text(encoding='utf-8'))

def write_json(path, value):
    path = pathlib.Path(path)
    temp = path.with_name(path.name + '.tmp')
    with open(temp, 'w', encoding='utf-8') as f:
        os.chmod(temp, 0o600)
        f.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    os.replace(temp, path)

def validate_episode(e):
    if not isinstance(e, dict):
        raise ValueError('Episode must be a JSON object.')
    parts = e.get('segments')
    if not isinstance(parts, list) or len(parts) != 5 or any(not isinstance(x,str) or not x.strip() for x in parts):
        raise ValueError('Exactly five nonempty segments are required.')
    for part in parts:
        if '[NEXT_TOPIC]' in part or re.search(r'<(?!short pause>|long pause>)[^>]*>', part):
            raise ValueError('Segments must omit separators and use only supported pause tags.')
    config=e.get('config',{})
    if not isinstance(config,dict): raise ValueError('config must be an object.')
    language=config.get('language','en')
    if not isinstance(language,str) or not re.fullmatch(r'[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*',language): raise ValueError('language must be a language code, such as en or ja.')
    locale=config.get('locale',language)
    if not isinstance(locale,str) or not re.fullmatch(r'[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*',locale): raise ValueError('locale must be a locale code, such as en-US or ja-JP.')
    for field in ('programmeName','djName'):
        if field in config and (not isinstance(config[field],str) or len(config[field])>120): raise ValueError(f'Invalid {field}.')
    clean=' '.join(re.sub(r'<short pause>|<long pause>', '', x) for x in parts)
    defaults={'unit':'characters','min':1950,'max':2250} if language.startswith('ja') else {'unit':'words','min':850,'max':1050}
    if not language.startswith(('en','ja')) and 'speechBudget' not in config:
        raise ValueError('Provide an explicit speechBudget for this language.')
    budget=config.get('speechBudget',defaults)
    if not isinstance(budget,dict) or budget.get('unit') not in ('words','characters') or type(budget.get('min')) is not int or type(budget.get('max')) is not int or not 1<=budget['min']<=budget['max']<=10000:
        raise ValueError('speechBudget requires unit, min and max within 1–10000.')
    count=len(re.sub(r'\s','',clean)) if budget['unit']=='characters' else len(re.findall(r"\b[\w]+(?:['’\-][\w]+)*\b",clean))
    if not budget['min']<=count<=budget['max']:
        raise ValueError(f"Spoken budget must be {budget['min']}–{budget['max']} {budget['unit']}; found {count}.")
    if not isinstance(e.get('title'), str) or not e['title'].strip():
        raise ValueError('Episode title is required.')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', str(e.get('date',''))):
        raise ValueError('Episode date must be YYYY-MM-DD.')
    sources = e.get('sources')
    if not isinstance(sources, list) or not sources:
        raise ValueError('Primary sources with checkedAt timestamps are required.')
    from datetime import datetime
    datetime.strptime(e['date'],'%Y-%m-%d')
    from urllib.parse import urlparse,parse_qsl,unquote
    for source in sources:
        if not isinstance(source,dict) or not source.get('label'):
            raise ValueError('Each source needs a label.')
        u = urlparse(str(source.get('url','')))
        if u.scheme != 'https' or not u.hostname or u.username or u.password:
            raise ValueError('Source URLs must be credential-free HTTPS URLs.')
        sensitive={'key','apikey','token','accesstoken','refreshtoken','secret','clientsecret','password','credential','signature','sig','authorization','auth','code','xamzsignature','xamzcredential','xamzsecuritytoken','xgoogsignature','xgoogcredential'}
        fragment=unquote(u.fragment)
        parameters=parse_qsl(u.query.replace(';','&'))+parse_qsl(fragment.replace(';','&'))+parse_qsl(fragment.partition('?')[2].replace(';','&'))
        if any(re.sub(r'[^a-z]','',key.lower()) in sensitive for key,_ in parameters) or re.search(r'(?:token|key|secret|password)=',fragment,re.I):
            raise ValueError('Source URL appears to contain credentials; use a clean public source URL.')
        dt = datetime.fromisoformat(str(source.get('checkedAt','')).replace('Z','+00:00'))
        if dt.utcoffset() is None:
            raise ValueError('Source timestamp must include a time zone.')
    return {'count':count,'unit':budget['unit'],'language':language,'segments':5}

def delivery_style(e):
    config=e.get('config',{})
    if not isinstance(config,dict): raise ValueError('config must be an object.')
    style=config.get('deliveryStyle',STYLE)
    if not isinstance(style,str) or not style.strip() or len(style)>2000: raise ValueError('Invalid deliveryStyle.')
    language=config.get('language','en'); locale=config.get('locale',language)
    return f'Narrate in {language}, locale {locale}. '+style

def edition_hash(e, model, voice):
    validate_episode(e)
    return digest(canonical({'version':1,'segments':e['segments'],'model':model,'voice':voice,'style':delivery_style(e),'language':e.get('config',{}).get('language','en')}).encode())

def run(command):
    result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise ValueError('Audio processing failed. Check file format and available disk space.')
    return result.stdout

def inspect_wav(path):
    with wave.open(str(path),'rb') as w:
        if w.getcomptype() != 'NONE' or w.getsampwidth() != 2 or w.getnchannels() != 1 or w.getframerate() != 24000:
            raise ValueError('Cached speech must be 24 kHz mono 16-bit PCM WAV.')
        n=w.getnframes()
        if not n or n>4_000_000 or len(w.readframes(n))!=n*2:
            raise ValueError('Speech is empty, truncated, or too long.')
        return n/24000

def decode_response(data, destination):
    """Accept one JSON response or an ordered list of streaming response events."""
    import base64
    events = data if isinstance(data,list) else [data]
    blocks=[]; mime=None; finished=False
    for event in events:
        if finished: raise ValueError('Unexpected event after terminal STOP.')
        candidates=event.get('candidates',[])
        if len(candidates)!=1:
            raise ValueError('Expected exactly one TTS candidate.')
        candidate=candidates[0]
        finish=candidate.get('finishReason')
        if finish and finish!='STOP':
            raise ValueError('TTS did not finish normally; do not cache incomplete speech.')
        finished=finished or finish=='STOP'
        for part in candidate.get('content',{}).get('parts',[]):
            inline=part.get('inlineData')
            if not inline: continue
            current=inline.get('mimeType','')
            if mime is not None and current!=mime:
                raise ValueError('Inconsistent audio types in one response.')
            mime=current
            blocks.append(base64.b64decode(inline.get('data',''),validate=True))
    if not finished or not blocks:
        raise ValueError('Missing audio or final STOP status.')
    raw=b''.join(blocks)
    if len(raw)>8_000_000:
        raise ValueError('Speech exceeds the per-segment size limit.')
    destination=pathlib.Path(destination)
    if mime and re.match(r'^audio/(?:wav|x-wav)(?:;|$)',mime,re.I):
        if len(blocks)!=1 or raw[:4]!=b'RIFF' or raw[8:12]!=b'WAVE':
            raise ValueError('Expected one complete WAV audio response.')
        destination.write_bytes(raw)
    elif mime and re.fullmatch(r'audio/(?:L16|pcm);\s*codec=pcm;\s*rate=24000',mime,re.I):
        if len(raw)%2: raise ValueError('PCM data has an incomplete sample.')
        with wave.open(str(destination),'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(raw)
    elif mime and re.fullmatch(r'audio/(?:L16|pcm);\s*rate=24000',mime,re.I):
        if len(raw)%2: raise ValueError('PCM data has an incomplete sample.')
        with wave.open(str(destination),'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(raw)
    else:
        raise ValueError('Unsupported audio MIME type; do not guess its sample rate or encoding.')
    os.chmod(destination,0o600)
    inspect_wav(destination)

def cache_dir(root, e, model, voice):
    path=pathlib.Path(root)/edition_hash(e,model,voice)
    path.mkdir(parents=True,exist_ok=True,mode=0o700)
    return path

class CacheLock:
    def __init__(self, directory): self.path=directory/'active.lock'
    def __enter__(self):
        try: self.fd=os.open(self.path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        except FileExistsError: raise ValueError('Cache is locked. Confirm no active process before manually removing a stale lock.')
        return self
    def __exit__(self,*args):
        os.close(self.fd); self.path.unlink()

def chunk_state(directory,index):
    p=directory/f'part-{index}.wav'; meta=directory/f'part-{index}.json'
    if p.is_file() and meta.is_file():
        if digest(p.read_bytes())!=read_json(meta).get('sha256'): raise ValueError(f'Chunk {index} integrity check failed.')
        inspect_wav(p)
        return 'ready'
    ledger=directory/'attempts.json'
    attempts=read_json(ledger) if ledger.exists() else []
    return 'unknown' if p.exists() or meta.exists() or any(a['chunk']==index for a in attempts) else 'missing'

def reserve(root,e,model,voice,index,retry=False):
    if not 0<=index<5: raise ValueError('Chunk index must be 0–4.')
    directory=cache_dir(root,e,model,voice)
    with CacheLock(directory):
        state=chunk_state(directory,index)
        if state=='ready': raise ValueError('Chunk is already ready; do not pay to regenerate it.')
        if state=='unknown' and not retry: raise ValueError('Previous attempt is unknown. Obtain retry approval before --retry-unknown.')
        if (directory/f'part-{index}.wav').exists() or (directory/f'part-{index}.json').exists():
            raise ValueError('Partial cache files need inspection; do not overwrite them.')
        ledger=directory/'attempts.json'; attempts=read_json(ledger) if ledger.exists() else []
        from datetime import datetime,timezone
        attempts.append({'chunk':index,'reservedAt':datetime.now(timezone.utc).isoformat(),'attempt':1+sum(a['chunk']==index for a in attempts)})
        write_json(ledger,attempts)
        return {'chunk':index,'state':'unknown','attempt':attempts[-1]['attempt'],'message':'Reserved locally; no network request was made.'}

def prepare(root,e,model,voice,out):
    directory=cache_dir(root,e,model,voice)
    out=pathlib.Path(out)
    if out.exists(): raise ValueError('Request output exists; choose a new directory.')
    out.mkdir(parents=True,mode=0o700)
    states=[]
    for i,part in enumerate(e['segments']):
        state=chunk_state(directory,i); states.append(state)
        body={'contents':[{'parts':[{'text':part,'speech_metadata':{'style':delivery_style(e)}}]}],
              'generationConfig':{'temperature':1,'maxOutputTokens':4096,'responseModalities':['AUDIO'],
              'speechConfig':{'voiceConfig':{'prebuiltVoiceConfig':{'voiceName':voice}}}}}
        write_json(out/f'request-{i}.json',body)
    plan={'editionHash':edition_hash(e,model,voice),'model':model,'voice':voice,'states':states,'paidRequests':0}
    write_json(out/'plan.json',plan)
    return plan

def cache_import(root,e,model,voice,index,response=None,wav_path=None):
    if not 0<=index<5: raise ValueError('Chunk index must be 0–4.')
    directory=cache_dir(root,e,model,voice)
    target=directory/f'part-{index}.wav'; metadata=directory/f'part-{index}.json'
    with CacheLock(directory):
        if target.exists() or metadata.exists():
            raise ValueError('Cached chunk already exists; use a separate cache for a replacement.')
        with tempfile.TemporaryDirectory(dir=directory) as temp:
            provisional=pathlib.Path(temp)/'audio.wav'
            if wav_path is not None:
                inspect_wav(wav_path); shutil.copyfile(wav_path,provisional); os.chmod(provisional,0o600)
            else:
                ledger=directory/'attempts.json'
                if not ledger.exists() or not any(a['chunk']==index for a in read_json(ledger)):
                    raise ValueError('Reserve this chunk before the external request. Use import-wav for existing user-supplied speech.')
                decode_response(response,provisional)
            sha=digest(provisional.read_bytes())
            os.replace(provisional,target)
            write_json(metadata,{'sha256':sha,'seconds':inspect_wav(target)})
    return target

def cached_parts(root,e,model,voice):
    directory=cache_dir(root,e,model,voice); result=[]
    for i in range(5):
        p=directory/f'part-{i}.wav'; meta=directory/f'part-{i}.json'
        if not p.is_file() or not meta.is_file(): raise ValueError(f'Missing chunk {i}; import or generate only missing chunks.')
        if digest(p.read_bytes())!=read_json(meta).get('sha256'): raise ValueError(f'Chunk {i} integrity check failed.')
        inspect_wav(p); result.append(p)
    return result

def bed_gain(t,c):
    duck=10**(-8/20)
    blend=lambda x:duck+(1-duck)*max(0,min(1,x))
    if t<10:
        return max(0,t) if t<1 else 1 if t<9.2 else blend((9.8-t)/.6)
    for start,end in c['gaps']:
        if start<=t<end:
            x=t-start; length=end-start
            return duck if x<.2 else blend((x-.2)/.9) if x<1.1 else 1 if x<length-.8 else blend((length-.2-x)/.6)
    if t>=c['outroStart']:
        if t>=c['fadeStart']: return max(0,(c['duration']-t)/5)
        return blend((t-c['outroStart'])/1.2)
    return duck

def render(parts,bgm,out,credit,bgm_gain=.18,calibration_db=0):
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        raise ValueError('ffmpeg and ffprobe are required.')
    if not math.isfinite(bgm_gain) or not 0<=bgm_gain<=1 or not math.isfinite(calibration_db) or not -30<=calibration_db<=12:
        raise ValueError('Invalid BGM gain.')
    if not isinstance(credit,dict) or not all(credit.get(k) for k in ['title','creator','source','license','changes']):
        raise ValueError('BGM title, creator, source, license and changes are required.')
    if len(parts)!=5: raise ValueError('Exactly five voice files are required.')
    bgm=pathlib.Path(bgm).resolve()
    if not bgm.is_file(): raise ValueError('BGM must be an existing local audio file.')
    out=pathlib.Path(out); out.mkdir(parents=True,exist_ok=True,mode=0o700)
    if any((out/name).exists() for name in ('episode.wav','episode.mp3','mix.json')):
        raise ValueError('Output exists; choose a new directory to preserve previous audio.')
    with tempfile.TemporaryDirectory(dir=out) as temp:
        temp=pathlib.Path(temp); voice=temp/'voice.raw'
        cursor=RATE*10; gaps=[]
        with open(voice,'wb') as dest:
            dest.write(bytes(cursor*2*4))
            for i,p in enumerate(parts):
                inspect_wav(p)
                raw=run(['ffmpeg','-v','error','-protocol_whitelist','file,pipe','-i',str(p),'-ar',str(RATE),'-ac','2','-f','f32le','pipe:1'])
                if len(raw)%8: raise ValueError('Decoded speech is misaligned.')
                dest.write(raw); cursor+=len(raw)//8
                if i<4:
                    gaps.append([cursor/RATE,cursor/RATE+5]); dest.write(bytes(RATE*5*8)); cursor+=RATE*5
            outro=cursor/RATE; dest.write(bytes(RATE*18*8)); cursor+=RATE*18
        cues={'introEnd':10,'gaps':gaps,'outroStart':outro,'duration':cursor/RATE,'fadeStart':cursor/RATE-5}
        music=temp/'music.raw'
        # Loop decoded samples in the filter graph. Demuxer-level -stream_loop drops encoder-delay samples per
        # iteration for MP3/AAC sources, so the bed would end short of the required duration.
        run(['ffmpeg','-v','error','-protocol_whitelist','file,pipe','-i',str(bgm),'-af',f"aloop=loop=-1:size=2147483647,atrim=end={cues['duration']}",'-ar',str(RATE),'-ac','2','-f','f32le',str(music)])
        mix=temp/'mix.raw'; peak=0.0; frame=0; factor=bgm_gain*10**(calibration_db/20)
        with open(voice,'rb') as v,open(music,'rb') as b,open(mix,'wb') as output:
            while raw:=v.read(4096*8):
                vr=array.array('f'); vr.frombytes(raw); br=array.array('f'); br.frombytes(b.read(len(raw)))
                if sys.byteorder!='little': vr.byteswap(); br.byteswap()
                if len(br)!=len(vr): raise ValueError('BGM ended unexpectedly.')
                for j in range(0,len(vr),2):
                    gain=factor*bed_gain(frame/RATE,cues)
                    for k in (j,j+1):
                        vr[k]+=br[k]*gain
                        if not math.isfinite(vr[k]): raise ValueError('Nonfinite audio sample.')
                        peak=max(peak,abs(vr[k]))
                    frame+=1
                if sys.byteorder!='little': vr.byteswap()
                output.write(vr.tobytes())
        headroom=min(1,.95/peak) if peak else 1
        comment=f"{credit['title']} — {credit['creator']}; {credit['source']}; {credit['license']}; {credit['changes']}"
        for suffix,codec in [('wav',['-c:a','pcm_s16le']),('mp3',['-c:a','libmp3lame','-b:a','192k'])]:
            command=['ffmpeg','-v','error','-f','f32le','-ar',str(RATE),'-ac','2','-i',str(mix),'-af',f'volume={headroom}',*codec,'-metadata',f'comment={comment}',str(temp/f'episode.{suffix}')]
            run(command)
        info=json.loads(run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(temp/'episode.wav')]))
        if abs(float(info['format']['duration'])-cues['duration'])>.001: raise ValueError('Rendered duration mismatch.')
        for suffix in ('wav','mp3'):
            os.chmod(temp/f'episode.{suffix}',0o600)
            os.replace(temp/f'episode.{suffix}',out/f'episode.{suffix}')
        (out/'credits.txt').write_text('\n'.join(f'{k}: {v}' for k,v in credit.items())+'\n',encoding='utf-8')
        os.chmod(out/'credits.txt',0o600)
        write_json(out/'mix.json',{'cues':cues,'peakBeforeSafetyGain':peak,'safetyGain':headroom,'bgmGain':bgm_gain,'calibrationDb':calibration_db,'credit':credit})
    return cues

def dry_run(out):
    out=pathlib.Path(out); out.mkdir(parents=True,exist_ok=True,mode=0o700)
    with tempfile.TemporaryDirectory(dir=out) as temp:
        temp=pathlib.Path(temp); parts=[]
        for i in range(5):
            p=temp/f'{i}.wav'
            with wave.open(str(p),'wb') as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000)
                samples=array.array('h',(int(1600*math.sin(2*math.pi*(300+i*40)*n/24000)) for n in range(6000)))
                if sys.byteorder!='little': samples.byteswap()
                w.writeframes(samples.tobytes())
            parts.append(p)
        credit={'title':'Synthetic test tones','creator':'Generated locally','source':'Local mathematical sine waves','license':'No external music used','changes':'Mixed, looped, ducked, and faded; test fixture only'}
        result=render(parts,parts[0],out,credit)
        write_json(out/'dry-run.json',{'syntheticOnly':True,'paidRequests':0,'duration':result['duration']})
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__); sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('validate'); p.add_argument('episode')
    p=sub.add_parser('dry-run'); p.add_argument('--out',required=True)
    for command in ('import-response','import-wav','prepare','reserve','mix'):
        p=sub.add_parser(command); p.add_argument('--episode',required=True); p.add_argument('--cache',required=True); p.add_argument('--model',required=True); p.add_argument('--voice',required=True)
        if command in ('import-response','import-wav','reserve'):
            p.add_argument('--chunk',type=int,required=True)
            if command=='import-response': p.add_argument('--response',required=True)
            elif command=='import-wav': p.add_argument('--wav',required=True)
            else: p.add_argument('--retry-unknown',action='store_true')
        elif command=='prepare': p.add_argument('--out',required=True)
        else:
            p.add_argument('--bgm',required=True); p.add_argument('--credit',required=True); p.add_argument('--out',required=True); p.add_argument('--bgm-gain',type=float,default=.18); p.add_argument('--calibration-db',type=float,default=0)
    a=parser.parse_args()
    if a.command=='validate': result=validate_episode(read_json(a.episode))
    elif a.command=='dry-run': result=dry_run(a.out)
    elif a.command=='import-response': result={'cachedFile':str(cache_import(a.cache,read_json(a.episode),a.model,a.voice,a.chunk,read_json(a.response)))}
    elif a.command=='import-wav': result={'cachedFile':str(cache_import(a.cache,read_json(a.episode),a.model,a.voice,a.chunk,wav_path=a.wav))}
    elif a.command=='reserve': result=reserve(a.cache,read_json(a.episode),a.model,a.voice,a.chunk,a.retry_unknown)
    elif a.command=='prepare': result=prepare(a.cache,read_json(a.episode),a.model,a.voice,a.out)
    else:
        e=read_json(a.episode); result=render(cached_parts(a.cache,e,a.model,a.voice),a.bgm,a.out,read_json(a.credit),a.bgm_gain,a.calibration_db)
        write_json(pathlib.Path(a.out)/'episode.json',e)
        pathlib.Path(a.out,'script.txt').write_text('\n\n'.join(e['segments']),encoding='utf-8')
        os.chmod(pathlib.Path(a.out,'script.txt'),0o600)
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':
    try: main()
    except (ValueError,OSError,KeyError,TypeError,EOFError,wave.Error) as exc:
        print(f'Error: {exc}',file=sys.stderr); sys.exit(1)
