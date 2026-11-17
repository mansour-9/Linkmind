"""Small source-action intents; normalize wording, never generate source facts."""
import re
from difflib import SequenceMatcher
from app.query_language import normalize

def words(question):
    def fix(token):
        if 5<=len(token)<=9 and max(SequenceMatcher(None,token,w).ratio() for w in ('project','projects'))>=.8:
            return 'projects' if token.endswith('s') else 'project'
        return token
    return ' '.join(fix(t) for t in re.findall(r'[^\W_]+',normalize(question)))

def project_request(question):
    text=words(question)
    projects=bool(re.search(r'\bprojects?\b|المشاريع|مشاريع|المشروعات',text))
    if not projects:return None
    if re.search(r'\b(status|owner|owns|block\w*|delay\w*|why|affect\w*|depend\w*|explain|describe)\b|حاله|حالة|مسؤول|تعطل|تاخر|اشرح',text):return None
    if re.search(r'\b(how (many|may)|count|number of|total)\b|كم|عدد',text):return 'count'
    if re.search(r'\b(list|show|available|see)\b|المتاح|اعرض|الموجود|قصدي|وش|ما هي',text):return 'list'
    if re.search(r'\b(what|which)\b',text) and re.search(r'\bprojects\b',text):return 'list'
    return None

def source_action(question):
    if project_request(question):return True
    text=words(question)
    if re.search(r'\b(how (do|can) i (connect|configure|enable|add)|set up|configuration)\b|كيف.*(اربط|اضيف|افعل)',text):return False
    return bool(re.search(r'\b(jira|confluence)\b|جيرا|كونفلونس',text) and re.search(r'\b(use|check|see|tell|look|search|find|count|show|get|read)\b|استخدم|شوف|ابحث|اعرض|تاكد',text))

def meaningful_previous(previous):
    return [p for p in previous if p['response'].get('retrieval_query') or p['response'].get('evidence') or p['response'].get('source_matches')]
