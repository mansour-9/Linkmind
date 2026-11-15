"""Source discovery, clarification, and scoped follow-ups without trusting chat as evidence."""
import re
from uuid import UUID

from fastapi import HTTPException
from app import source_discovery as catalog
from app.contracts import GroundedAnswer
from app.conversation_routing import plan
from app.question_intent import intent,needs_selection
from app.retrieval import dependencies_allowed,selected_context
from app.retrieval_coordinator import QuestionRetriever
from app.query_language import arabic,people_question,historical_question,operational_question,explain
from app import repository


def response(viewer,question,previous,document_ids,engine,search,answer,configured,source_document_id=None):
    scope=dict(org=viewer.organization_id,user=viewer.id)
    matches=[]
    evidence=[]
    coverage=None
    clarification=False
    message=None
    diagnostics={}
    used_previous=False
    retriever=QuestionRetriever(viewer,search)
    historical_dependencies=[]
    outcome=None
    previous_matches=previous[0]["response"].get("source_matches",[]) if previous else []

    def authorize_prior():
        with engine.connect() as conn:
            for turn in previous:
                if not dependencies_allowed(conn,viewer,turn["dependency_ids"],turn["response"].get("enrichment_dependencies",[]),turn['response'].get('historical_dependencies',[])) or not catalog.allowed(conn,viewer,turn["response"].get("source_matches",[])):
                    raise HTTPException(409,"Source access or versions changed. Ask again.")

    chosen=catalog.choose(question,previous_matches,source_document_id) if previous_matches else []
    if source_document_id and not chosen:
        raise HTTPException(409,"That source choice is no longer available. Search again.")
    routing_scope=document_ids
    if not chosen and not document_ids and intent(question)=='search':
        with engine.connect() as conn:
            project=repository.project_scope(conn,viewer,question)
        if project['ambiguous']:
            message=explain(question,'project_scope')
            clarification=True
        elif project['document_ids'] is not None:
            routing_scope=project['document_ids']
            if not routing_scope:
                message=explain(question,'project_empty')
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
        routing=plan(question,previous,scope,authorize_prior,routing_scope)
    route=routing["route"]
    used_previous=routing["use_previous"] and bool(previous)
    effective_scope=routing_scope
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
            message=explain(question,'choose_source')
        elif route not in {"help","greeting","social"}:
            effective_scope=[UUID(item["document_id"]) for item in previous_matches]
            matches=previous_matches
            used_previous=True

    if not message and route=='clarify':
        message='من تقصد تحديدًا؟ حدّد الشخص أو المصدر حتى ما أنسب مسؤوليات لشخص آخر.' if arabic(question) else 'Who do you mean? Specify the person or source so I do not attribute responsibilities to the wrong person.'
        clarification=True
    elif not message and historical_question(question):
        if not effective_scope:
            message=explain(question,'history_scope')
            outcome='history_scope'
        else:
            evidence,coverage,historical_dependencies=retriever.history(effective_scope,question)
            if len({d['document_id'] for d in historical_dependencies})<len(set(map(str,effective_scope))):
                message=explain(question,'no_history')
                outcome='no_history'
    elif not message and route in {"greeting","help","social"}:
        message=routing["reply"]
        matches=[]
    elif not message and route=="find_sources":
        with engine.connect() as conn:
            found=catalog.candidates(conn,viewer,routing["query"],effective_scope)
        if found:
            matches=catalog.public_matches(found)
        else:
            passages=retriever.search(routing["query"],effective_scope,diagnostics=diagnostics,neighbors=False)
            related={}
            for passage in passages:
                id=str(passage["document_id"])
                if id not in related and len(related)<6:
                    related[id]=dict(document_id=id,version_id=str(passage["version_id"]),filename=passage["filename"],
                        search_ready=True,match="content" if any(term in passage["text"].casefold() for term in catalog.terms(routing["query"])) else "related")
            matches=list(related.values())
        clarification=len(matches)>1
        message=explain(question,'found_sources' if clarification else 'found_source' if matches else 'no_source')
    elif not message and route=="document_overview" and effective_scope:
        evidence,coverage=retriever.context(effective_scope)
        question="Summarize what the selected source documents are about, using only the supplied passages. "+question
        if coverage["partial"]:
            question+=" The supplied passages cover only part of the selected sources; do not claim a complete document review."
        if not evidence:
            message=explain(question,'not_ready')
    elif not message and route=="document_overview" and not any(t['response'].get('evidence') for t in previous) and needs_selection(question):
        message=explain(question,'select_source')
    elif not message:
        with engine.connect() as conn:
            found=catalog.candidates(conn,viewer,routing["query"],effective_scope)
        compare=bool(re.search(r"\b(compare|both|all|difference|across|each)\b|قارن|كل|كلاهما|الفرق",question.casefold()))
        with engine.connect() as conn:
            identities=catalog.identity_choices(conn,viewer,routing["query"]) if not effective_scope and not compare else []
        if identities:
            matches=identities
            clarification=True
            message=explain(question,'identity_scope')
        elif not effective_scope and catalog.ambiguous(found) and not compare:
            matches=catalog.public_matches(found)
            clarification=True
            message=explain(question,'similar_sources')
        else:
            if effective_scope and people_question(question):
                evidence,coverage=retriever.context(effective_scope,question)
            else:
                evidence=retriever.search(routing["query"],effective_scope,diagnostics=diagnostics)
            if not evidence and effective_scope:
                evidence,coverage=retriever.context(effective_scope,question)
            elif not evidence and len(found)==1:
                matches=catalog.public_matches(found)
                evidence,coverage=retriever.context([found[0]["document_id"]],question)

    if routing["use_previous"] and previous and not message and not effective_scope:
        used_previous=True
        byid={p["id"]:p for p in evidence+previous[0]["response"].get("evidence",[])[:4]}
        evidence=list(byid.values())
    evidence=retriever.limits.context(evidence)
    dependencies={p["id"] for p in evidence}|retriever.limits.dependency_ids
    if used_previous and not message:
        dependencies.update(id for turn in previous for id in turn["dependency_ids"])
        historical_dependencies.extend(item for turn in previous for item in turn['response'].get('historical_dependencies',[]))
    historical_dependencies=list({item['passage_id']:item for item in historical_dependencies}.values())
    dependencies=sorted(dependencies)
    generations={(str(p["version_id"]),p["enrichment_version_id"]) for p in evidence if p.get("enrichment_version_id")}
    if used_previous and not message:
        generations.update((item["source_version_id"],item.get("generation_id")) for turn in previous
            for item in turn["response"].get("enrichment_dependencies",[]))
    generation_dependencies=[dict(source_version_id=source,generation_id=generation) for source,generation in sorted(generations,key=str)]

    def authorize():
        with engine.connect() as conn:
            if not dependencies_allowed(conn,viewer,dependencies,generation_dependencies,historical_dependencies) or not catalog.allowed(conn,viewer,matches):
                raise HTTPException(409,"Source access or versions changed. Ask again.")
    authorize()
    if not message and not evidence:
        outcome='no_matches'
        message=(explain(question,'semantic_limited')
            if diagnostics.get("semantic_status") in {"failed","unavailable"} and configured()
            else explain(question,'no_matches'))
    result=GroundedAnswer(statements=[],insufficient_evidence=False) if message else answer(question,
        [dict(id=p["id"],text=p["text"],filename=p["filename"],locator=p["locator"],entities=p.get("entities",[]),revision_role=p.get('revision_role','current')) for p in evidence],scope,
        history=[{"question":t["question"],"statements":t["response"].get("statements",[])} for t in reversed(previous)] if used_previous else [],authorize=authorize)
    failure=getattr(result,'_failure_reason',None)
    if not message and not result.statements:
        outcome=failure or 'evidence_gap'
        message=explain(question,outcome)
    elif result.statements and result.insufficient_evidence:
        outcome='partial'
        message=explain(question,'partial')
    provider='system' if not result.statements and (outcome in {'no_matches','no_history','history_scope'} or not evidence) else 'bedrock' if configured() else 'mock-extractive'
    if route in {'greeting','help','social','find_sources','clarify'} or clarification:
        provider='system'
    result={**result.model_dump(),"evidence":evidence,"provider":provider}
    if outcome:
        result['answer_state']=dict(code=outcome)
    if retriever.limits.activity:
        result['retrieval_activity']=retriever.limits.activity
    if historical_dependencies:
        result['historical_dependencies']=historical_dependencies
    if generation_dependencies:
        result["enrichment_dependencies"]=generation_dependencies
    if message:
        result["message"]=message
    if matches:
        result["source_matches"]=matches
        result["clarification"]=clarification
    elif clarification:
        result['clarification']=True
    if coverage:
        result["coverage"]=coverage
    if diagnostics.get("semantic_status")=="failed":
        result["search_notice"]=explain(question,'semantic_limited')
    if operational_question(question):
        result['freshness_notice']=explain(question,'stored_only')
    return result,dependencies
