"""Unapproved bounded proposal: no product mutation or warning suppression."""
import copy
import importlib.util
import json
import re
from pathlib import Path

spec=importlib.util.spec_from_file_location('caption',Path(__file__).with_name('TK-73_post013_caption_spike.py'))
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
COORDINATE=re.compile(r'(?P<a>[1-9]\d{0,3})(?:\s*[-–~]\s*(?P<b>[1-9]\d{0,3}))?\s*(?:쪽|페이지|행)[.!。！]?')


def inspect(doc,path):
    rows=s.exhibit_rows(doc);before=copy.deepcopy(rows)
    reading=s.build_reading_text(doc);text=reading.text
    owners=s.source_index(reading,s.native_pieces(doc,path));mask=s.protection(text)
    paragraphs=[];offset=0;active=None;headings=[]
    for raw in text.split('\n'):
        start=offset+len(raw)-len(raw.lstrip());value=raw.strip();offset+=len(raw)+1
        heading=s.HEAD.fullmatch(value)
        if heading and not s.parse_exhibits(value) and s.native(text,owners,start,start+len(value)) and not any(mask[start:start+len(value)]):
            rank=0 if heading['marker'][0].isdigit() else 1
            while headings and headings[-1]['rank']>=rank:headings.pop()['end']=len(paragraphs)
            active={'rank':rank,'index':len(paragraphs),'parent':tuple(h['index'] for h in headings),'end':None,'inventory':heading['title'].endswith('목록') and not s._EXHIBIT_SECTION_HEAD_RE.search(value)}
            headings.append(active)
        paragraphs.append({'start':start,'text':value,'heading':active})
    definitions={};equalities={};unplaced=set();witnesses={};by_occurrence={}
    for index,p in enumerate(paragraphs):
        h=p['heading'];start=p['start'];value=p['text'];refs=s.parse_exhibits(value)
        if not h or h['end'] is None:continue
        unique={tuple(r['span']):r for r in refs}
        if len(unique)==1 and value.count(' = ')==1:
            ref=next(iter(unique.values()));left,right=ref['span'];title,reftext=value.split(' = ')
            if right==len(value) and left==len(title)+3 and title and not s.parse_exhibits(title) and s.native(text,owners,start,start+len(value)) and not any(mask[start:start+len(value)]):
                for branch in ref['branches'] or [None]:equalities.setdefault((ref['party'],ref['number'],branch),[]).append((title,h,(start,start+len(value))))
        if refs and refs[0]['span'][0]==0:
            for n,(span,ref) in enumerate(unique.items()):
                end=list(unique)[n+1][0] if n+1<len(unique) else len(value)
                left,right=start+span[0],start+span[1]
                tail=text[right:start+end];marker=re.match(r'\s*:\s*',tail)
                proof=s.native(text,owners,left,right) and s.covered(text,owners,right,start+end) and not any(mask[left:start+end])
                if h['inventory'] and marker and proof and s.native(text,owners,right,right+marker.end()):witnesses.setdefault(h['index'],set()).add((left,right))
                for branch in ref['branches'] or [None]:
                    identity=(ref['party'],ref['number'],branch)
                    record=(index,span,tail,h,proof,marker,right,start+end)
                    definitions.setdefault(identity,[]).append(record)
                    by_occurrence.setdefault((index,span,identity),[]).append(record)
    for row in rows:
        group=row.get('line_group');identities=[(row['party'],row['number'],b) for b in row['branches'] or [None]]
        for identity in identities:
            matches=by_occurrence.get((group[0],tuple(group[1]),identity),[]) if group else []
            if not row.get('from_lines') or len(matches)!=1 or not matches[0][4]:
                unplaced.add(identity);continue
            record=matches[0]
            native_value=record[2][record[5].end():] if record[3]['inventory'] and record[5] else record[2].strip()
            if s.key(row.get('name',''))!=s.key(native_value):unplaced.add(identity)
    candidates=[]
    for identity,defs in definitions.items():
        eq=equalities.get(identity,[])
        if identity in unplaced or len(eq)!=1:continue
        title,eh,occurrence=eq[0]
        inv=[v for v in defs if v[3]['inventory']];plain=[v for v in defs if not v[3]['inventory']]
        if not inv or not plain or len({s.key(v[2]) for v in inv})!=1:continue
        if any(s.key(v[2])!=s.key(title) for v in plain):continue
        good=True
        for _,_,tail,h,proof,marker,right,end in inv:
            if not proof or not marker or len(witnesses.get(h['index'],[]))<2 or h['parent']!=eh['parent'] or h['rank']!=eh['rank'] or h['end']>=eh['index']:good=False;break
            prefix=marker.group()+title+', '
            if not tail.startswith(prefix) or not s.native(text,owners,right,right+len(prefix)):good=False;break
            remainder=tail[len(prefix):];coordinate=COORDINATE.fullmatch(remainder)
            if not coordinate or not s.native(text,owners,right+len(prefix),end) or coordinate['b'] and int(coordinate['a'])>int(coordinate['b']):good=False;break
        if good:candidates.append({'key':identity,'complete_title':title,'equality_occurrence':occurrence})
    assert s.exhibit_rows(doc)==before
    baseline=[f for f in s.check_exhibits(doc) if f.confidence_features.get('rule_id')=='EVI.EVIDENCE_NUMBER_DUPLICATE']
    return {'candidate_certificates':candidates,'baseline_duplicates':len(baseline),'original_rows_unchanged':True,'rows':len(rows)}


def run(directory):
    out=[]
    for extension in ('txt','pdf','docx'):
        for n,(base_title,location) in enumerate((('점검기록','7쪽.'),('작업대장','3-5페이지.'),('관측도면','12행.'))):
            for mode in ('same','different_title','qualifier','unit_prefix','negative_equality','quoted','global_conflict','missing_equality','other_parent','coordinate_title_difference','date_unknown','compat_equality'):
                title=base_title+', 7쪽' if mode=='coordinate_title_difference' else base_title+' [2024. 1. 2.]' if mode=='date_unknown' else base_title
                loc=location+' 추가 조건' if mode=='qualifier' else '7행성.' if mode=='unit_prefix' else location
                lines=['1. 자료 제출','가. 공개 자료 목록',f'갑 제1호증: {title}, {loc}','을 제2호증: 비교자료, 9쪽.','나. 자료 확인',f'갑 제1호증 {title+" 추가" if mode=="different_title" else base_title if mode=="coordinate_title_difference" else title}','다. 대응 정리']
                if mode=='other_parent':lines[-1]='2. 별도 정리'
                if mode!='missing_equality':lines.append(f'{title} {"≠" if mode=="negative_equality" else "＝" if mode=="compat_equality" else "="} 갑 제1호증')
                if mode=='global_conflict':lines.insert(4,f'갑 제1호증: {title}, 8쪽.')
                lines+=['라. 종료 구역','첨부서류']
                if mode=='quoted':lines=['「']+lines+['」']
                folder=directory/f'{extension}_{n}_{mode}';folder.mkdir(parents=True,exist_ok=True)
                result=inspect(s.parsed(folder,extension,lines),folder/('public_caption.'+extension))
                result.update(format=extension,example=n,mode=mode,expected_candidate=mode=='same')
                out.append(result)
    print(json.dumps(out,ensure_ascii=False,indent=2));return out


if __name__=='__main__':
    import sys
    run(Path(sys.argv[1]))
