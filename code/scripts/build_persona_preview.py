"""Backport only persona behavior to the existing schema-0010 Sonnet preview image."""
import json
from pathlib import Path
import re
import shutil
import subprocess

CODE=Path(__file__).resolve().parents[1]
REPO=CODE.parent
BASE_REF='4028a16'


def run(*args):
    return subprocess.check_output(args,cwd=REPO,text=True,encoding='utf-8')


def replace_once(source,before,after):
    if source.count(before)!=1:
        raise RuntimeError('Legacy persona patch does not match its reviewed source boundary.')
    return source.replace(before,after)


def main():
    schema=run('docker','exec','linkmind-company-sonnet-db-1','psql','-U','brain','-d','brain','-At','-c','SELECT version_num FROM alembic_version;').strip()
    if schema!='0010_test_budget':
        raise RuntimeError('This backport is only for the reviewed schema-0010 preview. Use the normal build after its F1.3 rollout.')
    current=json.loads(run('docker','inspect','linkmind-company-sonnet-api-1'))[0]
    base=current['Image']
    if not re.fullmatch('sha256:[a-f0-9]{64}',base):
        raise RuntimeError('Expected an immutable local image ID.')
    base_tag='linkmind-persona-base-'+base.split(':')[1][:12]+':local'
    subprocess.run(['docker','tag',base,base_tag],check=True)
    folder=REPO/'.local'/'persona-preview-build'
    folder.mkdir(parents=True,exist_ok=True)
    for name in ('assistant_persona.py','question_intent.py','conversation_routing.py'):
        shutil.copyfile(CODE/'apps/api/app'/name,folder/name)
    conversation=run('git','show',BASE_REF+':code/apps/api/app/conversational.py')
    conversation=replace_once(conversation,'from app.conversation_routing import HELP,plan','from app.conversation_routing import plan')
    conversation=conversation.replace('route not in {"help","greeting"}','route not in {"help","greeting","social"}')
    conversation=replace_once(conversation,
        'elif quick_matches and (quick_matches[0]["score"]>=0.98 or any(word.isupper() and len(word)>=4 for word in re.findall(r"\\w+",question))):',
        'elif quick_matches and (re.fullmatch(r"[A-Z][A-Z0-9_-]{2,30}[?!؟ ]*",question.strip())\n            or re.search(r"\\.(pdf|docx|txt|md)\\s*[?!؟]*$",question.strip(),re.IGNORECASE)):')
    conversation=replace_once(conversation,'if not message and route in {"greeting","help"}:','if not message and route in {"greeting","help","social"}:')
    conversation=replace_once(conversation,'message="Hello! Ask about your organization\'s sources, or select a document and ask what it is about." if route=="greeting" else HELP','message=routing["reply"]')
    (folder/'conversational.py').write_text(conversation,encoding='utf-8')
    provider=run('git','show',BASE_REF+':code/apps/api/app/providers.py')
    provider=replace_once(provider,'from app.inference_budget import reserve,settle','from app.inference_budget import reserve,settle\nfrom app.assistant_persona import CONVERSATION_SYSTEM')
    provider=replace_once(provider,'request["inferenceConfig"]["maxTokens"]=512','request["inferenceConfig"]["maxTokens"]=512\n    elif operation=="conversation_verification":\n        request["inferenceConfig"]["maxTokens"]=256')
    provider=replace_once(provider,'result=structured(GroundedAnswer,UNTRUSTED+','result=structured(GroundedAnswer,CONVERSATION_SYSTEM+"\\nSOURCE ANSWERING — MANDATORY GROUNDING\\n"+UNTRUSTED+')
    (folder/'providers.py').write_text(provider,encoding='utf-8')
    names=('assistant_persona.py','question_intent.py','conversation_routing.py','conversational.py','providers.py')
    (folder/'Dockerfile').write_text('FROM '+base_tag+'\nCOPY '+' '.join(names)+' /app/apps/api/app/\n',encoding='utf-8')
    subprocess.run(['docker','build','-t','linkmind-company-sonnet-backend:persona',str(folder)],check=True)
    print(json.dumps(dict(image='linkmind-company-sonnet-backend:persona',base_image_id=base,
        schema_change=False,source_ref=BASE_REF)),flush=True)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
