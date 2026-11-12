"""Generate two deterministic, source-cited graph-demo fixtures (never benchmark data)."""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent / "graph_demo"
PROJECTS = [
    ("Atlas", "Amal", "Platform Engineering", "Amazon RDS for PostgreSQL"),
    ("Beacon", "Nadia", "Data Platform", "Amazon OpenSearch Service"),
    ("Cedar", "Omar", "Finance Operations", "Amazon Redshift"),
    ("Delta", "Lina", "Customer Success", "Amazon S3"),
]
PEOPLE = ["Amal", "Omar", "Nadia", "Lina", "Priya", "Sam", "Jonas", "Mira", "Noor", "Rami", "Sara", "Tarek"]
TEAMS = {
    "Platform Engineering": ["Amal", "Omar", "Jonas", "Mira", "Rami"],
    "Data Platform": ["Nadia", "Priya", "Jonas", "Sara"],
    "Finance Operations": ["Omar", "Lina", "Sam"],
    "Customer Success": ["Lina", "Sam", "Noor", "Mira", "Tarek"],
    "Compliance and Trust": ["Priya", "Noor", "Mira"],
    "Knowledge Experience": ["Amal", "Nadia", "Priya", "Rami"],
}
TASKS = [
    ("GD-ATLAS-101 · Migrate customer records", "Amal", "Atlas"),
    ("GD-ATLAS-102 · Validate rollback plan", "Omar", "Atlas"),
    ("GD-BEACON-201 · Index support articles", "Nadia", "Beacon"),
    ("GD-BEACON-202 · Measure search relevance", "Priya", "Beacon"),
    ("GD-CEDAR-301 · Reconcile cost centers", "Omar", "Cedar"),
    ("GD-CEDAR-302 · Audit monthly close", "Lina", "Cedar"),
    ("GD-DELTA-401 · Archive resolved tickets", "Lina", "Delta"),
    ("GD-DELTA-402 · Review retention policy", "Sam", "Delta"),
]
DECISIONS = [
    ("Decision · Retain source files", "Amal", "Atlas", "Compliance and Trust"),
    ("Decision · Launch relevance pilot", "Priya", "Beacon", "Knowledge Experience"),
    ("Decision · Automate close checklist", "Lina", "Cedar", "Finance Operations"),
    ("Decision · Adopt retention tiers", "Sam", "Delta", "Compliance and Trust"),
]
CONTRIBUTIONS = [("Atlas", "Delta"), ("Atlas", "Cedar"), ("Beacon", "Delta"),
                 ("Cedar", "Delta"), ("Atlas", "Beacon"), ("Cedar", "Delta"),
                 ("Atlas", "Beacon"), ("Atlas", "Delta"), ("Beacon", "Delta"),
                 ("Atlas", "Delta"), ("Beacon", "Delta"), ("Cedar", "Delta")]
PHRASES = {"owned_by": "is owned by", "managed_by": "is managed by", "uses": "uses",
           "assigned_to": "is assigned to", "belongs_to": "belongs to", "approved_by": "was approved by",
           "supported_by": "is supported by", "member_of": "is a member of", "leads": "leads",
           "operated_by": "is operated by", "contributes_to": "contributes to", "informs": "informs",
           "collaborates_with": "collaborates with", "advises": "advises"}


def key(name):
    return re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-")


def generate():
    catalog = []
    def entity(kind, name, namespace=None, value=None):
        identifiers = [{"namespace": "url", "value": f"https://graph-demo.linkmind.invalid/{kind}/{key(name)}"}]
        if namespace: identifiers.append({"namespace": namespace, "value": value})
        catalog.append(dict(key=key(name), kind=kind, name=name, identifiers=identifiers))
    for project, *_ in PROJECTS: entity("project", "Project " + project, "project_key", "DEMO-" + project.upper())
    for person in PEOPLE: entity("person", person, "email", person.casefold() + "@demo.linkmind.local")
    for team in TEAMS: entity("team", team)
    for task, *_ in TASKS: entity("task", task, "issue_key", task.split(" · ")[0])
    for decision, *_ in DECISIONS: entity("decision", decision)
    for *_, technology in PROJECTS: entity("technology", technology)
    facts = [[], []]
    def fact(file, source, predicate, target): facts[file].append((source, predicate, target))
    for project, owner, team, technology in PROJECTS:
        for predicate, target in [("owned_by",owner),("managed_by",team),("uses",technology)]: fact(0,"Project "+project,predicate,target)
        fact(0,technology,"operated_by",team)
    for task, owner, project in TASKS:
        fact(0,task,"assigned_to",owner); fact(0,task,"belongs_to","Project "+project)
    for decision, owner, project, team in DECISIONS:
        for predicate,target in [("approved_by",owner),("belongs_to","Project "+project),("supported_by",team)]: fact(0,decision,predicate,target)
    for team, members in TEAMS.items():
        for person in members: fact(0,person,"member_of",team)
    for person, team in [("Amal","Platform Engineering"),("Nadia","Data Platform"),("Omar","Finance Operations"),("Lina","Customer Success"),("Priya","Compliance and Trust")]: fact(0,person,"leads",team)
    for person, projects in zip(PEOPLE, CONTRIBUTIONS):
        for project in projects: fact(1,person,"contributes_to","Project "+project)
    for left,right in [(0,3),(1,2),(2,3)]: fact(1,DECISIONS[left][0],"informs",DECISIONS[right][0])
    for left,right in [("Platform Engineering","Data Platform"),("Data Platform","Knowledge Experience"),("Finance Operations","Customer Success")]: fact(1,left,"collaborates_with",right)
    for team in ["Platform Engineering","Finance Operations"]: fact(1,"Compliance and Trust","advises",team)
    assert len(catalog)==38 and len({e['key'] for e in catalog})==38
    assert [len(f) for f in facts]==[73,32]
    assert len(set(facts[0]+facts[1]))==105
    files={}; fixtures=[]
    for index,(filename,title) in enumerate([("graph-demo-operations.md","Operations knowledge"),("graph-demo-connections.md","Cross-project connections")]):
        lines=[f"# Graph Demo — {title} (synthetic)","","Synthetic demonstration only. These fictional records are not company facts.",""]
        if index: lines += ["This second source connects shared demo people, projects, teams and decisions.",""]
        lines += ["## Entity directory", ""]
        occurrences=[]
        for e in catalog:
            ids="; ".join(i['namespace']+": "+i['value'] for i in e['identifiers'])
            lines.append(f"{e['name']} is a synthetic {e['kind']}; {ids}.")
            occurrences.append({**e,"line":len(lines)})
        lines += ["", "## Supported relationships", ""]
        relationships=[]
        for source,predicate,target in facts[index]:
            lines.append(f"{source} {PHRASES[predicate]} {target}.")
            relationships.append(dict(source_key=key(source),target_key=key(target),predicate=predicate,line=len(lines)))
        fixtures.append(dict(filename=filename,entities=occurrences,claims=[],relationships=relationships))
        files[filename]="\n".join(lines)+"\n"
    manifest=dict(version=2,description="Clearly labeled synthetic graph demo; independent of benchmark expectations.",
                  entity_count=38,entity_occurrence_count=76,relationship_count=105,fixtures=fixtures)
    files['manifest.json']=json.dumps(manifest,indent=2,ensure_ascii=False)+"\n"
    return files


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    for name,content in generate().items():
        path=ROOT/name
        if args.check:
            if not path.exists() or path.read_bytes()!=content.encode('utf-8'): raise SystemExit(f"Stale generated fixture: {name}")
        else:
            ROOT.mkdir(parents=True,exist_ok=True);path.write_bytes(content.encode('utf-8'))
    print('Verified 38 canonical entities, 76 cited occurrences and 105 relationships.' if args.check else 'Generated 38 canonical entities, 76 cited occurrences and 105 relationships.')
