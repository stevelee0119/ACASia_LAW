"""Public role/confidence contrasts; original product and grades unchanged."""
import copy
import importlib.util
import json
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

spec=importlib.util.spec_from_file_location('caption',Path(__file__).with_name('TK-73_post013_caption_spike.py'))
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
HEADER=['호증','서증명','작성일','입증취지']


def table_document(folder,extension,rows):
    path=folder/('public_title_role.'+extension)
    cells=[HEADER]+rows
    if extension=='docx':
        from docx import Document
        out=Document();table=out.add_table(rows=0,cols=4);table.style='Table Grid'
        for row in cells:
            native=table.add_row().cells
            for cell,value in zip(native,row):cell.text=value
        out.save(path)
        with ZipFile(path) as archive:root=ET.fromstring(archive.read('word/document.xml'))
        ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        raw_table=root.find('.//w:tbl',ns)
        observed=[[''.join(node.text or '' for node in cell.findall('.//w:t',ns)) for cell in row.findall('w:tc',ns)] for row in raw_table.findall('w:tr',ns)]
        native_kind='OOXML original table/row/cell/w:t occurrences'
    else:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        s.build_pdf({'name':'public font','header':'공개','footer':'합성','body':[('p','공개')]},folder/'font.pdf')
        font=s.build_pdf.__globals__['FONT']
        out=canvas.Canvas(str(path),pagesize=A4);out.setFont(font,9)
        xs=[30,110,315,400,575];top=730;height=55
        for x in xs:out.line(x,top,x,top-height*len(cells))
        for n in range(len(cells)+1):out.line(xs[0],top-n*height,xs[-1],top-n*height)
        for n,row in enumerate(cells):
            for x,value in zip(xs,row):out.drawString(x+5,top-n*height-25,value)
        out.save()
        import pdfplumber
        with pdfplumber.open(path) as raw:observed=raw.pages[0].extract_tables()[0]
        native_kind='PDF decoded extraction cells bounded by original ruled geometry'
    assert observed==cells,(extension,observed,cells)
    doc=s.parse_document(str(path),document_id='public_title_role',filename=path.name,
                         mime_type='application/pdf' if extension=='pdf' else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',sha256='0'*64)
    return doc,native_kind


def result(doc):
    rows=s.exhibit_rows(doc);before=copy.deepcopy(rows)
    findings=s.check_exhibits(doc)
    duplicate=[f for f in findings if f.confidence_features.get('rule_id')=='EVI.EVIDENCE_NUMBER_DUPLICATE']
    invalid=[f for f in findings if f.confidence_features.get('rule_id')=='EVI.EVIDENCE_DATE_INVALID']
    assert s.exhibit_rows(doc)==before
    return {'rows':rows,'original_rows_unchanged':True,'duplicate_count':len(duplicate),'duplicate_grades':[getattr(f.evidence_grade,'value',f.evidence_grade) for f in duplicate],'invalid_date_count':len(invalid),'invalid_date_grades':[getattr(f.evidence_grade,'value',f.evidence_grade) for f in invalid]}


def run(directory):
    output=[]
    for number,(title,clauses) in enumerate((('점검기록',('동쪽에 있다.','서쪽에 있다.')),('작업대장',('제한된 경로를 나타낸다.','전체 경로를 나타낸다.')),('관측도면',('조건이 맞으면 표시한다.','조건이 맞지 않으면 표시한다.')))):
        payloads=[title+': '+value for value in clauses]
        for mode in ('purpose_only','formal_title','invalid_date'):
            names=[title,title] if mode!='formal_title' else payloads
            purposes=list(clauses) if mode!='formal_title' else ['기재 확인','기재 확인']
            date='2025. 2. 30.' if mode=='invalid_date' else '2025. 3. 4.'
            native=[['갑 제1호증',name,date,purpose] for name,purpose in zip(names,purposes)]
            for extension in ('pdf','docx'):
                folder=directory/f'table_{extension}_{number}_{mode}';folder.mkdir(parents=True,exist_ok=True)
                doc,kind=table_document(folder,extension,native);record=result(doc)
                expected=1 if mode=='formal_title' else 0
                if extension=='pdf':
                    assert len(record['rows'])==2 and [r['name'] for r in record['rows']]==names
                    assert [r['purpose'] for r in record['rows']]==purposes and [r['date'] for r in record['rows']]==[date,date]
                    assert record['duplicate_count']==expected
                    assert not expected or record['duplicate_grades']==['A']
                    assert record['invalid_date_count']==(2 if mode=='invalid_date' else 0)
                    assert mode!='invalid_date' or record['invalid_date_grades']==['A','A']
                    coverage='original product table rows covered'
                else:
                    assert record['rows']==[] and record['duplicate_count']==0 and record['invalid_date_count']==0
                    coverage='RESIDUAL: native table exists; original DOCX exhibits row-free'
                record.update(example=number,mode=mode,format=extension,source_role=kind,native_expected_duplicate=expected,product_coverage=coverage)
                output.append(record)
        # Identical untyped glyphs can encode either intended title/purpose role.
        # Neither interpretation is fabricated into product metadata.
        for extension in ('txt','pdf','docx'):
            folder=directory/f'line_{extension}_{number}';folder.mkdir(parents=True,exist_ok=True)
            lines=['가. 공개 자료 목록',*[f'갑 제1호증 {value}' for value in payloads],'나. 별도 정리','첨부서류']
            record=result(s.parsed(folder,extension,lines))
            assert record['duplicate_count']==1 and record['duplicate_grades']==['A']
            record.update(example=number,mode='untyped_identical_payload',format=extension,source_role='UNKNOWN: line string lacks title/purpose cell ownership',expected_duplicate=1)
            output.append(record)
    print(json.dumps(output,ensure_ascii=False,indent=2));return output


if __name__=='__main__':
    import sys
    run(Path(sys.argv[1]))
