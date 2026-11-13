"""Build a deterministic fictional company corpus and exact-byte mock records."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).parent / "company_demo"
PROJECTS = [
    ("atlas", "Atlas", "Lina Faris", "lina", "Platform", "2026-12-03"),
    ("beacon", "Beacon", "Omar Nasser", "omar", "Customer Success", "2026-12-10"),
    ("cedar", "Cedar", "Maya Hassan", "maya", "Data", "2026-12-17"),
    ("delta", "Delta", "Samir Haddad", "samir", "Operations", "2027-01-07"),
    ("ember", "Ember", "Noor Saleh", "noor", "Security", "2027-01-14"),
]


def main():
    ROOT.mkdir(exist_ok=True)
    fixtures = []

    def document(slug, title, visibility="team", revision_of=None):
        lines = ["# Northstar Labs (synthetic) — " + title, "This is fictional demonstration data."]
        item = dict(key=slug, filename=slug + ".md", title=title, visibility=visibility,
                    revision_of=revision_of, entities=[], claims=[], relationships=[])

        def line(text):
            lines.append(text)
            return len(lines)

        def entity(key, kind, name, number, identifiers=()):
            if not any(e["key"] == key for e in item["entities"]):
                item["entities"].append(dict(key=key, kind=kind, name=name, line=number,
                    identifiers=[dict(namespace=ns, value=value) for ns, value in identifiers]))

        def claim(key, predicate, value, number):
            item["claims"].append(dict(entity_key=key, predicate=predicate, value=value, line=number,
                asserted_by=None, effective_from=None, effective_to=None))

        def edge(subject, predicate, target, number):
            item["relationships"].append(dict(source_key=subject, predicate=predicate, target_key=target, line=number))

        def finish():
            data=("\n".join(lines)+"\n").encode("utf-8")
            (ROOT/item["filename"]).write_bytes(data)
            item["sha256"]=hashlib.sha256(data).hexdigest()
            fixtures.append(item)

        return line, entity, claim, edge, finish

    for slug, name, owner, email, team, deadline in PROJECTS:
        key="NS-"+slug.upper()
        team_url="https://northstar.example/teams/"+slug
        for kind in ("charter", "handover", "decision", "status"):
            line, entity, claim, edge, finish = document(slug+"-"+kind, name+" "+kind)
            owner_name, owner_email = ("Lina Faris", "lina") if slug=="beacon" and kind=="status" else (owner,email)
            number=line(f"Project {name} (project key {key}) is owned by {owner_name} ({owner_email}@northstar.example).")
            entity("project","project","Project "+name,number,[("project_key",key)])
            entity("owner","person",owner_name,number,[("email",owner_email+"@northstar.example")])
            claim("project","owner",owner_name,number)
            edge("project","owned_by","owner",number)
            if kind=="charter":
                number=line(f"Project {name} ({key}) is managed by the {team} team ({team_url}).")
                entity("team","team",team,number,[("url",team_url)])
                edge("project","managed_by","team",number)
                number=line(f"Project {name} ({key}) plans to launch on {deadline}.")
                claim("project","launch_date",deadline,number)
                line(f"The objective of {key} is a reliable {team.lower()} knowledge handover for internal employees.")
            elif kind=="handover":
                issue=key+"-01"
                number=line(f"Task {issue}, Validate {name} handover, belongs to project {key} and is assigned to {owner_name} ({owner_email}@northstar.example).")
                entity("task","task","Validate "+name+" handover",number,[("issue_key",issue)])
                edge("task","part_of","project",number)
                edge("task","assigned_to","owner",number)
                number=line(f"Task {issue} is due on {deadline}.")
                claim("task","deadline",deadline,number)
                line(f"The handover checklist for {key} requires an owner, evidence links, a rollback procedure and a support contact.")
            elif kind=="decision":
                decision_url=f"https://northstar.example/decisions/{slug}-d1"
                number=line(f"Decision {key}-D1 ({decision_url}) approves PostgreSQL for project {key}.")
                entity("decision","decision",name+" database decision",number,[("url",decision_url)])
                claim("decision","decision","Use PostgreSQL for "+key,number)
                edge("decision","part_of","project",number)
                number=line(f"Project {key} uses PostgreSQL (https://northstar.example/technology/postgresql).")
                entity("database","technology","PostgreSQL",number,[("url","https://northstar.example/technology/postgresql")])
                edge("project","uses","database",number)
                line("The reason is compatibility with existing tools and a tested restore procedure.")
            else:
                number=line(f"Project {name} ({key}) status is Pilot in progress, reported on 2026-11-12.")
                claim("project","status","Pilot in progress",number)
                line(f"Project {key} has an unresolved dependency on the security review before launch.")
                if slug=="beacon":
                    line("This status note disagrees with the Beacon charter about ownership. Both sources must be inspected; no approved resolution is recorded.")
            finish()

    line, entity, claim, edge, finish=document("company-onboarding","Employee onboarding")
    n=line("The Northstar Labs onboarding guide (https://northstar.example/policies/onboarding) requires a manager introduction, equipment check and security training.")
    entity("guide","document","Northstar onboarding guide",n,[("url","https://northstar.example/policies/onboarding")])
    claim("guide","requirements","Manager introduction, equipment check and security training",n)
    line("A new employee should complete security training in the first five working days.")
    finish()
    line, entity, claim, edge, finish=document("company-leave-policy","Leave policy / سياسة الإجازات")
    n=line("The Northstar leave policy (https://northstar.example/policies/leave) provides 25 working days of annual leave.")
    entity("policy","document","Northstar leave policy",n,[("url","https://northstar.example/policies/leave")])
    claim("policy","annual_leave","25 working days",n)
    line("سياسة الإجازات في الشركة الافتراضية: الإجازة السنوية 25 يوم عمل، ويجب التنسيق مع المدير.")
    finish()
    line, entity, claim, edge, finish=document("company-people","People and teams")
    for slug,name,person,email,team,deadline in PROJECTS:
        n=line(f"{person} ({email}@northstar.example) leads the {team} team (https://northstar.example/teams/{slug}).")
        entity(email,"person",person,n,[("email",email+"@northstar.example")])
        entity(slug,"team",team,n,[("url",f"https://northstar.example/teams/{slug}")])
        edge(email,"leads",slug,n)
    finish()
    line, entity, claim, edge, finish=document("ember-private-budget","Ember confidential budget",visibility="private")
    n=line("Project Ember (project key NS-EMBER) has a confidential approved budget of USD 42000.")
    entity("project","project","Project Ember",n,[("project_key","NS-EMBER")])
    claim("project","budget","USD 42000",n)
    line("This owner-only source must not appear in another user's results, graph details or answers.")
    finish()
    line, entity, claim, edge, finish=document("atlas-handover-revision","Atlas revised handover",revision_of="atlas-handover")
    n=line("Task NS-ATLAS-01, Validate Atlas handover, belongs to Project Atlas (project key NS-ATLAS) and is assigned to Lina Faris (lina@northstar.example).")
    entity("project","project","Project Atlas",n,[("project_key","NS-ATLAS")])
    entity("owner","person","Lina Faris",n,[("email","lina@northstar.example")])
    entity("task","task","Validate Atlas handover",n,[("issue_key","NS-ATLAS-01")])
    edge("task","assigned_to","owner",n)
    edge("task","part_of","project",n)
    n=line("Task NS-ATLAS-01 is now due on 2026-12-08. This replaces the earlier handover deadline only; the charter launch plan is a separate statement.")
    claim("task","deadline","2026-12-08",n)
    finish()
    questions = [
        dict(question="Who owns NS-ATLAS?",expected="Lina Faris",sources=["atlas-charter"]),
        dict(question="When does NS-CEDAR plan to launch?",expected="2026-12-17",sources=["cedar-charter"]),
        dict(question="Who is assigned to NS-DELTA-01?",expected="Samir Haddad",sources=["delta-handover"]),
        dict(question="What is the deadline for NS-EMBER-01?",expected="2027-01-14",sources=["ember-handover"]),
        dict(question="Which database does NS-ATLAS use?",expected="PostgreSQL",sources=["atlas-decision"]),
        dict(question="What is the status of NS-CEDAR?",expected="Pilot in progress",sources=["cedar-status"]),
        dict(question="Do the NS-BEACON sources agree about its owner?",expected="The charter says Omar Nasser; the status note says Lina Faris. Ownership is unresolved.",sources=["beacon-charter","beacon-status"]),
        dict(question="Who leads the Security team?",expected="Noor Saleh",sources=["company-people"]),
        dict(question="How much annual leave does Northstar provide?",expected="25 working days",sources=["company-leave-policy"]),
        dict(question="كم عدد أيام الإجازة السنوية؟",expected="25 يوم عمل",sources=["company-leave-policy"]),
        dict(question="What must a new employee complete during onboarding?",expected="Manager introduction, equipment check and security training",sources=["company-onboarding"]),
        dict(question="What is this document about?",expected="A cited overview of the selected handover, including its owner and checklist",sources=["atlas-handover"],mode="selected-document"),
        dict(question="What is the private NS-EMBER budget?",expected="USD 42000 for Amal; unavailable to Omar",sources=["ember-private-budget"],mode="permissions"),
        dict(question="What changed after the Atlas handover revision?",expected="Task deadline changes from 2026-12-03 to 2026-12-08; old evidence remains historical",sources=["atlas-handover"],mode="revision"),
        dict(question="What is Northstar's approved acquisition date?",expected="Insufficient evidence; no acquisition date is given",sources=["company-onboarding"],mode="missing-evidence"),
    ]
    manifest=dict(name="Northstar Labs",description="Fictional company: 24 initial documents, five projects, people, policies, disagreement and an owner-only budget.",
        synthetic=True,fixtures=fixtures,questions=questions)
    (ROOT/"manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    (ROOT/"your-addition.txt").write_text("Fictional user addition: Project NS-ATLAS has a support drill on 2026-12-15.\n",encoding="utf-8")
    print(json.dumps({"initial_documents":sum(not f["revision_of"] for f in fixtures),"revision_samples":1,"questions":len(questions)}))


if __name__=="__main__":
    main()
