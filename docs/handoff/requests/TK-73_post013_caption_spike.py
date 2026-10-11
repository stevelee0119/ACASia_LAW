"""Public capability only: no product patch or finding suppression."""
import copy
import json
import re
import time
import unicodedata
from pathlib import Path

from packages.claim_engine.evidence_consistency import check_exhibits, exhibit_rows, _EXHIBIT_SECTION_HEAD_RE
from packages.claim_engine.exhibits import parse_exhibits
from packages.document_engine.reading_text import SPACE_MAP, build_reading_text
from packages.document_engine.registry import parse_document
from scripts.audit.corpus import build_pdf

BRACKETS = {'《': '》', '〈': '〉', '(': ')', '[': ']', '{': '}', '<': '>', '「': '」', '『': '』', '【': '】', '“': '”', '‘': '’', '"': '"', "'": "'"}
HEAD = re.compile(r'(?P<marker>\d{1,2}\.|[가-하]\.)\s+(?P<title>[^.!?。！？]+)$')
PARTICLE = re.compile(r'(?:으로|에서|에게|로|에|을|를|은|는|이|가|와|과)\s+')
COORD = re.compile(r'(?<!\d)\d{1,4}(?:\s*[-–—~∼〜]\s*\d{1,4})?\s*(?:페이지|쪽|행)')
ENDINGS = ('니다', '한다', '된다', '했다', '였다', '이다', '있다', '없다', '었다', '았다', '해요', '어요', '아요')


def key(text):
    return ''.join(unicodedata.normalize('NFKC', text).split())


def native_pieces(doc, path):
    """Native text-codepoint/PDF extraction origins; never attrs.lines text proof."""
    extension = path.suffix
    if extension == '.pdf':
        import pdfplumber
        originals = []
        with pdfplumber.open(path) as raw:
            for page_number, page in enumerate(raw.pages, 1):
                for char_index, char in enumerate(page.chars):
                    originals.append((page_number, char_index, char))
        out = {}
        for page in doc.pages:
            for block in page.blocks:
                if block.bbox is None:
                    out[block.block_id] = []
                    continue
                box = block.bbox
                chars = [(index, c) for number,index,c in originals if number == block.page
                         and c['x0'] >= box.x0-0.1 and c['x1'] <= box.x1+0.1
                         and c['top'] >= box.y0-0.1 and c['bottom'] <= box.y1+0.1]
                chars.sort(key=lambda v:(round(v[1]['top'],1),v[1]['x0']))
                lines=[]
                for index,char in chars:
                    if not lines or abs(char['top']-lines[-1][0]) > 2.5:
                        lines.append((char['top'], []))
                    lines[-1][1].extend((value,('pdf_extraction',block.page,index,sub))
                                        for sub,value in enumerate(char['text']))
                out[block.block_id] = [line[1] for line in lines]
        return out
    if extension == '.txt':
        raw = path.read_text(encoding='utf-8')
        lines=[];absolute=0
        for index,line in enumerate(raw.splitlines(keepends=True)):
            if line.strip():
                lines.append([(value,('txt_codepoint',index,absolute+position))
                              for position,value in enumerate(line.rstrip('\r\n'))])
            absolute += len(line)
    else:
        from zipfile import ZipFile
        from xml.etree import ElementTree as ET
        with ZipFile(path) as archive:
            xml = ET.fromstring(archive.read('word/document.xml'))
        ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        lines=[]
        for paragraph_index,paragraph in enumerate(xml.findall('.//w:body/w:p',ns)):
            value=[]
            for run_index,node in enumerate(paragraph.findall('.//w:t',ns)):
                value.extend((char,('ooxml_text_codepoint',paragraph_index,run_index,index))
                             for index,char in enumerate(node.text or ''))
            lines.append(value)
    # Forward native occurrence assignment. attrs.lines supplies only cardinality,
    # and exact lexical equality below must validate that tentative assignment.
    out={};cursor=0
    for page in doc.pages:
        for block in page.blocks:
            count=len(block.attributes.get('lines') or [None])
            out[block.block_id]=lines[cursor:cursor+count]
            cursor += count
    return out

def source_index(reading, originals):
    """Linear lexical projection; joins have no original glyph owner."""
    owners = [None] * len(reading.text)
    blocks = {}
    for segment in reading.segments:
        block = segment.block
        if block.block_id not in blocks:
            pieces = originals.get(block.block_id, [])
            raw_lines = [''.join(v[0] for v in piece) for piece in pieces]
            raw_origins = [[v[1] for v in piece] for piece in pieces]
            original = [(char, (block.block_id, line, position))
                        for line, value in enumerate(raw_lines) for position, char in enumerate(value) if not char.isspace()]
            shown = [(position, char) for position, char in enumerate(block.text) if not char.isspace()]
            mapped = [None] * len(block.text)
            if len(original) == len(shown) and all(a[0] == b[1] for a, b in zip(original, shown)):
                for (char, owner), (position, _) in zip(original, shown):
                    mapped[position] = (*owner, char, raw_origins[owner[1]][owner[2]])
                # Native spaces are proved only between adjacent same-line glyphs.
                prior = None
                for position, owner in enumerate(mapped):
                    if owner is None:
                        continue
                    if prior is not None:
                        previous_position, previous = prior
                        if previous[:2] == owner[:2]:
                            raw_gap = raw_lines[owner[1]][previous[2]+1:owner[2]]
                            display_gap = block.text[previous_position+1:position]
                            if raw_gap.translate(SPACE_MAP) == display_gap:
                                for offset, char in enumerate(raw_gap):
                                    mapped[previous_position+1+offset] = (owner[0], owner[1], previous[2]+1+offset, char, raw_origins[owner[1]][previous[2]+1+offset])
                    prior = (position, owner)
            blocks[block.block_id] = mapped
        mapped = blocks[block.block_id]
        leading = len(block.text) - len(block.text.lstrip())
        for position in range(segment.start, segment.end):
            local = leading + position - segment.start
            if local < len(mapped):
                owner = mapped[local]
                if owner and owner[3].translate(SPACE_MAP) == reading.text[position]:
                    owners[position] = owner
    return owners


def covered(text, owners, start, end):
    return start < end and all(char.isspace() or owners[index] is not None
                              for index, char in enumerate(text[start:end], start))


def native(text, owners, start, end):
    values = owners[start:end]
    return bool(values) and all(values) and all(a[:2] == b[:2] and a[2]+1 == b[2]
                                              for a, b in zip(values, values[1:]))


def protection(text):
    stack, mask = [], bytearray(len(text)+1)
    for index, char in enumerate(text):
        mask[index] = bool(stack)
        folded = unicodedata.normalize('NFKC', char)
        token = folded if len(folded) == 1 and folded in set(BRACKETS) | set(BRACKETS.values()) else char
        if token != char and (token in BRACKETS or token in BRACKETS.values()):
            mask[index] = True
        if stack and token == stack[-1]:
            stack.pop()
        elif stack and stack[-1] in ('"', "'", '”', '’', '」', '』'):
            pass
        elif token in BRACKETS:
            stack.append(BRACKETS[token])
    mask[-1] = bool(stack)
    return mask


def finite(text):
    value = text.strip()
    return bool(value) and value[-1] in '.!。！' and value[:-1].rstrip().endswith(ENDINGS)


def complete_identity(text):
    value = key(text)
    return value[:-1] if len(value) > 1 and value[-1] in '.!。！' and value[-2] not in '.!?。！？' else value


def capability(doc, path):
    """Return candidate certificates separately from unchanged product findings."""
    rows = exhibit_rows(doc)
    before = copy.deepcopy(rows)
    reading = build_reading_text(doc)
    originals = native_pieces(doc, path)
    text, owners = reading.text, source_index(reading, originals)
    mask = protection(text)
    paragraphs, offset = [], 0
    for raw in text.split('\n'):
        start = offset + len(raw)-len(raw.lstrip())
        value = raw.strip()
        offset += len(raw)+1
        refs = parse_exhibits(value)
        paragraphs.append({'text': value, 'start': start, 'refs': refs})
    headings, stack = {}, []
    for index, par in enumerate(paragraphs):
        match = HEAD.fullmatch(par['text'])
        if not match or par['refs'] or any(mask[par['start']:par['start']+len(par['text'])]):
            continue
        prefix_end = par['start']+match.start('title')
        if not native(text, owners, par['start'], par['start']+len(par['text'])):
            continue
        rank = 0 if match['marker'][0].isdigit() else 1
        while stack and stack[-1]['rank'] >= rank:
            stack.pop()['end'] = index
        heading = {'index': index, 'rank': rank, 'parent': tuple(v['index'] for v in stack),
                   'inventory': match['title'].endswith('목록') and not _EXHIBIT_SECTION_HEAD_RE.search(par['text']), 'end': None,
                   'witnesses': set(), 'witness_open': True}
        headings[index] = heading
        stack.append(heading)
    contexts, active = {}, []
    for index in range(len(paragraphs)):
        if index in headings:
            h = headings[index]
            while active and active[-1]['rank'] >= h['rank']:
                active.pop()
            active.append(h)
        contexts[index] = active[-1] if active else None
    inventories, later_rows, citations, origin_seen = {}, {}, [], set()
    for index, par in enumerate(paragraphs):
        heading = contexts[index]
        if not heading or heading['end'] is None:
            continue
        start, value, refs = par['start'], par['text'], par['refs']
        unique = {tuple(ref['span']): ref for ref in refs}
        leading = refs and refs[0]['span'][0] == 0
        if leading:
            spans = list(unique)
            for item, span in enumerate(spans):
                ref = unique[span]
                left, right = start+span[0], start+span[1]
                end = start+(spans[item+1][0] if item+1 < len(spans) else len(value))
                tail = text[right:end]
                marker = re.match(r'\s*[:：]\s*', tail)
                keys = [(ref['party'], ref['number'], branch) for branch in ref['branches'] or [None]]
                record = {'start': right, 'end': end, 'tail': tail, 'reference_span': (left,right),
                          'source': native(text,owners,left,right) and not any(mask[left:right]) and covered(text,owners,right,end),
                          'heading': heading, 'definition': marker and native(text,owners,right,right+marker.end()),
                          'content_start': right+marker.end() if marker else right+len(tail)-len(tail.lstrip())}
                if heading['inventory']:
                    if record['source'] and record['definition'] and heading['witness_open']:
                        heading['witnesses'].add((left, right))
                    else:
                        heading['witness_open'] = False
                for identity in keys:
                    origin_seen.add((left, right, identity))
                    (inventories if heading['inventory'] else later_rows).setdefault(identity, []).append(record)
        elif len(unique) == 1 and not heading['inventory'] and finite(value):
            span, ref = next(iter(unique.items()))
            left, right = start+span[0], start+span[1]
            subject = text[start:left].rstrip()
            if not subject.endswith(('은','는','이','가')) or not native(text,owners,left-1,right) or any(mask[start:right]):
                continue
            arg_start = right
            while arg_start < start+len(value) and text[arg_start].isspace():
                arg_start += 1
            particles = [m for m in PARTICLE.finditer(text[arg_start:start+len(value)-1])
                         if not any(mask[arg_start+m.start():arg_start+m.end()])]
            if len(particles) != 1:
                continue
            particle = particles[0]
            boundary, predicate = arg_start+particle.start(), arg_start+particle.end()
            if not native(text,owners,boundary-1,predicate) or not finite(text[predicate:start+len(value)]):
                continue
            if any(c in ':：.!?。！？' and not mask[i] for i,c in enumerate(text[arg_start:boundary],arg_start)):
                continue
            if not covered(text,owners,start,start+len(value)):
                continue
            for branch in ref['branches'] or [None]:
                citations.append({'key': (ref['party'],ref['number'],branch), 'title': text[arg_start:boundary],
                                  'heading': heading, 'span': (start,start+len(value)),
                                  'identity': complete_identity(value)})
    original_unplaced = set()
    for row in rows:
        group = row.get('line_group')
        identities = [(row['party'],row['number'],branch) for branch in row['branches'] or [None]]
        if not row.get('from_lines') or not group or group[0] >= len(paragraphs):
            original_unplaced.update(identities); continue
        par = paragraphs[group[0]]
        bullet = re.match(r'^(\d{1,2}\s*[.)]|[-*•·]\s*|[가-하]\s*[.)]|[①-⑳]\s*)',par['text'])
        consumed = bullet.end() if bullet else 0
        remainder = par['text'][consumed:]
        consumed += len(remainder)-len(remainder.lstrip())
        left,right = (par['start']+consumed+value for value in group[1])
        for identity in identities:
            if (left,right,identity) not in origin_seen or not native(text,owners,left,right):
                original_unplaced.add(identity)
    citations_by_key = {}
    for citation in citations:
        citations_by_key.setdefault(citation['key'],[]).append(citation)
    certificates, reasons = [], []
    for identity, original in inventories.items():
        global_valid = (identity not in original_unplaced
                        and all(v['source'] and v['definition'] and len(v['heading']['witnesses']) >= 2 for v in original)
                        and len({v['identity'] for v in citations_by_key.get(identity,[])}) == 1
                        and len({complete_identity(v['tail']) for v in original}) == 1)
        for citation in citations_by_key.get(identity,[]):
            title = citation['title']
            local = [v for v in original if v['heading']['parent'] == citation['heading']['parent']
                     and v['heading']['rank'] == citation['heading']['rank'] and v['heading']['end'] < citation['heading']['index']]
            body = later_rows.get(identity, [])
            if not global_valid or not local or not body or len({complete_identity(v['tail']) for v in body}) != 1:
                reasons.append('global/source/domain/complete-alternative veto')
                continue
            valid = True
            for entry in local:
                remainder = text[entry['content_start']:entry['end']]
                prefix = re.match(re.escape(title)+r'\s*,\s*',remainder)
                if not prefix or not native(text,owners,entry['content_start']+len(title),entry['content_start']+prefix.end()):
                    valid = False; break
                locator_start = entry['content_start']+prefix.end()
                coordinate = COORD.search(text[locator_start:entry['end']])
                if not coordinate:
                    valid = False; break
                a,b = locator_start+coordinate.start(),locator_start+coordinate.end()
                if b >= entry['end'] or not native(text,owners,a,b+1) or not (text[b].isspace() or unicodedata.category(text[b]).startswith('P')):
                    valid = False; break
            for entry in body:
                remainder = text[entry['start']:entry['end']]
                matched = re.fullmatch(r'(?P<before>\s*'+re.escape(title)+r'\s*[:：]\s*)(?P<predicate>.+)',remainder)
                delimiter_start = entry['start']+len(remainder)-len(remainder.lstrip())+len(title)-1
                if not matched or not finite(matched['predicate']) or not entry['source'] or not native(text,owners,delimiter_start,entry['start']+matched.start('predicate')):
                    valid = False; break
            if valid:
                certificates.append({'key': identity, 'complete_title': title, 'argument_occurrence': citation['span'],
                                     'inventory_occurrences': [(v['start'],v['end']) for v in local],
                                     'all_global_inventory_count': len(original), 'all_global_caption_count': len(body)})
    assert exhibit_rows(doc) == before
    baseline = [f for f in check_exhibits(doc) if f.confidence_features.get('rule_id') == 'EVI.EVIDENCE_NUMBER_DUPLICATE']
    return {'structural_candidates': certificates, 'certificates': [],
            'semantic_role_status': 'UNKNOWN: complete remainder/proposition role proof absent',
            'veto_reasons': reasons, 'original_rows_unchanged': True,
            'rows': len(rows), 'baseline_duplicates': len(baseline), 'reading_segments': len(reading.segments),
            'application_only_characters': sum(v is None for v in owners),
            'native_source_trace': [{'reading_index': i, 'native_origin': v[4], 'character': v[3], 'unicode_category': unicodedata.category(v[3])}
                                    for i,v in enumerate(owners) if v is not None][:8],
            'unplaced_original_keys': len(original_unplaced)}


def parsed(folder, extension, lines):
    path = folder / ('public_caption.'+extension)
    if extension == 'pdf':
        from reportlab.pdfgen import canvas
        from reportlab.pdfbase import pdfmetrics
        from reportlab.lib.pagesizes import A4
        build_pdf({'name':'public font','header':'공개','footer':'합성','body':[('p','공개')]},folder/'font.pdf')
        font = build_pdf.__globals__['FONT']
        out = canvas.Canvas(str(path),pagesize=A4); out.setFont(font,10.5)
        y = 750
        for line in lines:
            assert pdfmetrics.stringWidth(line,font,10.5) <= A4[0]-50
            out.drawString(50,y,line); y -= 20
        out.save()
    elif extension == 'docx':
        from docx import Document
        out=Document()
        for line in lines:
            out.add_paragraph(line)
        out.save(path)
    else:
        path.write_text('\n'.join(lines),encoding='utf-8')
    return parse_document(str(path),document_id='public_caption',filename=path.name,
                          mime_type={'txt':'text/plain','pdf':'application/pdf','docx':'application/vnd.openxmlformats-officedocument.wordprocessingml.document'}[extension],sha256='0'*64)


def run(directory):
    results=[]
    for extension in ('txt','pdf','docx'):
        for example,(title,other) in enumerate((('점검기록','점검보고'),('작업대장','작업도면'),('관측도면','관측보고'))):
            for mode in ('same','different_title','qualified','unit_prefix','format_boundary','global_conflict','fragment_boundary','missing_citation','other_branch','other_parent','prose_conflict','citation_conflict','one_entry','compat_marker','comma_title','colon_title','protected_date','negative_citation','epistemic_citation','opaque_remainder','outer_bookquote','outer_anglequote'):
                if mode=='comma_title': title,other='기록, 여름','기록, 겨울'
                if mode=='colon_title': title,other='기록: 동쪽에 있다.','기록: 서쪽에 있다.'
                if mode=='protected_date': title,other='관측 [2024. 1. 2.]','관측 [2024. 1. 3.]'
                first=f'갑 제1호증: {title}, 전체 확인 범위는 순서와 경로의 모든 관찰 자료로 구성되어 있다'
                second='1. 보관 7쪽 발췌 부분.'
                if mode=='unit_prefix': second='1. 제7행성 탐사.'
                if mode=='format_boundary': second='1. 제7행\u200d성 탐사.'
                if mode=='compat_marker': first=first.replace('호증:', '호증﹕')
                if mode=='opaque_remainder': first=f'갑 제1호증: {title}, 별도 개정 문서·7쪽내용폐기'
                if mode=='qualified': first=first.replace(title,title+' 추가 조건')
                inventory=[first,second,'을 제2호증: 비교자료, 전체 확인 범위는 순서와 경로의 모든 관찰 자료로 구성되어 있다','1. 보관 9쪽 확인 부분.']
                if extension!='pdf': inventory=[first+' '+second,inventory[2]+' '+inventory[3]]
                if mode=='fragment_boundary':
                    inventory=[first,'1. 제7행','성 탐사.']+inventory[2 if extension=='pdf' else 1:]
                if mode=='one_entry': inventory=inventory[:2 if extension=='pdf' else 1]
                if mode=='global_conflict': inventory.append(f'갑 제1호증: {title}, 보관 8쪽 다른 부분.')
                lines=['1. 자료 제출','가. 공개 자료 목록',*inventory,'나. 자료 확인','기본 순서는 여러 단계로 구성되어 있다.','다. 처리 분석']
                if mode=='other_parent': lines[-1]='2. 별도 자료 정의'
                if mode!='missing_citation':
                    label='갑 제1호증의 1' if mode=='other_branch' else '갑 제1호증'
                    ending='확인되지 않았다.' if mode=='negative_citation' else '확인되었는지 알 수 없다.' if mode=='epistemic_citation' else '확인되었다.'
                    lines.append(f'전체 경로는 {label} {title}으로 {ending}')
                lines.append(f'갑 제1호증 {other if mode in ("different_title","comma_title","colon_title","protected_date") else title}: 순서를 설명한다.')
                if mode=='prose_conflict': lines.append(f'갑 제1호증 {title}: 순서를 설명하지 않는다.')
                if mode=='citation_conflict': lines.append(f'전체 경로는 갑 제1호증 {title}으로 확인되지 않았다.')
                lines+=['라. 별도 정리','첨부서류']
                if mode in ('outer_bookquote','outer_anglequote'):
                    opener,closer=('《','》') if mode=='outer_bookquote' else ('〈','〉')
                    lines=[opener]+lines+[closer]
                folder=directory/f'{extension}_{example}_{mode}';folder.mkdir(parents=True,exist_ok=True)
                record=capability(parsed(folder,extension,lines),folder/('public_caption.'+extension))
                record.update(format=extension,example=example,mode=mode,desired_structural_candidate=mode=='same',desired_certificate=False)
                results.append(record)
    print(json.dumps(results,ensure_ascii=False,indent=2))
    return results


if __name__=='__main__':
    import sys
    run(Path(sys.argv[1]))
