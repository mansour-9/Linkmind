"""Small deterministic conversation intents; source content never controls routing."""
import re


def intent(question):
    text = re.sub(r"[?!؟.,]+", "", question.casefold()).strip()
    text = " ".join(text.split())
    if text in {"hi", "hello", "hey", "good morning", "good evening", "مرحبا", "مرحباً", "اهلا", "السلام عليكم"}:
        return "greeting"
    if text in {"thanks","thank you","thank u","thx","شكرا","شكرًا","شكراً","يعطيك العافية"}:
        return "social"
    if (text in {"who are you","what is your name","what's your name","are you chatgpt","can you help me","can you help","help me",
                 "مين انت","من انت","وش اسمك","انت مين","ممكن تساعدني","تقدر تساعدني"}
            or re.fullmatch(r"what (?:is )?(?:can you|you can|u can) do(?: (?:for|form) me)?",text)):
        return "help"
    if (re.search(r"^(what|how) (is |does |do |can )?(this |the )?(chat|caht|assistant|linkmind|you)\b.{0,25}\b(do|help|work|use|can)$", text)
            or re.search(r"^(how (do|can) i upload|help me upload|how (do|can) i (use (this |the )?(chat|assistant|linkmind)|add (data|documents|files)))\b", text)
            or text in {"help", "what can you do", "what can i ask", "كيف استخدمك", "وش تقدر تسوي", "وش يسوي الشات", "كيف ارفع ملف"}):
        return "help"
    if (re.search(r"\b(find|locate|look for|looking for|any|there|which|where|list|show).*(file|document|pdf|source)s?\b", text)
            or re.search(r"\b(file|document|pdf).*(called|named|mention|about)\b", text)
            or re.search(r"(فيه|في|وين|ابحث|دور|عندك).*(ملف|مستند)", text)):
        return "find_sources"
    if text in {"what is that", "what is this", "what's this", "what's that", "what is this about",
                "tell me about this", "explain this", "explain that", "what does this mean",
                "ما هذا", "ما هذا الملف", "اشرح هذا", "ما معنى هذا"}:
        return "document_overview"
    if re.search(r"\b(summari[sz]e|summary|overview)\b", text) or any(term in text for term in ("لخص", "لخّص", "ملخص")):
        return "document_overview"
    if re.search(r"\b(what|tell|explain).*(document|file|pdf).*(about|contain|cover)?", text):
        return "document_overview"
    return "search"


def needs_selection(question):
    text=" ".join(re.sub(r"[?!؟.,]+","",question.casefold()).split())
    return text in {"what is that","what is this","what's this","what's that","what is this about",
        "what is this document about","what is this file about","summarize","summarise","summary",
        "summarize this","summarise this","summarize this document","explain this document",
        "tell me about this","explain this","explain that","what does this mean",
        "ما هذا","ما هذا الملف","اشرح هذا","ما معنى هذا","لخص هذا","ملخص"}
