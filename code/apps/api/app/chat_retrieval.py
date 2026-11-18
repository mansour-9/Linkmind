"""Small intent-aware rankings; discovery metadata is never factual evidence."""
import re

STOP=set('what is are the a an and of to for in its it explain give every all who does do which should current main project company please me tell about'.split())

def terms(text):
    return set(re.findall(r'[^\W_]+',text.casefold()))-STOP

def purpose(query):
    q=query.casefold()
    if re.search(r'department|directory|organization|organis|teams|أقسام|اقسام|إدارات|ادارات',q):return 'directory'
    if re.search(r'policy|retention|retain|approved|سياسة|احتفاظ',q):return 'policy'
    if re.search(r'owner|owns|responsib|ownership|مسؤول|يمسك',q):return 'ownership'
    if re.search(r'block|release|readiness|next|beta|إطلاق|عوائق',q):return 'release'
    return 'overview'

HINTS={
    'overview':['overview','scope','purpose','customer portal','product','features','company and teams'],
    'directory':['company and teams','company overview','department directory','operating departments','organization','directory','people directory','department contacts'],
    'policy':['approved','policy','retention','standard','decision'],
    'ownership':['ownership','accountability','scope','overview','register'],
    'release':['release','readiness','gate','blocker','status','plan'],
}

def score(query,title):
    text=title.casefold();kind=purpose(query)
    value=3*len(terms(query)&terms(title))
    value+=sum(7 for hint in HINTS[kind] if hint in text)
    anchors=re.findall(r'\b[A-Z][A-Z0-9_]{1,30}(?:-\d+)?\b',query)
    if anchors:value+=15*sum(bool(re.search(r'\b'+re.escape(k)+r'\b',title,re.I)) for k in anchors)
    if 'department responsibilities' in text and kind!='directory':value-=18
    if kind=='directory' and 'department responsibilities' in text:value-=12
    if kind=='directory' and re.search(r'customer|partner',text) and not re.search(r'customer|partner',query,re.I):value-=12
    if kind=='policy' and re.search(r'draft|proposal|superseded',text):value-=5
    return value

def rank_hits(query,hits):
    return sorted(hits,key=lambda h:(-score(query,h['title']),h['title'].casefold(),h['native_id']))

def pack_passages(passages,max_characters=2400):
    """Pack adjacent tiny source lines without losing their original locators.

    Parsing is shared with uploads and deliberately remains unchanged. Live prose
    should not spend its entire passage allowance on headings and single lines.
    """
    from app.parsers import Passage
    result=[];group=[];size=0
    for passage in passages:
        if group and size+1+len(passage.text)>max_characters:
            result.append(Passage('\n'.join(p.text for p in group),{'parts':[p.locator for p in group]}))
            group=[];size=0
        group.append(passage);size+=len(passage.text)+bool(size)
    if group:result.append(Passage('\n'.join(p.text for p in group),{'parts':[p.locator for p in group]}))
    return result

def select_passages(passages,query,max_characters=12000,max_passages=24):
    """Rank all parsed passages, retaining original positions and whole text."""
    needles=terms(query)
    ranked=sorted(enumerate(passages),key=lambda pair:(
        -len(needles&terms(pair[1].text)),pair[0])) if query else list(enumerate(passages))
    selected=[];used=0
    for index,p in ranked:
        if len(selected)>=max_passages:break
        if used+len(p.text)<=max_characters:
            selected.append((index,p));used+=len(p.text)
    return sorted(selected),len(selected)==len(passages)
