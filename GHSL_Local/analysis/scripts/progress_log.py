"""Keep the human-readable progress report and command history synchronized."""
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import fcntl
import json
import re

PROJECT=Path(__file__).resolve().parents[2]
REPORTS=PROJECT/'analysis/reports'


def update(command,outcome,detail='',history=True):
    stamp=datetime.now(ZoneInfo('Asia/Kolkata')).isoformat()
    with (REPORTS/'progress_report.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        checkpoint=PROJECT/'integration/data/national_run1/progress.json'
        completed=len(json.loads(checkpoint.read_text())) if checkpoint.exists() else 0
        if history:
            with (REPORTS/'COMMAND_LOG.md').open('a') as f:
                f.write(f'\n## {stamp}\n\n**Command:** {command}  \n**Outcome:** {outcome}  \n{detail}\n')
        phase='phase 3 (weeks 6–8)' if (PROJECT/'phase2/_SUCCESS').exists() else 'phase 2 (weeks 4–5), followed by phase 3'
        p=REPORTS/'PROGRESS_REPORT.md';text=p.read_text()
        section=(f'### Latest activity\n\n**Updated:** {stamp}  \n'
                 f'**Latest command:** {command}  \n**Outcome:** {outcome}  \n'
                 f'{detail}\n\n**Integration coverage:** {completed} of 168 original tile-year jobs verified. User-approved scope excludes the 12 R8_C27 jobs; accepted target is 156. '
                 f'Current work: {phase}. Full project completion requires all stages to pass.\n\n')
        text=re.sub(r'### Latest activity\n.*?(?=### 1\. Overall status)',lambda m:section,text,flags=re.S)
        text=re.sub(r'\*\*In progress — \d+ of 168 jobs complete\*\*',f'**In progress — {completed} of 168 jobs complete**',text)
        text=re.sub(r'The first of \*\*168 planned national processing jobs\*\* has passed validation\.',
                    f'**{completed} of 168 planned national processing jobs** have passed validation.',text)
        text=re.sub(r'\*\*\d+ of 168 planned national processing jobs\*\* have passed validation\.',
                    f'**{completed} of 168 planned national processing jobs** have passed validation.',text)
        text=re.sub(r'First national tile/year validated; \d+ jobs remain\.',f'{completed} national tile/year jobs validated; {168-completed} jobs remain.',text)
        text=re.sub(r'National completion remains \d+ of 168 jobs until further checkpoints pass\.',
                    f'National completion is {completed} of 168 jobs at the latest checkpoint.',text)
        if '### 1. Overall status' not in text:
            final_activity=(f'### Latest post-completion activity\n\nUpdated: {stamp}  \n'
                            f'{command}: **{outcome}**. {detail}\n\n')
            if '### Latest post-completion activity' in text:
                text=re.sub(r'### Latest post-completion activity\n.*?(?=\n# |\Z)',lambda m:final_activity,text,flags=re.S)
            else:text=final_activity+text
        tmp=p.with_suffix('.md.tmp');tmp.write_text(text);tmp.replace(p)

    # Keep user-visible dialogue synchronized without putting tool payloads in it.
    import importlib.util
    spec=importlib.util.spec_from_file_location("ghsl_conversation_archive",PROJECT/"analysis/scripts/archive_conversation.py")
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    sync=module.sync
    try:
        sync()
    except (OSError,RuntimeError) as exc:
        import warnings
        warnings.warn("Conversation archive was not refreshed: "+str(exc),RuntimeWarning)
