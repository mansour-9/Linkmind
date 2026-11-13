"""Source discovery, clarification, and scoped follow-ups without trusting chat as evidence."""
import re
from uuid import UUID

from fastapi import HTTPException
from app import source_discovery as catalog
from app.contracts import GroundedAnswer
from app.conversation_routing import plan
from app.question_intent import intent,needs_selection
from app.retrieval import dependencies_allowed,selected_context


def response(viewer,question,previous,document_ids,engine,search,answer,configured,source_document_id=None):
    scope=dict(org=viewer.organization_id,user=viewer.id)
    matches=[]
    evidence=[]
    coverage=None
    clarification=False
    message=None
    diagnostics={}
    used_previous=False
    previous_matches=previous[0]["response"].get("source_matches",[]) if previous else []

    def authorize_prior():
        with engine.connect() as conn:
            for turn in previous:
                if not dependencies_allowed(conn,viewer,turn["dependency_ids"],turn["response"].get("enrichment_dependencies",[])) or not catalog.allowed(conn,viewer,turn["response"].get("source_matches",[])):
                    raise HTTPException(409,"Source access or versions changed. Ask again.")

    chosen=catalog.choose(question,previous_matches,source_document_id) if previous_matches else []
    if source_document_id and not chosen:
        raise HTTPException(409,"That source choice is no longer available. Search again.")
    quick_matches=[]
    if (not chosen and not document_ids and intent(question)=="search" and len(catalog.words(question))<=3
            and not re.search(r"\b(who|what|when|why|how|owner|status|deadline|date)\b|مين|متى|كيف|وش|ايش",question.casefold())):
        with engine.connect() as conn:
            quick_matches=catalog.candidates(conn,viewer,question,document_ids)
    if chosen:
        routing=dict(route="document_overview",query=question,use_previous=True,planning="local")
        # A choice can include a factual follow-up, e.g. 'the second one, who owns it?'.
        if not source_document_id and re.search(r"\b(who|when|why|deadline|owner|status|compare|difference)\b|مين|متى|ليش|الموعد|قارن|الفرق",question.casefold()):
            routing=dict(route="answer",query=question,use_previous=True,planning="local")
    elif quick_matches and (re.fullmatch(r"[A-Z][A-Z0-9_-]{2,30}[?!؟ ]*",question.strip())
            or re.search(r"\.(pdf|docx|txt|md)\s*[?!؟]*$",question.strip(),re.IGNORECASE)):
        routing=dict(route="find_sources",query=question,use_previous=False,planning="local")
    else:
        routing=plan(question,previous,scope,authorize_prior)
    route=routing["route"]
    used_previous=routing["use_previous"] and bool(previous)
    effective_scope=document_ids
    if chosen:
        effective_scope=[UUID(item["document_id"]) for item in chosen]
        matches=chosen
        used_previous=True
    elif routing["use_previous"] and previous_matches:
        if len(previous_matches)==1:
            effective_scope=[UUID(previous_matches[0]["document_id"])]
            matches=previous_matches
            used_previous=True
        elif route not in {"help","greeting","social"} and previous[0]["response"].get("clarification"):
            matches=previous_matches
            clarification=True
            message="Which source do you mean? Choose one below, describe it, or say ‘both’."
        elif route not in {"help","greeting","social"}:
            effective_scope=[UUID(item["document_id"]) for item in previous_matches]
            matches=previous_matches
            used_previous=True

    if not message and route in {"greeting","help","social"}:
        message=routing["reply"]
        matches=[]
    elif not message and route=="find_sources":
        with engine.connect() as conn:
            found=catalog.candidates(conn,viewer,routing["query"],effective_scope)
        if found:
            matches=catalog.public_matches(found)
        else:
            passages=search(viewer,routing["query"],effective_scope,diagnostics=diagnostics)
            related={}
            for passage in passages:
                id=str(passage["document_id"])
                if id not in related and len(related)<6:
                    related[id]=dict(document_id=id,version_id=str(passage["version_id"]),filename=passage["filename"],
                        search_ready=True,match="content" if any(term in passage["text"].casefold() for term in catalog.terms(routing["query"])) else "related")
            matches=list(related.values())
        clarification=len(matches)>1
        message=("I found these possible source matches. Which one do you mean? You can also say ‘both’." if clarification
            else "I found a possible source match. Choose it below or ask a follow-up." if matches
            else "I couldn't find a matching source in your current scope. Try describing its topic, check Focus sources, or add it in Data Sources.")
    elif not message and route=="document_overview" and effective_scope:
        evidence,coverage=selected_context(viewer,effective_scope)
        question="Summarize what the selected source documents are about, using only the supplied passages. "+question
        if coverage["partial"]:
            question+=" The supplied passages cover only part of the selected sources; do not claim a complete document review."
        if not evidence:
            message="The selected source is not search ready yet. Check Processing and try again."
    elif not message and route=="document_overview" and not any(t['response'].get('evidence') for t in previous) and needs_selection(question):
        message="Select a document with Focus sources, or describe the topic or source you want explained."
    elif not message:
        with engine.connect() as conn:
            found=catalog.candidates(conn,viewer,routing["query"],effective_scope)
        compare=bool(re.search(r"\b(compare|both|all|difference|across|each)\b|قارن|كل|كلاهما|الفرق",question.casefold()))
        with engine.connect() as conn:
            identities=catalog.identity_choices(conn,viewer,routing["query"]) if not effective_scope and not compare else []
        if identities:
            matches=identities
            clarification=True
            message="This name appears in several sources, and I can't confirm they refer to the same person or item. Which source do you mean? You can also ask to compare them."
        elif not effective_scope and catalog.ambiguous(found) and not compare:
            matches=catalog.public_matches(found)
            clarification=True
            message="Several similarly named sources could fit. Which do you mean? You can choose a source or say ‘both’."
        else:
            evidence=search(viewer,routing["query"],effective_scope,diagnostics=diagnostics)
            if not evidence and effective_scope:
                evidence,coverage=selected_context(viewer,effective_scope)
            elif not evidence and len(found)==1:
                matches=catalog.public_matches(found)
                evidence,coverage=selected_context(viewer,[found[0]["document_id"]])

    if routing["use_previous"] and previous and not message and not effective_scope:
        used_previous=True
        byid={p["id"]:p for p in evidence+previous[0]["response"].get("evidence",[])[:4]}
        evidence=list(byid.values())
    dependencies={p["id"] for p in evidence}
    if used_previous and not message:
        dependencies.update(id for turn in previous for id in turn["dependency_ids"])
    dependencies=sorted(dependencies)
    generations={(str(p["version_id"]),p.get("enrichment_version_id")) for p in evidence}
    if used_previous and not message:
        generations.update((item["source_version_id"],item.get("generation_id")) for turn in previous
            for item in turn["response"].get("enrichment_dependencies",[]))
    generation_dependencies=[dict(source_version_id=source,generation_id=generation) for source,generation in sorted(generations,key=str)]

    def authorize():
        with engine.connect() as conn:
            if not dependencies_allowed(conn,viewer,dependencies,generation_dependencies) or not catalog.allowed(conn,viewer,matches):
                raise HTTPException(409,"Source access or versions changed. Ask again.")
    authorize()
    if not message and not evidence:
        message=("Source search is temporarily limited because semantic search is unavailable. Try a distinctive topic or part of a filename."
            if diagnostics.get("semantic_status") in {"failed","unavailable"} and configured()
            else "I couldn't retrieve supporting passages in your current scope. Try a related topic, check Focus sources, or add a source.")
    result=GroundedAnswer(statements=[],insufficient_evidence=False) if message else answer(question,
        [dict(id=p["id"],text=p["text"],filename=p["filename"],locator=p["locator"],entities=p.get("entities",[])) for p in evidence],scope,
        history=[{"question":t["question"],"statements":t["response"].get("statements",[])} for t in reversed(previous)] if used_previous else [],authorize=authorize)
    result={**result.model_dump(),"evidence":evidence,"provider":"system" if message else "bedrock" if configured() else "mock-extractive"}
    if generation_dependencies:
        result["enrichment_dependencies"]=generation_dependencies
    if message:
        result["message"]=message
    if matches:
        result["source_matches"]=matches
        result["clarification"]=clarification
    if coverage:
        result["coverage"]=coverage
    if diagnostics.get("semantic_status")=="failed":
        result["search_notice"]="Semantic search is temporarily unavailable; available text and filename matches were used."
    return result,dependencies
