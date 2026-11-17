"""Small bilingual retrieval vocabulary. Never changes source text or proves identity."""
import re
import unicodedata


def arabic(text):
    return bool(re.search(r'[\u0600-\u06ff]', text))


def normalize(text):
    text = ''.join(c for c in text if not unicodedata.combining(c) and c != '\u0640')
    return text.translate(str.maketrans('أإآى', 'اااي')).casefold()


CONCEPTS = {
    'people': ['people', 'person', 'roles', 'role', 'responsibilities', 'responsibility', 'stakeholders', 'lead', 'manager', 'engineer', 'sponsor', 'coordinator', 'responsible', 'owns',
               'اشخاص', 'الاشخاص', 'مسؤوليات', 'المسؤوليات', 'مسؤولياتهم', 'فريق', 'الفريق', 'ادوار', 'الادوار'],
    'ownership': ['owner', 'owns', 'managed', 'مسؤول', 'مسؤوله', 'مسؤولية', 'مسؤولة', 'مالك', 'يمتلك'],
    'remote': ['remote', 'work', 'policy', 'بعد', 'العمل', 'سياسة', 'سياسه'],
    'requests': ['requests', 'reviews', 'submitted', 'طلب', 'طلبات', 'الطلبات', 'مراجعة', 'مراجعه', 'التقديم', 'اجراءات'],
    'dates': ['date', 'deadline', 'pilot', 'موعد', 'الموعد', 'تاريخ', 'التاريخ', 'متي'],
}


def search_terms(question):
    from app.source_discovery import terms
    # The simple bilingual index retains English function words that PostgreSQL's
    # English index normally drops. They must not retrieve unrelated passages on
    # their own. The complete original question still reaches ranking/answering.
    original = [normalize(t) for t in terms(question) if t.casefold() not in {'no', 'not', 'such'}]
    stripped = [re.sub(r'^و?ال', '', t) if arabic(t) else t for t in original]
    expanded = list(original + stripped)
    for words in CONCEPTS.values():
        if set(original + stripped) & {normalize(w) for w in words}:
            expanded.extend(normalize(w) for w in words)
    tokens = list(dict.fromkeys(t for t in expanded if re.fullmatch(r'[^\W_]+', t, re.UNICODE)))[:60]
    variants = list(tokens)
    for token in tokens:
        if arabic(token):
            base = re.sub(r'^و?ال', '', token)
            variants.extend((base, 'ال' + base, 'وال' + base))
    return list(dict.fromkeys(variants))[:100]


def people_question(question):
    text = normalize(question)
    return bool(re.search(r'\b(people|responsibilit\w*|stakeholders|roles|team members)\b', text)
                or any(word in text for word in ('اشخاص', 'مسؤوليات', 'ادوار', 'فريق')))


def historical_question(question):
    text = normalize(question)
    return bool(re.search(r'\b(previous|earlier|prior|old) (version|revision)\b', text)
                or 'النسخة السابقة' in text or 'النسخه السابقه' in text)


def operational_question(question):
    return bool(re.search(r'\b(latest|live|now|current|currently)\b|\b(الحالي|الحالية|الحاليه|حاليا|الان|الحين|احدث)\b|اخر تحديث', normalize(question)))


def explain(question, code):
    messages = {
        'no_matches': ("I couldn't retrieve matching evidence in your current scope. Choose a source or add a distinctive project name.",
                       'ما لقيت مقاطع مناسبة داخل نطاق المصادر الحالي. حدّد ملفًا أو أضف اسم المشروع عشان أبحث بدقة أكثر.'),
        'evidence_gap': ("The retrieved passages don't establish an answer to this question. Open the evidence or narrow the requested detail.",
                         'وصلتني مقاطع من المصادر، لكنها ما تكفي لتوثيق المطلوب. تقدر تفتح المراجع أو تحدد المعلومة المطلوبة أكثر.'),
        'verification_failed': ("I found source passages, but the proposed answer did not pass support verification. I haven't presented it as a source fact. Try a narrower question or inspect the cited source context.",
                                'لقيت مقاطع من المصادر، لكن الإجابة المقترحة ما اجتازت التحقق من دعمها بالنص، لذلك ما عرضتها كمعلومة موثّقة. جرّب سؤالًا أضيق أو افتح سياق المصدر.'),
        'citation_failed': ("I retrieved evidence, but couldn't anchor the generated quotations to their exact passages. Open the original passage or ask for one specific detail.",
                            'استرجعت مقاطع، لكن ما قدرت أطابق اقتباسات الإجابة مع مواضعها الأصلية. افتح النص الأصلي أو اسأل عن نقطة محددة.'),
        'partial': ("I could support only part of the request from the supplied evidence. The cited statements below are verified; the remaining details are not established.",
                    'قدرت أوثّق جزءًا من المطلوب فقط. المعلومات المذكورة مع مراجعها مدعومة، وباقي التفاصيل ما قدرت أثبتها من المقاطع المتاحة.'),
        'history_scope': ("Choose the document whose previous and current revisions you want compared. A document's received date alone does not establish when its facts became effective.",
                          'حدّد الملف اللي تبغى أقارن نسخه السابقة والحالية. تاريخ استلام الملف وحده ما يثبت متى صارت معلوماته سارية.'),
        'no_history': ("This source has no earlier searchable revision retained. I can use the current revision, but cannot reconstruct a missing previous version.",
                       'ما فيه نسخة سابقة قابلة للبحث محفوظة لهذا المصدر. أقدر أستخدم النسخة الحالية، لكن ما أقدر أعيد بناء نسخة غير محفوظة.'),
        'semantic_limited': ("Semantic search is unavailable; text and metadata retrieval were used. A missed match does not prove the information is absent.",
                             'البحث الدلالي غير متاح الآن؛ استخدمت النص ومعلومات المصادر. عدم ظهور نتيجة ما يعني بالضرورة أن المعلومة غير موجودة.'),
        'stored_only': ("Only stored sources are connected here. This answer cannot confirm a newly live status.",
                        'المتاح هنا مصادر محفوظة فقط. الإجابة ما تعتبر تأكيدًا مباشرًا للحالة الحالية في الأنظمة الخارجية.'),
        'limit': ("This question reached its processing limit. No unverified answer was saved. Narrow the scope or retry later.",
                  'وصل السؤال لحد المعالجة المسموح. ما حفظت إجابة غير موثّقة. قلّل نطاق السؤال أو جرّب لاحقًا.'),
        'project_scope': ("More than one project or too many documents match this scope. Choose the relevant documents with Focus sources before I combine their information.",
                          'النطاق يطابق أكثر من مشروع أو عددًا كبيرًا من الملفات. حدّد الملفات المناسبة من Focus sources قبل ما أجمع معلوماتها.'),
        'project_empty': ("This project has no searchable documents available to you yet. Add or publish a source, or choose another scope.",
                          'ما فيه ملفات قابلة للبحث متاحة لك تحت هذا المشروع حاليًا. أضف مصدرًا أو حدّد نطاقًا آخر.'),
        'choose_source': ("Which source do you mean? Choose one below, describe it, or say ‘both’.",
                          'أي مصدر تقصد؟ اختر واحدًا، أو وضّحه أكثر، أو قل الاثنين.'),
        'found_sources': ("I found these possible source matches. Which one do you mean? You can also say ‘both’.",
                          'لقيت هذه المصادر المحتملة. أي واحد تقصد؟ تقدر تختار الاثنين أيضًا.'),
        'found_source': ("I found a possible source match. Choose it below or ask a follow-up.",
                         'لقيت مصدرًا محتملًا. اختره أو اسأل سؤالًا عنه.'),
        'no_source': ("I couldn't find a matching source in your current scope. Try describing its topic, check Focus sources, or add it in Data Sources.",
                      'ما لقيت مصدرًا مطابقًا في النطاق الحالي. وضّح موضوعه، أو راجع Focus sources، أو أضفه من Data Sources.'),
        'not_ready': ("The selected source is not search ready yet. Check Processing and try again.",
                      'المصدر المحدد مو جاهز للبحث حتى الآن. راجع Processing وجرّب بعد اكتمال المعالجة.'),
        'select_source': ("Select a document with Focus sources, or describe the topic or source you want explained.",
                          'حدّد ملفًا من Focus sources أو وضّح الموضوع أو المصدر اللي تبغى أشرحه.'),
        'identity_scope': ("This name appears in several sources, and I can't confirm they refer to the same person or item. Which source do you mean? You can also ask to compare them.",
                           'الاسم موجود في أكثر من مصدر، وما أقدر أجزم أنها تشير لنفس الشخص أو الشيء. أي مصدر تقصد؟ أو تقدر تطلب المقارنة بينها.'),
        'similar_sources': ("Several similarly named sources could fit. Which do you mean? You can choose a source or say ‘both’.",
                            'فيه مصادر بأسماء متشابهة ممكن تناسب سؤالك. أي واحد تقصد؟ اختر مصدرًا أو قل الاثنين.'),
    }
    return messages[code][1 if arabic(question) else 0]
