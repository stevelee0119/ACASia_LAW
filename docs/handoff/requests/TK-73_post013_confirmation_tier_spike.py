"""Unapproved parallel confirmation tiers; original warnings/grades unchanged."""
import copy
import importlib.util
import json
import re
import unicodedata
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from packages.claim_engine.evidence_consistency import DATE_RE

base=Path(__file__).parent
spec=importlib.util.spec_from_file_location('caption',base/'TK-73_post013_caption_spike.py');s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
spec=importlib.util.spec_from_file_location('role',base/'TK-73_post013_title_confidence_spike.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)


def literal(value):return re.sub(r'\s','',value or '')


def finding_contract(findings):
    snapshots=[]
    for finding in findings:
        snapshot=asdict(finding)
        snapshot.pop('finding_id');snapshot.pop('created_at')
        for evidence in snapshot['evidence']:evidence.pop('evidence_id')
        snapshots.append(snapshot)
    return snapshots


def native_title_certificates(doc,path):
    """Read actual native header/cell occurrences; no expected-title argument."""
    import pdfplumber
    from packages.claim_engine.evidence_consistency import HEADER_KEYS
    originals=s.exhibit_rows(doc);certificates={};by_table={}
    for index,row in enumerate(originals):
        if not row.get('from_lines'):
            by_table.setdefault((row.get('page'),row.get('table_ref')),[]).append((index,row))
    with pdfplumber.open(path) as raw:
        for page_number,page in enumerate(raw.pages,1):
            for table_number,table in enumerate(page.find_tables()):
                cells=table.extract()
                if not cells or not cells[0]:continue
                header=cells[0]
                title_columns=[i for i,value in enumerate(header) if literal(value) in HEADER_KEYS['name']]
                id_columns=[i for i,value in enumerate(header) if literal(value) in HEADER_KEYS['id']]
                if len(title_columns)!=1 or len(id_columns)!=1:continue
                title_column,id_column=title_columns[0],id_columns[0]
                native=[]
                def cell_proof(row_number,column,value):
                    if row_number>=len(table.rows) or column>=len(table.rows[row_number].cells):return None
                    box=table.rows[row_number].cells[column]
                    if not box:return None
                    x0,y0,x1,y1=box
                    chars=[(i,char) for i,char in enumerate(page.chars) if char['x0']>=x0-.1 and char['x1']<=x1+.1 and char['top']>=y0-.1 and char['bottom']<=y1+.1]
                    chars.sort(key=lambda item:(round(item[1]['top'],1),item[1]['x0']))
                    if not chars or literal(''.join(c['text'] for _,c in chars))!=literal(value):return None
                    return {'cell_bbox':list(box),'raw_character_indices':[i for i,_ in chars]}
                header_proof=cell_proof(0,title_column,header[title_column])
                id_header_proof=cell_proof(0,id_column,header[id_column])
                if not header_proof or not id_header_proof:continue
                for row_number,values in enumerate(cells[1:],1):
                    if len(values)<=max(title_column,id_column):native=[];break
                    title=values[title_column];reference=values[id_column]
                    title_proof=cell_proof(row_number,title_column,title)
                    reference_proof=cell_proof(row_number,id_column,reference)
                    if not title_proof or not reference_proof:native=[];break
                    for ref in s.parse_exhibits(reference or ''):
                        native.append((ref,title,reference,row_number,title_proof,reference_proof))
                paired=by_table.get((page_number,f'p{page_number}t{table_number}'),[])
                if len(native)!=len(paired):continue
                pending={}
                # The original parser iterates native table rows then refs. Check
                # every occurrence and key, rather than first matching strings.
                for (index,row),(ref,title,reference,row_number,title_proof,reference_proof) in zip(paired,native):
                    if (row['party'],row['number'],row['branches'])!=(ref['party'],ref['number'],ref['branches']) or literal(row.get('name'))!=literal(title) or literal(row.get('id'))!=literal(reference):pending={};break
                    pending[index]={'complete_title':title,'source_page':page_number,'native_table':table_number,'native_cell':(row_number,title_column),'actual_header':header[title_column],'header_proof':header_proof,'id_header_proof':id_header_proof,'title_proof':title_proof,'reference_proof':reference_proof,'role':'original explicit native TITLE field'}
                certificates.update(pending)
    return certificates


def diagnose(doc,path,title_certificates=None,missing_owner=False):
    rows=s.exhibit_rows(doc);before=copy.deepcopy(rows)
    findings=s.check_exhibits(doc)
    old=[f for f in findings if f.confidence_features.get('rule_id')=='EVI.EVIDENCE_NUMBER_DUPLICATE']
    reading=s.build_reading_text(doc);text=reading.text
    owners=s.source_index(reading,s.native_pieces(doc,path)) if not title_certificates else []
    if missing_owner:
        for index,owner in enumerate(owners):
            if owner and text[index]=='갑':owners[index]=None;break
    mask=s.protection(text);paragraphs=[];offset=0;stack=[];active=None
    for raw in text.split('\n'):
        start=offset+len(raw)-len(raw.lstrip());value=raw.strip();offset+=len(raw)+1
        head=s.HEAD.fullmatch(value)
        if head and not s.parse_exhibits(value) and owners and s.native(text,owners,start,start+len(value)) and not any(mask[start:start+len(value)]):
            rank=0 if head['marker'][0].isdigit() else 1
            while stack and stack[-1]['rank']>=rank:stack.pop()['end']=len(paragraphs)
            active={'index':len(paragraphs),'rank':rank,'parent':tuple(h['index'] for h in stack),'end':None,'inventory':head['title'].endswith('목록') and not s._EXHIBIT_SECTION_HEAD_RE.search(value),'witnesses':set(),'open':True}
            stack.append(active)
        paragraphs.append({'start':start,'text':value,'heading':active})
    by_occurrence={}
    for index,p in enumerate(paragraphs):
        h=p['heading'];start=p['start'];value=p['text'];refs=s.parse_exhibits(value)
        if not h or not refs or refs[0]['span'][0]!=0:continue
        unique={tuple(r['span']):r for r in refs};spans=list(unique)
        for n,span in enumerate(spans):
            ref=unique[span];left,right=start+span[0],start+span[1];end=start+(spans[n+1][0] if n+1<len(spans) else len(value))
            tail=text[right:end];mark=re.match(r'\s*:\s*',tail);content=right+(mark.end() if mark else len(tail)-len(tail.lstrip()))
            complete=bool(owners) and s.native(text,owners,left,right) and s.covered(text,owners,right,end)
            protected=any(mask[left:end]) or any(c in s.BRACKETS or c in s.BRACKETS.values() for c in text[left:end])
            uncertain=any(unicodedata.category(c) in ('Cf','Co','Cs') for c in text[left:end])
            good=complete and not protected and not uncertain
            definition=bool(mark) and good and s.native(text,owners,right,content)
            if h['inventory']:
                if h['open'] and definition:h['witnesses'].add((left,right))
                else:h['open']=False
            delimiters=[i for i in range(content,end) if text[i] in ':：' and not mask[i] and i>content and i+1<end and s.native(text,owners,i-1,i+2)] if owners else []
            record={'heading':h,'value':text[content:end].strip(),'source_complete':good,'colon_shape':bool(delimiters),'reference_span':(left,right),'payload_span':(content,end),'has_date':bool(DATE_RE.search(text[content:end]))}
            for branch in ref['branches'] or [None]:by_occurrence.setdefault((index,span,(ref['party'],ref['number'],branch)),[]).append(record)
    groups={}
    for row_index,row in enumerate(rows):
        for branch in row['branches'] or [None]:
            identity=(row['party'],row['number'],branch);group=row.get('line_group')
            matches=by_occurrence.get((group[0],tuple(group[1]),identity),[]) if group else []
            record=matches[0] if len(matches)==1 else None
            if record and literal(record['value'])!=literal(row.get('name')):record={**record,'source_complete':False}
            groups.setdefault(identity,[]).append((row_index,row,record))
    receipt=[]
    for identity,items in groups.items():
        label=f'{identity[0]} 제{identity[1]}호증'+(f'의 {identity[2]}' if identity[2] else '')
        matching=[f for f in old if f.confidence_features.get('exhibit')==label]
        if not matching:continue
        reason='legacy/global/source fallback';tier='LEGACY_A_RETAINED'
        certs=[title_certificates.get(i) for i,_,_ in items] if title_certificates else []
        if certs and all(certs) and all(literal(c['complete_title'])==literal(row['name']) for c,(_,row,_) in zip(certs,items)) and len({literal(c['complete_title']) for c in certs})>1:
            tier='CONFIRMED_TITLE_A';reason='independent native TITLE cells with distinct complete values'
        elif all(r and r['source_complete'] and not r['has_date'] and not row.get('date') and not row.get('in_section') for _,row,r in items):
            records=[r for _,_,r in items];heads=[r['heading'] for r in records]
            inv=[r for r in records if r['heading']['inventory']];other=[r for r in records if not r['heading']['inventory']]
            same_parent=len({h['parent'] for h in heads})==1
            inv_good=all(h['end'] is not None and len(h['witnesses'])>=2 for h in heads if h['inventory'])
            other_closed=all(h['end'] is not None for h in heads if not h['inventory'])
            # Whole original alternatives remain; neither projection nor clipping.
            if same_parent and inv_good and other_closed and inv and other and len({literal(r['value']) for r in inv})==1 and len({literal(r['value']) for r in other})==1 and all(r['colon_shape'] for r in other):
                tier='PENDING_CANDIDATE';reason='source-complete scoped-inventory/noninventory mixed formatting; formal role unproved'
        receipt.append({'key':identity,'tier':tier,'reason':reason,'original_A_count':len(matching),'original_grades':[getattr(f.evidence_grade,'value',f.evidence_grade) for f in matching],'original_complete_names':[row['name'] for _,row,_ in items],'source_witnesses':[r and {'source_complete':r['source_complete'],'reference_span':r['reference_span'],'payload_span':r['payload_span'],'heading_index':r['heading']['index'],'parent':r['heading']['parent']} for _,_,r in items]})
    assert s.exhibit_rows(doc)==before
    assert finding_contract(s.check_exhibits(doc))==finding_contract(findings)
    assert all(f.evidence_grade=='A' for f in old)
    return {'original_A_findings':len(old),'proposal_tiers':receipt,'original_rows_unchanged':True,'original_findings_unchanged':True,'original_rows':len(rows),'other_original_rule_ids':[f.confidence_features.get('rule_id') for f in findings if f not in old]}


def run(directory):
    results=[]
    for extension in ('txt','pdf','docx'):
        for number,(title,other) in enumerate((('점검기록','점검도면'),('작업대장','작업일지'),('관측도면','관측보고'))):
            for mode in ('same_description','true_unknown_mixed','true_plain','global_prose','global_inventory','cross_parent','protected','missing_owner','recognized','date_guard','branch_unregistered','party_unregistered'):
                first=f'갑 제1호증: {title}, 보관 7쪽 확인 부분.'
                body=f'갑 제1호증 {other if mode in ("true_unknown_mixed","cross_parent") else title}: 순서를 설명한다.'
                if mode=='true_plain':first=f'갑 제1호증: {title}';body=f'갑 제1호증 {other}'
                lines=['1. 자료 제출','가. 공개 자료 목록',first,'을 제2호증: 비교자료, 보관 9쪽 확인 부분.','나. 자료 확인','기본 순서는 여러 단계로 구성되어 있다.','다. 처리 분석',body,'라. 별도 정리','첨부서류']
                if mode=='global_prose':lines.insert(8,f'갑 제1호증 {title}: 경로를 설명한다.')
                if mode=='global_inventory':lines.insert(4,f'갑 제1호증: {title}, 보관 8쪽 다른 부분.')
                if mode=='cross_parent':lines[6]='2. 별도 처리'
                if mode=='protected':lines[2]=f'갑 제1호증: {title} 「7쪽 관찰」';lines[7]=f'갑 제1호증 {other}: 순서를 설명한다.'
                if mode=='recognized':lines[1]='입증방법'
                if mode=='date_guard':lines[2]=f'갑 제1호증: {title} 2025. 2. 30.';lines[7]=f'갑 제1호증 {other} 2025. 3. 4.: 순서를 설명한다.'
                if mode=='branch_unregistered':lines[7]=body.replace('갑 제1호증','갑 제1호증의 1')
                if mode=='party_unregistered':lines[7]=body.replace('갑 제1호증','병 제1호증')
                folder=directory/f'{extension}_{number}_{mode}';folder.mkdir(parents=True,exist_ok=True)
                doc=s.parsed(folder,extension,lines);r=diagnose(doc,folder/('public_caption.'+extension),missing_owner=mode=='missing_owner')
                # Author-intended public semantic oracle is reported after triage;
                # it is never passed to the source-only proposal classifier.
                genuine=mode in ('true_unknown_mixed','true_plain','global_prose','global_inventory','cross_parent','protected','date_guard')
                r.update(format=extension,example=number,mode=mode,public_true_duplicate=genuine,missing_owner_simulation=mode=='missing_owner')
                results.append(r)
    for number,title in enumerate(('점검기록','작업대장','관측도면')):
        names=[title+': 동쪽에 있다.',title+': 서쪽에 있다.']
        folder=directory/f'native_pdf_title_{number}';folder.mkdir(parents=True,exist_ok=True)
        doc,kind=v.table_document(folder,'pdf',[['갑 제1호증',name,'2025. 3. 4.','기재 확인'] for name in names])
        certs=native_title_certificates(doc,folder/'public_title_role.pdf')
        assert len(certs)==2
        assert [row['name'] for row in s.exhibit_rows(doc)]==names
        assert all(row['label']=='갑 제1호증' for row in s.exhibit_rows(doc))
        r=diagnose(doc,folder/'public_title_role.pdf',title_certificates=certs)
        r.update(format='pdf',example=number,mode='native_title',public_true_duplicate=True,actual_title_certificates=list(certs.values()),certificate_source='actual native PDF headers/cell geometry/character occurrences; no expected-title input')
        results.append(r)
    # Fixed public diagnostic expectations, separate from semantic truth labels.
    # These do not edit or replace product/protected test expectations.
    for r in results:
        no_duplicate=r['mode'] in ('branch_unregistered','party_unregistered')
        expected_tier=('CONFIRMED_TITLE_A' if r['mode']=='native_title' else
                       'PENDING_CANDIDATE' if r['mode'] in ('same_description','true_unknown_mixed') else
                       'LEGACY_A_RETAINED')
        assert r['original_A_findings']==(0 if no_duplicate else 1)
        assert [item['tier'] for item in r['proposal_tiers']]==([] if no_duplicate else [expected_tier])
        assert r['original_rows']==(2 if r['mode']=='native_title' else 4 if r['mode'] in ('global_prose','global_inventory') else 3)
        expected_other=[] if r['mode'] in ('native_title','recognized') else ['EVI.EVIDENCE_NUMBERING_GAP']
        if r['mode']=='date_guard':expected_other.insert(0,'EVI.EVIDENCE_DATE_INVALID')
        assert r['other_original_rule_ids']==expected_other
        if expected_tier=='PENDING_CANDIDATE':
            assert all(w and w['source_complete'] for item in r['proposal_tiers'] for w in item['source_witnesses'])
    counters=Counter();transition=[]
    for r in results:
        for item in r['proposal_tiers']:
            truth=r['public_true_duplicate'];tier=item['tier'];counters['original_A']+=item['original_A_count'];counters[tier]+=1
            counters['detected_true' if truth else 'old_A_false_candidates']+=1
            if truth and tier=='PENDING_CANDIDATE':counters['true_moved_pending']+=1
            if not truth and tier=='PENDING_CANDIDATE':counters['false_candidates_pending']+=1
            if truth and tier=='CONFIRMED_TITLE_A':counters['independently_confirmed_true']+=1
            if truth and tier!='PENDING_CANDIDATE':counters['retained_A_true']+=1
            if not truth and tier!='PENDING_CANDIDATE':counters['retained_A_false_candidates']+=1
            transition.append((r['format'],r['mode'],tier,truth))
    print(json.dumps({'records':results,'counters':dict(counters),'transitions':transition},ensure_ascii=False,indent=2));return results


if __name__=='__main__':
    import sys
    run(Path(sys.argv[1]))
