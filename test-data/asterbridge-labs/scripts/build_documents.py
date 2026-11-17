"""Create editable Word business documents from the canonical fictional source records."""
from pathlib import Path
import json, re
from datetime import datetime, timezone
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT=Path(__file__).resolve().parents[1]
def paragraph(doc,text):
    p=doc.add_paragraph()
    parts=re.split(r'(\[[^\]]+\]\(https://[^)]+\))',text)
    for part in parts:
        match=re.fullmatch(r'\[([^\]]+)\]\((https://[^)]+)\)',part)
        if match:
            rel=p.part.relate_to(match[2],'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink',is_external=True)
            link=OxmlElement('w:hyperlink');link.set(qn('r:id'),rel)
            run=OxmlElement('w:r');props=OxmlElement('w:rPr');style=OxmlElement('w:rStyle');style.set(qn('w:val'),'Hyperlink');props.append(style);run.append(props)
            t=OxmlElement('w:t');t.text=match[1];run.append(t);link.append(run);p._p.append(link)
        else:p.add_run(part)
    return p

def main():
    items=json.loads((ROOT/'onedrive/documents.json').read_text(encoding='utf-8'))
    results=[]
    for item in items:
        if item['format']!='docx':continue
        doc=Document();s=doc.sections[0];s.page_width=Inches(8.5);s.page_height=Inches(11)
        s.top_margin=s.bottom_margin=Inches(.72);s.left_margin=s.right_margin=Inches(.8)
        for style_name in ['Normal','Title','Subtitle','Heading 1','Heading 2']:
            style=doc.styles[style_name];style.font.name='Arial';style.font.color.rgb=RGBColor(0,0,0)
            style.paragraph_format.space_after=Pt(6)
        doc.styles['Normal'].font.size=Pt(11)
        doc.styles['Normal'].paragraph_format.line_spacing=1.08
        doc.styles['Title'].font.size=Pt(21)
        doc.styles['Heading 1'].font.size=Pt(13)
        doc.styles['Heading 1'].paragraph_format.space_before=Pt(12)
        doc.styles['Heading 1'].paragraph_format.keep_with_next=True
        doc.add_paragraph(item['title'],style='Title')
        names={x['id']:x['name'] for x in json.loads((ROOT/'organization/employees.json').read_text(encoding='utf-8'))}
        p=doc.add_paragraph('AsterBridge Labs\n'+names[item['owner']]+'\n'+item['report_date']);p.paragraph_format.space_after=Pt(12)
        for heading,text in item['sections']:
            doc.add_paragraph(heading,style='Heading 1');paragraph(doc,text)
        doc.core_properties.title=item['title'];doc.core_properties.author=names[item['owner']]
        doc.core_properties.subject='Fictional enterprise connector evaluation dataset'
        doc.core_properties.created=datetime.fromisoformat(item['report_date']).replace(tzinfo=timezone.utc)
        doc.core_properties.modified=datetime(2026,11,16,tzinfo=timezone.utc)
        target=ROOT/item['path'];target.parent.mkdir(parents=True,exist_ok=True);doc.save(target)
        reopened=Document(target)
        text='\n'.join(p.text for p in reopened.paragraphs)
        assert item['title'] in text and len(text)>550
        assert not re.search(r'local seed|not published|\{\{jira:',text),item['seed_id']
        results.append(dict(seed_id=item['seed_id'],path=item['path'],paragraphs=len(reopened.paragraphs),characters=len(text),structural_check='passed',render_status='pending'))
    (ROOT/'validation').mkdir(exist_ok=True)
    (ROOT/'validation/documents.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(docx=len(results),structural_check='passed')))

if __name__=='__main__':main()
