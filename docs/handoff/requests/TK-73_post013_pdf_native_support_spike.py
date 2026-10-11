"""Separate native PDF capability comparison; frozen diagnostics unchanged."""
import contextlib
import copy
import importlib.util
import io
import json
import math
from collections import Counter
from pathlib import Path

spec=importlib.util.spec_from_file_location('eof_support',Path(__file__).with_name('TK-73_post013_eof_support_spike.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
s=m.s;t=m.t


def native_pdf_support(path):
    """Account for actual native page instructions; extraction absence is unused."""
    from pypdf import PdfReader
    from pypdf.generic import (read_object, NameObject, NumberObject, FloatObject,
                               TextStringObject, ByteStringObject, ArrayObject)
    from pypdf._utils import read_non_whitespace
    reasons=[];operators=[];resource_keys=[]
    arity={b'BT':0,b'ET':0,b'T*':0,b'q':0,b'Q':0,b'cm':6,b'Tm':6,b'Td':2,b'TD':2,
           b'Tf':2,b'TL':1,b'Tc':1,b'Tw':1,b'Tz':1,b'Ts':1,b'Tr':1,
           b'Tj':1,b'TJ':1,b"'":1,b'"':3,b'rg':3,b'RG':3,b'g':1,b'G':1,b'k':4,b'K':4}
    def number(x):return isinstance(x,(NumberObject,FloatObject)) and math.isfinite(float(x))
    def string(x):return isinstance(x,(TextStringObject,ByteStringObject))
    try:
        reader=PdfReader(path,strict=True)
        if reader.is_encrypted:reasons.append('unsupported_native_encryption')
        root=reader.trailer['/Root']
        if set(root)-{'/Type','/Pages','/PageMode'}:reasons.append('unsupported_native_catalog_capability')
        if root.get('/Type')!='/Catalog':reasons.append('uncertain_native_catalog')
        for page_index,page in enumerate(reader.pages):
            ancestor=page.get('/Parent');visited=set()
            while ancestor is not None:
                parent=ancestor.get_object()
                if id(parent) in visited:
                    reasons.append('uncertain_native_page_tree_cycle');break
                visited.add(id(parent))
                if parent.get('/Type')!='/Pages' or set(parent)-{'/Type','/Parent','/Kids','/Count','/Resources','/MediaBox','/CropBox','/Rotate'}:
                    reasons.append('unsupported_native_page_ancestor')
                ancestor=parent.get('/Parent')
            if set(page)-{'/Type','/Parent','/Resources','/Contents','/MediaBox','/CropBox','/Rotate','/Trans'}:
                reasons.append('unsupported_native_page_capability')
            if page.get('/Trans') and page['/Trans'].get_object():reasons.append('unsupported_native_transition')
            resources=page.get('/Resources')
            if resources is None:reasons.append('missing_native_resources');continue
            resources=resources.get_object();resource_keys.append(sorted(resources))
            if set(resources)-{'/Font','/ProcSet'}:reasons.append('unsupported_native_resource')
            fonts=resources.get('/Font',{}).get_object() if '/Font' in resources else {}
            for font in fonts.values():
                font=font.get_object()
                if font.get('/Subtype') not in ('/Type0','/Type1','/TrueType') or '/CharProcs' in font:
                    reasons.append('unsupported_native_font_program')
                if font.get('/Subtype')=='/Type0':
                    descendants=font.get('/DescendantFonts',[])
                    if not descendants or any(f.get_object().get('/Subtype') not in ('/CIDFontType0','/CIDFontType2') for f in descendants):
                        reasons.append('uncertain_native_font_descendants')
            contents=page.get('/Contents')
            if contents is None:reasons.append('missing_native_content_stream');continue
            contents=contents.get_object();streams=contents if isinstance(contents,ArrayObject) else [contents]
            args=[];text_open=False;graphics_depth=0
            # Streams are concatenated in native declared order. Only standard
            # content-stream whitespace is inserted; it proves no title syntax.
            data=b'\n'.join(stream.get_object().get_data() for stream in streams)
            source=io.BytesIO(data)
            while True:
                token=read_non_whitespace(source)
                if not token:break
                if token==b'%':source.readline();continue
                if token.isalpha() or token in (b"'",b'"'):
                    op=token
                    while True:
                        char=source.read(1)
                        if not char:break
                        if char in b'\x00\t\n\f\r ()<>[]{}/%':source.seek(-1,1);break
                        op+=char
                    operators.append({'page':page_index,'operator':op.decode('latin1')})
                    if op not in arity:reasons.append('unsupported_native_operator:'+op.decode('latin1'));break
                    valid=len(args)==arity[op]
                    if op==b'Tf':valid=valid and isinstance(args[0],NameObject) and args[0] in fonts and number(args[1])
                    elif op in (b'Tj',b"'"):valid=valid and string(args[0])
                    elif op==b'"':valid=valid and all(number(x) for x in args[:2]) and string(args[2])
                    elif op==b'TJ':valid=valid and isinstance(args[0],ArrayObject) and all(string(x) or number(x) for x in args[0])
                    else:valid=valid and all(number(x) for x in args)
                    if not valid:reasons.append('uncertain_native_operator_operands');break
                    if op==b'BT':
                        if text_open:reasons.append('uncertain_native_text_state')
                        text_open=True
                    elif op==b'ET':
                        if not text_open:reasons.append('uncertain_native_text_state')
                        text_open=False
                    elif op==b'q':graphics_depth+=1
                    elif op==b'Q':
                        graphics_depth-=1
                        if graphics_depth<0:reasons.append('uncertain_native_graphics_state')
                    elif op in (b'Tj',b'TJ',b"'",b'"',b'T*',b'Tm',b'Td',b'TD') and not text_open:
                        reasons.append('uncertain_native_text_state')
                    if op==b'Tr' and args[0]!=0:reasons.append('unsupported_native_text_rendering_mode')
                    args=[]
                else:
                    source.seek(-1,1);start=source.tell();args.append(read_object(source,reader))
                    if source.tell()<=start:raise ValueError('native token parser did not advance')
            if args:reasons.append('unconsumed_native_operands')
            if text_open or graphics_depth:reasons.append('unclosed_native_content_state')
    except Exception as error:
        reasons.append('uncertain_native_pdf_parse:'+type(error).__name__)
    return {'supported':not reasons,'rejections':sorted(set(reasons)),
            'operators':operators,'resource_keys':resource_keys}


def compared(doc,path,certificates=None,missing_owner=False):
    rows=copy.deepcopy(s.exhibit_rows(doc));findings=t.finding_contract(s.check_exhibits(doc))
    _,old=m.refined(doc,path,certificates=certificates,missing_owner=missing_owner)
    new=copy.deepcopy(old);native=native_pdf_support(path) if path.suffix=='.pdf' else None
    if native and not native['supported']:
        new['source_supported']=False;new['source_EOF_proved']=False
        for item in new['tiers']:
            if item['tier']=='PENDING_CANDIDATE':item['tier']='LEGACY_A_RETAINED'
    assert rows==s.exhibit_rows(doc) and findings==t.finding_contract(s.check_exhibits(doc))
    return old,new,native


def record(old,new,native,mode,number,truth):
    out=m.observation(old,new,mode,'pdf',number,truth);out['native_support']=native
    return out


def actual_controls(directory):
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.colors import red,blue
    from pypdf import PdfReader,PdfWriter
    from pypdf.generic import DecodedStreamObject,NameObject,DictionaryObject
    records=[]
    for number,title in enumerate(('점검기록','작업대장','관측도면')):
        lines=['1. 자료 제출','가. 공개 자료 목록',f'갑 제1호증: {title}, 확인 부분 2025. 3. 4. 경로 기록.',
               '을 제2호증: 비교자료, 확인 부분 2025. 3. 4. 경로 기록.','나. 자료 확인',
               '기본 순서는 여러 단계로 구성되어 있다.','다. 처리 분석',
               f'갑 제1호증 {title}: 순서를 설명한다. 2025. 3. 4. 확인 기록.']
        for mode in ('ordinary','form','shading','unknown_operator','dangling_operand','unknown_resource','genuine_global_date'):
            folder=directory/f'{mode}_{number}';folder.mkdir(parents=True,exist_ok=True);path=folder/'public_caption.pdf'
            s.build_pdf({'name':'public font','header':'공개','footer':'합성','body':[('p','공개')]},folder/'font.pdf')
            out=canvas.Canvas(str(path),pagesize=A4)
            if mode=='form':out.beginForm('PublicForm')
            out.setFont(s.build_pdf.__globals__['FONT'],10.5)
            for index,line in enumerate(lines):out.drawString(50,750-20*index,line)
            if mode=='genuine_global_date':out.drawString(50,750-20*len(lines),f'갑 제1호증 {title}: 순서를 설명한다. 2025. 3. 5. 확인 기록.')
            if mode=='form':out.endForm();out.doForm('PublicForm')
            if mode=='shading':out.linearGradient(50,500,150,500,(red,blue))
            out.save()
            if mode in ('unknown_operator','dangling_operand','unknown_resource'):
                reader=PdfReader(path);writer=PdfWriter();writer.clone_document_from_reader(reader);page=writer.pages[0]
                if mode=='unknown_resource':page['/Resources'][NameObject('/PublicUnknown')]=DictionaryObject()
                else:
                    stream=DecodedStreamObject();stream.set_data(page.get_contents().get_data()+(b'\n publicUnknown\n' if mode=='unknown_operator' else b'\n 17\n'))
                    page[NameObject('/Contents')]=writer._add_object(stream)
                with path.open('wb') as target:writer.write(target)
            doc=m.read_document(path);old,new,native=compared(doc,path)
            assert old['original_A_findings']==1 and [i['tier'] for i in old['tiers']]==['LEGACY_A_RETAINED' if mode=='genuine_global_date' else 'PENDING_CANDIDATE']
            assert [i['tier'] for i in new['tiers']]==['PENDING_CANDIDATE' if mode=='ordinary' else 'LEGACY_A_RETAINED']
            assert new['source_EOF_proved']==(mode in ('ordinary','genuine_global_date'))
            observation=record(old,new,native,mode,number,mode=='genuine_global_date')
            import pdfplumber
            with pdfplumber.open(path) as raw:observation['extracted_object_categories']=sorted({kind for page in raw.pages for kind in page.objects})
            records.append(observation)
    return records


def frozen_comparison(directory):
    capture=io.StringIO()
    with contextlib.redirect_stdout(capture):m.run(directory)
    frozen=json.loads(capture.getvalue());groups={}
    populations={'new54':frozen['new_controls'],**frozen['frozen']}
    for population,expected_records in populations.items():
        records=[]
        for expected in expected_records:
            extension=expected['format'];mode=expected['mode'];number=expected['example']
            base=directory/'new_controls' if population=='new54' else directory/'frozen'/population
            native=mode in ('native_title','native_date_title')
            folder=(f'native_pdf_title_{number}' if mode=='native_title' else f'native_date_title_{number}' if mode=='native_date_title' else
                    f'{extension}_source_boundary_{number}' if mode in ('native_source_reordered','native_source_table') else
                    f'{extension}_native_unsupported_{number}' if mode in ('image_only_final_page','native_symbol_at_end') else
                    f'docx_foreign_namespace_{number}' if mode=='foreign_namespace_at_end' else f'{extension}_{number}_{mode}')
            path=base/folder/('public_title_role.pdf' if native else 'public_caption.'+extension)
            doc=m.read_document(path);certs=t.native_title_certificates(doc,path) if native else None
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
            out=m.observation(old,new,mode,extension,number,expected['public_true_duplicate']);out['native_support']=proof;records.append(out)
        groups[population]=records
    return groups


def run(directory):
    new=actual_controls(directory/'native_controls');frozen=frozen_comparison(directory/'frozen')
    print(json.dumps({'new_controls':new,'frozen':frozen,'counts':{'new_controls':m.summary(new),**{name:m.summary(records) for name,records in frozen.items()}}},ensure_ascii=False,indent=2))


if __name__=='__main__':
    import sys
    run(Path(sys.argv[1]))
