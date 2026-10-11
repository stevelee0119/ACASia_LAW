"""Separate page-tree/source-stream review; fixed prior diagnostics unchanged."""
import contextlib
import copy
import importlib.util
import io
import json
from collections import Counter
from pathlib import Path

spec=importlib.util.spec_from_file_location('native',Path(__file__).with_name('TK-73_post013_pdf_native_support_spike.py'))
n=importlib.util.module_from_spec(spec);spec.loader.exec_module(n)
m=n.m;s=n.s;t=n.t


def tree_stream_support(path):
    from pypdf import PdfReader
    from pypdf.generic import IndirectObject,ArrayObject,NumberObject,StreamObject
    reasons=[];leaves=[];visited=set();node_count=0;stream_count=0;extracted_page_ids=[]
    try:
        reader=PdfReader(path,strict=True)
        def key(reference):
            if not isinstance(reference,IndirectObject) or reference.pdf is not reader or reference.idnum<=0 or not 0<=reference.generation<=65535:
                raise ValueError('unproved native reference owner/range')
            # The PDFMiner occurrence owner exposes object id, not generation.
            # Do not certify an identity that this application mapping drops.
            if reference.generation!=0:raise ValueError('unsupported native reference generation')
            # Resolution is necessary in addition to numeric bounds.
            if reference.get_object() is None:raise ValueError('missing native reference')
            return (reference.idnum,reference.generation)
        root=reader.trailer['/Root'];pages=root.raw_get('/Pages')
        stack=[(pages,None,False,0)]
        while stack:
            reference,parent,exit_phase,start=stack.pop()
            identity=key(reference);node=reference.get_object()
            if exit_phase:
                if node['/Count']!=len(leaves)-start:reasons.append('native_page_count_mismatch')
                continue
            if identity in visited:reasons.append('native_page_cycle_or_reused_node');continue
            visited.add(identity);node_count+=1
            if parent is None:
                if '/Parent' in node:reasons.append('native_root_has_parent')
            elif '/Parent' not in node or key(node.raw_get('/Parent'))!=parent:
                reasons.append('native_parent_child_mismatch')
            kind=node.get('/Type')
            if kind=='/Pages':
                if set(node)-{'/Type','/Parent','/Kids','/Count','/Resources','/MediaBox','/CropBox','/Rotate'}:
                    reasons.append('unsupported_native_tree_capability')
                kids=node.raw_get('/Kids');count=node.raw_get('/Count')
                if not isinstance(kids,ArrayObject) or not isinstance(count,NumberObject) or count<0:
                    raise ValueError('unproved native Kids/Count types')
                stack.append((reference,parent,True,len(leaves)))
                stack.extend((child,identity,False,0) for child in reversed(kids))
            elif kind=='/Page' and parent is not None:
                leaves.append(identity)
                source_contents=node.raw_get('/Contents')
                if isinstance(source_contents,IndirectObject):key(source_contents)
                contents=source_contents.get_object()
                streams=contents if isinstance(contents,ArrayObject) else [source_contents]
                for stream_reference in streams:
                    key(stream_reference)
                    stream=stream_reference.get_object()
                    stream_count+=1
                    if not isinstance(stream,StreamObject):reasons.append('uncertain_native_content_stream');continue
                    if set(stream)-{'/Length','/Filter','/DecodeParms'}:
                        reasons.append('unsupported_native_stream_capability')
                    if any(field in stream for field in ('/F','/FFilter','/FDecodeParms')):
                        reasons.append('unsupported_external_content_stream')
            else:reasons.append('uncertain_native_page_tree_type')
        # Do not flatten a rejected/cyclic graph to invent a repaired view.
        if not reasons:
            shown=[key(page.indirect_reference) for page in reader.pages]
            if shown!=leaves:reasons.append('native_page_occurrence_order_mismatch')
    except Exception as error:
        reasons.append('uncertain_native_tree_parse:'+type(error).__name__)
    # Only a proved tree/embedded-stream domain may enter the old content
    # decoding helper. External sources are never fetched or treated as empty.
    native=n.native_pdf_support(path) if not reasons else None
    if native and not native['supported']:reasons.extend(native['rejections'])
    if not reasons:
        try:
            import pdfplumber
            with pdfplumber.open(path) as extracted:
                extracted_page_ids=[page.page_obj.pageid for page in extracted.pages]
            if extracted_page_ids!=[identity[0] for identity in leaves]:
                reasons.append('native_extraction_page_occurrence_mismatch')
        except Exception as error:
            reasons.append('uncertain_native_page_occurrence:'+type(error).__name__)
    return {'supported':not reasons,'rejections':sorted(set(reasons)),
            'native_leaf_references':leaves,'visited_nodes':node_count,
            'content_stream_occurrences':stream_count,'native_grammar':native,
            'extracted_native_page_ids':extracted_page_ids}


def compared(doc,path,certificates=None,missing_owner=False):
    before=copy.deepcopy(s.exhibit_rows(doc));findings=t.finding_contract(s.check_exhibits(doc))
    _,old,_=n.compared(doc,path,certificates,missing_owner)
    new=copy.deepcopy(old);proof=tree_stream_support(path) if path.suffix=='.pdf' else None
    if proof and not proof['supported']:
        new['source_supported']=False;new['source_EOF_proved']=False
        for item in new['tiers']:
            if item['tier']=='PENDING_CANDIDATE':item['tier']='LEGACY_A_RETAINED'
    assert before==s.exhibit_rows(doc) and findings==t.finding_contract(s.check_exhibits(doc))
    return old,new,proof


def actual_controls(directory):
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from pypdf import PdfReader,PdfWriter
    from pypdf.generic import (NameObject,NumberObject,ArrayObject,DictionaryObject,
                               IndirectObject,TextStringObject)
    records=[]
    modes=('ordinary','valid_nested','parent_mismatch','count_mismatch','duplicate_child',
           'root_parent_cycle','dangling_child','external_stream','unknown_stream','genuine_global_date')
    for number,title in enumerate(('점검기록','작업대장','관측도면')):
        for mode in modes:
            folder=directory/f'{mode}_{number}';folder.mkdir(parents=True,exist_ok=True);path=folder/'public_caption.pdf'
            s.build_pdf({'name':'public font','header':'공개','footer':'합성','body':[('p','공개')]},folder/'font.pdf')
            lines=['1. 자료 제출','가. 공개 자료 목록',f'갑 제1호증: {title}, 확인 부분 2025. 3. 4. 경로 기록.',
                   '을 제2호증: 비교자료, 확인 부분 2025. 3. 4. 경로 기록.','나. 자료 확인',
                   '기본 순서는 여러 단계로 구성되어 있다.','다. 처리 분석',
                   f'갑 제1호증 {title}: 순서를 설명한다. 2025. 3. 4. 확인 기록.']
            if mode=='genuine_global_date':lines.append(f'갑 제1호증 {title}: 순서를 설명한다. 2025. 3. 5. 확인 기록.')
            out=canvas.Canvas(str(path),pagesize=A4);out.setFont(s.build_pdf.__globals__['FONT'],10.5)
            for index,line in enumerate(lines):out.drawString(50,750-20*index,line)
            out.save()
            if mode not in ('ordinary','genuine_global_date'):
                reader=PdfReader(path);writer=PdfWriter();writer.clone_document_from_reader(reader)
                root_reference=writer._root_object.raw_get('/Pages');root=root_reference.get_object()
                page=writer.pages[0];leaf=page.indirect_reference
                if mode in ('valid_nested','parent_mismatch'):
                    node=DictionaryObject({NameObject('/Type'):NameObject('/Pages'),NameObject('/Kids'):ArrayObject([leaf] if mode=='valid_nested' else []),NameObject('/Count'):NumberObject(1 if mode=='valid_nested' else 0)})
                    branch=writer._add_object(node);page[NameObject('/Parent')]=branch
                    if mode=='valid_nested':node[NameObject('/Parent')]=root_reference;root[NameObject('/Kids')]=ArrayObject([branch])
                elif mode=='count_mismatch':root[NameObject('/Count')]=NumberObject(0)
                elif mode=='duplicate_child':root[NameObject('/Kids')]=ArrayObject([leaf,leaf]);root[NameObject('/Count')]=NumberObject(2)
                elif mode=='root_parent_cycle':root[NameObject('/Parent')]=root_reference
                elif mode=='dangling_child':root[NameObject('/Kids')]=ArrayObject([leaf,IndirectObject(999999,0,writer)]);root[NameObject('/Count')]=NumberObject(2)
                elif mode in ('external_stream','unknown_stream'):
                    stream=page.raw_get('/Contents').get_object()
                    stream[NameObject('/F' if mode=='external_stream' else '/PublicUnknown')]=TextStringObject('public_unavailable_source.dat')
                with path.open('wb') as target:writer.write(target)
            proof=tree_stream_support(path)
            assert proof['supported']==(mode in ('ordinary','valid_nested','genuine_global_date'))
            observation={'mode':mode,'format':'pdf','example':number,'public_true_duplicate':mode=='genuine_global_date','tree_support':proof}
            try:
                doc=m.read_document(path);old,new,checked=compared(doc,path)
                observation.update(m.observation(old,new,mode,'pdf',number,mode=='genuine_global_date'))
                assert checked==proof
                if mode in ('ordinary','valid_nested'):
                    assert old['original_A_findings']==1 and [i['tier'] for i in new['tiers']]==['PENDING_CANDIDATE']
                if not proof['supported']:assert not new['source_EOF_proved']
                if mode=='genuine_global_date':assert [i['tier'] for i in new['tiers']]==['LEGACY_A_RETAINED']
                observation['comparison_measured']=True
            except AssertionError:
                raise
            except Exception as error:
                if mode not in ('external_stream','dangling_child'):raise
                observation['comparison_measured']=False;observation['comparison_error']=type(error).__name__
                observation['full_EOF']='unmeasured';assert not proof['supported']
            records.append(observation)
    return records


def frozen_comparison(directory):
    capture=io.StringIO()
    with contextlib.redirect_stdout(capture):n.run(directory)
    receipt=json.loads(capture.getvalue());populations={'native21':receipt['new_controls'],**receipt['frozen']};groups={}
    for population,expected_records in populations.items():
        records=[]
        for expected in expected_records:
            extension=expected['format'];mode=expected['mode'];number=expected['example']
            if population=='native21':path=directory/'native_controls'/f'{mode}_{number}'/'public_caption.pdf'
            else:
                base=directory/'frozen'/'new_controls' if population=='new54' else directory/'frozen'/'frozen'/population
                native=mode in ('native_title','native_date_title')
                folder=(f'native_pdf_title_{number}' if mode=='native_title' else f'native_date_title_{number}' if mode=='native_date_title' else
                        f'{extension}_source_boundary_{number}' if mode in ('native_source_reordered','native_source_table') else
                        f'{extension}_native_unsupported_{number}' if mode in ('image_only_final_page','native_symbol_at_end') else
                        f'docx_foreign_namespace_{number}' if mode=='foreign_namespace_at_end' else f'{extension}_{number}_{mode}')
                path=base/folder/('public_title_role.pdf' if native else 'public_caption.'+extension)
            doc=m.read_document(path);certs=t.native_title_certificates(doc,path) if mode in ('native_title','native_date_title') else None
            provider=s.source_index
            if population=='original111' and mode=='missing_owner':
                def original_fault(reading,pieces):
                    owners=provider(reading,pieces)
                    for index,owner in enumerate(owners):
                        if owner and reading.text[index]=='갑':owners[index]=None;break
                    return owners
                s.source_index=original_fault
            try:old,new,proof=compared(doc,path,certs,population=='dated117' and mode=='missing_owner')
            finally:s.source_index=provider
            assert [i['tier'] for i in old['tiers']]==expected['refined_tiers']
            assert old['original_A_findings']==expected['original_A']
            assert [i['tier'] for i in new['tiers']]==expected['refined_tiers']
            out=m.observation(old,new,mode,extension,number,expected['public_true_duplicate']);out['tree_support']=proof;out['comparison_measured']=True;records.append(out)
        groups[population]=records
    return groups


def summary(records):
    measured=[r for r in records if r['comparison_measured']]
    result=m.summary(measured);result['actual_documents']=len(records);result['unmeasured_documents']=len(records)-len(measured)
    return result


def run(directory):
    new=actual_controls(directory/'tree_controls');frozen=frozen_comparison(directory/'frozen')
    print(json.dumps({'new_controls':new,'frozen':frozen,'counts':{'new_controls':summary(new),**{key:summary(records) for key,records in frozen.items()}}},ensure_ascii=False,indent=2))


if __name__=='__main__':
    import sys
    run(Path(sys.argv[1]))
