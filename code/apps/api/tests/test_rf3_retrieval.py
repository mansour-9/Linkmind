from answer_support import support_verdict
"""Bilingual source-only retrieval, version history and explicit outcome regressions."""
from io import BytesIO
from uuid import UUID

import pytest
from fastapi import HTTPException, UploadFile

from app import main, processing, providers, retrieval
from app.contracts import GroundedAnswer, AnswerVerdict
from app.conversation_routing import plan
from app.db import sql
from app.query_limits import QueryLimits, QueryLimitReached, question_limits
from test_search_readiness import workspace, source, viewer, OMAR


def ready(conn, text, document=None, filename='rf3.md'):
    if document:
        job = main.revision(document, viewer(), UploadFile(BytesIO(text.encode()), filename=filename))
    else:
        item = source(conn, text.encode(), enrichment_requested=False)
        job = main.job(item.id, viewer())
    assert processing.process_one()
    return job


def conversation(documents, user=None):
    return main.create_conversation(main.NewConversation(document_ids=documents), user or viewer())['id']


@pytest.mark.parametrize('question', ['Who are the people and their responsibilities?', 'تقدر تقولي من الاشخاص و المسؤوليات؟', 'وش roles الفريق؟'])
def test_team_context_prioritizes_roles_over_repeated_project_logs(workspace, monkeypatch, question):
    lines = [f'Project Harbor routine log section {i}: shipment updates.' for i in range(40)]
    roles = ['Maya is the Product Manager and owns scope.', 'Ethan is the Operations Lead.', 'Luis is the Integrations Engineer.']
    for position, text in zip([9, 14, 19], roles):
        lines[position] = text
    job = ready(workspace, '\n'.join(lines))
    monkeypatch.setattr(providers, 'structured', lambda *a, **k: pytest.fail('Scoped mock retrieval needs no planner/model'))
    result = main.ask(conversation([job['document_id']]), main.Question(question=question), viewer())
    context = '\n'.join(p['text'] for p in result['evidence'])
    assert all(role in context for role in roles)
    assert result['coverage']['partial'] and result['coverage']['supplied_passages'] <= 24
    assert result['retrieval_activity'][0]['operation'] == 'selected_source_context'
    assert sum(len(p['text']) for p in result['evidence']) <= 22000
    assert sql(workspace, 'SELECT count(*) FROM entities WHERE version_id=:id', id=job['version_id']).scalar() == 0


@pytest.mark.parametrize('question', ['ما اجراءات العمل عن بعد؟', 'إجراءات العمل عن بعد', 'Who reviews remote work requests?'])
def test_arabic_original_text_matches_spelling_and_english_concepts(workspace, question):
    text = 'إِجْرَاءَات العَمَل عن بُعْد: ليلى حسن مسؤولة عن مراجعة الطلبات.'
    job = ready(workspace, text)
    hits = retrieval.search(viewer(), question, [job['document_id']], semantic=False)
    assert hits and hits[0]['text'] == text
    assert main.evidence(UUID(hits[0]['id']), viewer())['quote'] == text


def test_current_answer_never_includes_a_previous_revision_without_explicit_history(workspace):
    job = ready(workspace, 'The release coordinator is Amina.')
    revised = ready(workspace, 'The release coordinator is Daniel.', document=job['document_id'])
    current = main.ask(conversation([job['document_id']]), main.Question(question='Who coordinates the release?'), viewer())
    assert {str(p['version_id']) for p in current['evidence']} == {str(revised['version_id'])}
    old = main.ask(conversation([job['document_id']]), main.Question(question='Compare the previous version with the current version.'), viewer())
    assert {str(p['version_id']) for p in old['evidence']} == {str(job['version_id']), str(revised['version_id'])}
    assert len(old['historical_dependencies']) == 1
    assert old['coverage']['mode'] == 'revision_comparison'


@pytest.mark.parametrize('change', ['revision', 'access', 'deletion'])
def test_historical_answers_reauthorize_sources_and_anchor_revisions(workspace, change):
    job = ready(workspace, 'The release coordinator is Amina.')
    ready(workspace, 'The release coordinator is Daniel.', document=job['document_id'])
    user = viewer(OMAR)
    id = conversation([job['document_id']], user)
    result = main.ask(id, main.Question(question='قارن النسخة السابقة بالحالية.'), user)
    assert result['historical_dependencies'] and not main.history(id, user)['turns'][0]['suppressed']
    forged = [{**result['historical_dependencies'][0], 'document_id': str(UUID(int=42))}]
    assert not retrieval.dependencies_allowed(workspace, user, [p['id'] for p in result['evidence']], historical=forged)
    if change == 'revision':
        ready(workspace, 'The release coordinator is Leila.', document=job['document_id'])
    elif change == 'access':
        main.change_access(job['document_id'], main.AccessChange(visibility='private'), viewer())
    else:
        main.delete(job['document_id'], viewer())
    assert main.history(id, user)['turns'][0]['suppressed']


def test_missing_history_is_explained_without_reconstructing_it(workspace, monkeypatch):
    job = ready(workspace, 'There is one retained source revision.')
    monkeypatch.setattr(main, 'answer', lambda *a, **k: pytest.fail('No absent-history model call'))
    scoped = main.ask(conversation([job['document_id']]), main.Question(question='Compare the previous version.'), viewer())
    assert scoped['answer_state']['code'] == 'no_history' and not scoped['statements']
    unscoped = main.ask(conversation([]), main.Question(question='قارن النسخة السابقة بالحالية.'), viewer())
    assert unscoped['answer_state']['code'] == 'history_scope'


@pytest.mark.parametrize('reason', ['verification_failed', 'citation_failed', 'evidence_gap'])
def test_no_answer_outcomes_keep_the_actual_failure_reason(workspace, monkeypatch, reason):
    job = ready(workspace, 'Evidence exists for this source.')
    def rejected(*args, **kwargs):
        result = GroundedAnswer(statements=[], insufficient_evidence=True)
        result._failure_reason = reason
        return result
    monkeypatch.setattr(main, 'answer', rejected)
    result = main.ask(conversation([job['document_id']]), main.Question(question='تقدر تشرح المسؤوليات؟'), viewer())
    assert result['answer_state']['code'] == reason and result['evidence'] and not result['statements']
    assert any('\u0600' <= c <= '\u06ff' for c in result['message'])
    assert 'Try a different question or add a source' not in result['message']


def test_partial_verified_answer_has_partial_explanation_instead_of_empty_answer_copy(workspace, monkeypatch):
    job = ready(workspace, 'Ethan reviews warehouse exceptions.')
    def partial(question, passages, *args, **kwargs):
        p = passages[0]
        return GroundedAnswer(statements=[dict(text='Ethan reviews warehouse exceptions.', evidence=[dict(passage_id=p['id'], quote=p['text'])])], insufficient_evidence=True)
    monkeypatch.setattr(main, 'answer', partial)
    result = main.ask(conversation([job['document_id']]), main.Question(question='List all responsibilities and approved costs.'), viewer())
    assert result['answer_state']['code'] == 'partial' and result['statements']
    assert 'only part' in result['message']


def test_adjacent_passages_keep_literal_original_anchors(workspace):
    job = ready(workspace, 'FirstBoundaryMarker is discussed here.\nThe next line contains the continued explanation.\nA final context line.')
    hits = retrieval.search(viewer(), 'FirstBoundaryMarker', [job['document_id']], semantic=False)
    adjacent = retrieval.adjacent_context(viewer(), hits[:1])
    assert any('continued explanation' in p['text'] for p in adjacent)
    for passage in adjacent:
        assert main.evidence(UUID(passage['id']), viewer())['quote'] == passage['text']
    main.change_access(job['document_id'], main.AccessChange(visibility='private'), viewer())
    assert retrieval.adjacent_context(viewer(OMAR), hits[:1]) == []


def test_selected_scope_and_identifiers_bypass_model_planning(monkeypatch):
    monkeypatch.setattr(providers, 'configured', lambda: True)
    monkeypatch.setattr(providers, 'structured', lambda *a, **k: pytest.fail('No planner for this direct route'))
    for question, selected in [('تقدر تقولي من الاشخاص و المسؤوليات؟', [UUID(int=1)]), ('Who owns HB-42?', []), ('Compare previous version.', [])]:
        assert plan(question, [], {}, lambda: None, selected)['planning'] == 'direct'


def test_arabic_answer_prompt_keeps_verbatim_english_evidence_and_semantic_check(monkeypatch):
    operations = []
    source_text = 'Ethan is the Operations Lead.'
    monkeypatch.setattr(providers, 'configured', lambda: True)
    monkeypatch.setattr(providers, 'record', lambda *a, **k: None)
    def structured(contract, system, payload, scope, operation, *args, **kwargs):
        operations.append(operation)
        if operation == 'answer':
            assert payload['answer_language'] == 'Arabic'
            assert 'Respond in the language' in system and 'exact supporting quotations' in system
            return GroundedAnswer(statements=[dict(text='Ethan هو قائد العمليات.', evidence=[dict(passage_id='p', quote=source_text)])], insufficient_evidence=False)
        return support_verdict(payload,[True])
    monkeypatch.setattr(providers, 'structured', structured)
    assert providers.answer('من المسؤول؟', [dict(id='p', text=source_text)], {}).statements
    assert operations == ['answer', 'answer_verification']


def test_processing_limit_is_actionable_and_saves_no_answer(workspace, monkeypatch):
    job = ready(workspace, 'An authorized source for limit testing.')
    def exhausted(*args, **kwargs):
        raise QueryLimitReached('model_call_limit')
    monkeypatch.setattr(main, 'answer', exhausted)
    id = conversation([job['document_id']])
    with pytest.raises(HTTPException) as exc:
        main.ask(id, main.Question(question='تقدر تشرح المسؤوليات؟'), viewer())
    assert exc.value.status_code == 503 and exc.value.detail['code'] == 'model_call_limit'
    assert main.history(id, viewer())['turns'] == []


def test_followup_cannot_choose_an_arbitrary_person_when_planner_requests_clarification(workspace, monkeypatch):
    job = ready(workspace, 'Maya is a manager. Ethan is an operations lead.')
    id = conversation([job['document_id']])
    main.ask(id, main.Question(question='Who are the people?'), viewer())
    from app import conversational
    monkeypatch.setattr(conversational, 'plan', lambda *a, **k: dict(route='clarify', query='', use_previous=False, planning='model'))
    monkeypatch.setattr(main, 'answer', lambda *a, **k: pytest.fail('Ambiguous pronouns must clarify'))
    response = main.ask(id, main.Question(question='What will he do?'), viewer())
    assert response['clarification'] and response['provider'] == 'system' and not response['statements']


def test_operational_question_discloses_stored_only_sources(workspace):
    job = ready(workspace, 'The recorded pilot status is pending as of 1 November 2026.')
    response = main.ask(conversation([job['document_id']]), main.Question(question='What is the latest status right now?'), viewer())
    assert 'cannot confirm a newly live status' in response['freshness_notice']


def test_english_function_word_does_not_create_an_unrelated_bilingual_hit(workspace):
    job = ready(workspace, 'Both sources disagree; no approved resolution is recorded.')
    assert retrieval.search(viewer(), 'no-such-topic-928374', [job['document_id']], semantic=False) == []
    assert retrieval.search(viewer(), 'approved resolution', [job['document_id']], semantic=False)
