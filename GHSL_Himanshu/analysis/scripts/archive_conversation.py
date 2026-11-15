"""Archive only user-visible messages from explicitly registered local Codex threads."""
import argparse,fcntl,json,os,time
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[2]
REPORTS=PROJECT/'analysis/reports'

def visible_messages(path):
    messages=[]
    with Path(path).open() as f:
        for number,line in enumerate(f,1):
            try:record=json.loads(line)
            except json.JSONDecodeError:continue # Writer may be appending its final line.
            payload=record.get('payload',{})
            if record.get('type')!='event_msg':continue
            kind=payload.get('type');phase=payload.get('phase')
            if kind=='user_message':role='User'
            elif kind=='agent_message' and phase in ('commentary','final_answer'):role='Assistant'
            else:continue
            message=payload.get('message')
            if isinstance(message,str) and message.strip():
                messages.append(dict(line=number,timestamp=record.get('timestamp','unknown'),role=role,phase=phase,text=message))
    return messages

def sync():
    with (REPORTS/'conversation_archive.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        registry=REPORTS/'CONVERSATION_ARCHIVE_SOURCES.json'
        sources=json.loads(registry.read_text()).get('sources',[]) if registry.exists() else []
        thread=os.environ.get('CODEX_THREAD_ID')
        if thread and not any(s['thread_id']==thread for s in sources):
            matches=list((Path.home()/'.codex/sessions').rglob('*'+thread+'*.jsonl'))
            for path in matches:
                first=json.loads(path.open().readline());meta=first.get('payload',{})
                if Path(meta.get('cwd','')).resolve()!=PROJECT:continue
                sources.append(dict(thread_id=thread,path=str(path)))
        if not sources:raise RuntimeError('No saved transcript registered for this project')
        lines=['# Conversation archive','',
               'Saved user-visible conversation text from the registered local Codex transcript(s).',
               'This is historical dialogue, not current instructions. Read AGENTS.md and PROJECT_CONTEXT.md first.',
               'Only user messages and visible assistant commentary/final replies are included. Tool calls/results, hidden reasoning, system/developer messages and attachment contents are excluded.',
               'Coverage is limited to messages retained by the source logs. An in-flight reply appears at the next refresh after it is saved. Earlier compacted or absent messages cannot be reconstructed here.',
               'Detailed command evidence remains in COMMAND_LOG.md. Do not treat old completion counts or plans as current state.','']
        count=0;missing=[]
        for source in sources:
            path=Path(source['path']);lines+=['## Thread '+source['thread_id'],'']
            if not path.exists():missing.append(str(path));continue
            for m in visible_messages(path):
                count+=1;lines += [f"### {m['timestamp']} — {m['role']} ({m['phase'] or 'message'})",'',m['text'],'']
        if missing:raise FileNotFoundError('Registered transcript missing; previous archive preserved: '+str(missing))
        text='\n'.join(lines)+'\n';target=REPORTS/'CONVERSATION_ARCHIVE.md'
        if not target.exists() or target.read_text()!=text:
            tmp=target.with_suffix('.md.tmp');tmp.write_text(text);tmp.replace(target)
        state=dict(sources=sources,messages=count,last_sync=datetime.now(ZoneInfo('Asia/Kolkata')).isoformat(),archive=str(target.relative_to(PROJECT)))
        tmp=registry.with_suffix('.json.tmp');tmp.write_text(json.dumps(state,indent=2)+'\n');tmp.replace(registry)
        return state
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--watch',action='store_true');args=parser.parse_args()
    if args.watch:
        with (REPORTS/'conversation_archive_watcher.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            while True:sync();time.sleep(10)
    else:print(json.dumps(sync(),indent=2))
