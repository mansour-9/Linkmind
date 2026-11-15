"""Bounded source discovery and revision-aware authorization of source suggestions."""
import re
from difflib import SequenceMatcher
from uuid import UUID

from app.db import sql
from app.retrieval import ACCESS
from app.source_access import CATALOG_VERSION

STOP_WORDS = set("a an the is are there any have has do does i me we you can could please find locate look looking for show list file files document documents pdf source sources called call named name mention mentions mentioning about contain contains what which where who tell this that it one use second first third and of in on to with عندك فيه في وين ابحث دور ملف ملفات مستند عن هذا هذه هو هي هل ممكن ابي ابغى وش ايش ما اسم اسمه يسمى الاول الثاني الثالث".split())


def words(text):
    return re.findall(r"[^\W_]+", text.casefold(), re.UNICODE)


def terms(text):
    return list(dict.fromkeys(w for w in words(text) if w not in STOP_WORDS and len(w)>1))[:12]


def title_score(query, filename):
    needles=terms(query)
    title=words(filename.rsplit(".",1)[0])
    if not needles or not title:
        return 0.0
    scores=[max(1.0 if token==needle else SequenceMatcher(None,needle,token).ratio()
                for token in title) for needle in needles]
    # A single acronym or distinctive partial name can locate a long filename.
    return sum(scores)/len(scores)


# A never-published upload is discoverable as a file even before parsing succeeds.


def candidates(conn,viewer,query,document_ids=None,limit=6):
    needles=terms(query)
    if not needles:
        return []
    # Bigrams admit transpositions/misspellings without scanning an unlimited catalog.
    patterns=list(dict.fromkeys("%"+token[i:i+2]+"%" for token in needles
        for i in range(len(token)-1)))[:100]
    params={**viewer.access(),"patterns":patterns,"query":"%"+" ".join(needles)+"%"}
    where=ACCESS+" AND "+CATALOG_VERSION
    if document_ids:
        where+=" AND d.id=ANY(:scope)"
        params["scope"]=[UUID(str(id)) for id in document_ids]
    rows=sql(conn,f"""SELECT d.id AS document_id,v.id AS version_id,v.filename,
        v.search_ready_at IS NOT NULL AS search_ready
        FROM documents d JOIN document_versions v ON v.document_id=d.id
        WHERE {where} AND lower(v.filename) LIKE ANY(:patterns)
        ORDER BY (v.filename ILIKE :query) DESC,v.created_at DESC,d.id LIMIT 200""",**params).mappings()
    ranked=[]
    for row in rows:
        score=max(title_score(token,row.filename) for token in needles)
        if score>=0.68:
            ranked.append({**dict(row),"match":"filename" if score>=0.98 else "similar_name","score":score})
    return sorted(ranked,key=lambda row:(-row["score"],row["filename"],str(row["document_id"])))[:limit]


def public_matches(rows):
    return [{key:str(row[key]) if key in {"document_id","version_id"} else row[key]
             for key in ("document_id","version_id","filename","search_ready","match")} for row in rows]


def identity_choices(conn,viewer,query):
    """Unconfirmed same-name identities require context, not an automatic merge."""
    needles=[token for token in terms(query) if len(token)>=3 and token not in {"project","person","team","system","owner","owns","status","deadline"}]
    if not needles:
        return []
    rows=sql(conn,f"""SELECT DISTINCT e.canonical_id,e.name,e.kind,d.id AS document_id,
        v.id AS version_id,v.filename,v.search_ready_at IS NOT NULL AS search_ready,
        EXISTS(SELECT 1 FROM entity_identifiers i WHERE i.canonical_id=e.canonical_id
            AND i.value<>'' AND position(lower(i.value) in lower(:query))>0) AS identified
        FROM live_entities e JOIN document_versions v ON v.id=e.version_id
        JOIN documents d ON d.id=v.document_id
        WHERE {ACCESS} AND d.current_version_id=v.id AND e.kind IN ('person','project','team','system')
        AND lower(e.name) LIKE ANY(:names) ORDER BY e.name,v.filename,e.canonical_id LIMIT 100""",
        **viewer.access(),query=query,names=["%"+word+"%" for word in needles]).mappings().all()
    if any(row.identified for row in rows):
        return []
    groups={}
    for row in rows:
        groups.setdefault((row.kind,tuple(words(row.name))),[]).append(row)
    for group in groups.values():
        if len({row.canonical_id for row in group})>1 and len({row.document_id for row in group})>1:
            docs={str(row.document_id):{**dict(row),"match":"entity_name"} for row in group}
            return public_matches(list(docs.values())[:6])
    return []


def allowed(conn,viewer,matches):
    if not matches:
        return True
    for item in matches:
        try:
            document,version=UUID(str(item["document_id"])),UUID(str(item["version_id"]))
        except (ValueError,KeyError,TypeError):
            return False
        if not sql(conn,f"""SELECT 1 FROM documents d JOIN document_versions v ON v.document_id=d.id
            WHERE {ACCESS} AND {CATALOG_VERSION} AND d.id=:document AND v.id=:version
            AND v.filename=:filename""",**viewer.access(),document=document,version=version,filename=item.get("filename")).first():
            return False
    return True


def ambiguous(matches):
    if len(matches)<2:
        return False
    first,second=matches[:2]
    return (second["score"]>=first["score"]*0.9 and
            SequenceMatcher(None," ".join(words(first["filename"]))," ".join(words(second["filename"]))).ratio()>=0.82)


def choose(question,matches,explicit=None):
    if explicit:
        return [item for item in matches if str(item["document_id"])==str(explicit)]
    text=" ".join(words(question))
    if text in {"both","both of them","all of them","all","كلاهما","كلهم","الاثنين"}:
        return matches
    if re.search(r"\b(compare|difference)\b|قارن|الفرق",text):
        return matches
    for number,pattern in enumerate((r"\b(first|1)\b|الأول|الاول",r"\b(second|2)\b|الثاني",r"\b(third|3)\b|الثالث")):
        if re.search(pattern,text) and number<len(matches):
            return [matches[number]]
    scores=[title_score(question,item["filename"]) for item in matches]
    best=max(scores,default=0)
    selected=[item for item,score in zip(matches,scores) if score==best and score>=0.8]
    if len(selected)==1:
        return selected
    if len(matches)==1 and text in {"yes","yes please","that one","this one","نعم","ايه","اي","هذا"}:
        return matches
    return []
