"""Apply both review diagnostics to the same fixed public111 documents."""
import contextlib
import importlib.util
import io
import json
from collections import Counter
from pathlib import Path

spec=importlib.util.spec_from_file_location('dated',Path(__file__).with_name('TK-73_post013_dated_eof_spike.py'))
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
t=d.t;s=t.s


def run(directory):
    # Original111 generator/expectations are unchanged and execute first.
    with contextlib.redirect_stdout(io.StringIO()):frozen=t.run(directory)
    records=[];counts=Counter();changes=Counter()
    for expected in frozen:
        mode=expected['mode'];extension=expected['format'];number=expected['example']
        native=mode=='native_title'
        folder=directory/(f'native_pdf_title_{number}' if native else f'{extension}_{number}_{mode}')
        path=folder/('public_title_role.pdf' if native else 'public_caption.'+extension)
        doc=s.parse_document(str(path),document_id='public_caption',filename=path.name,
                             mime_type={'txt':'text/plain','pdf':'application/pdf','docx':'application/vnd.openxmlformats-officedocument.wordprocessingml.document'}[extension],sha256='0'*64)
        certs=t.native_title_certificates(doc,path) if native else None
        old=t.diagnose(doc,path,title_certificates=certs,missing_owner=mode=='missing_owner')
        before=t.finding_contract(s.check_exhibits(doc))
        original_provider=s.source_index
        if mode=='missing_owner':
            # Match the ORIGINAL111 producer-metadata simulation exactly.
            # The newer117 simulation targets a different occurrence; do not
            # confuse a changed fault location with a changed review criterion.
            def identical_fault(reading,pieces):
                owners=original_provider(reading,pieces)
                for index,owner in enumerate(owners):
                    if owner and reading.text[index]=='갑':owners[index]=None;break
                return owners
            s.source_index=identical_fault
        try:new=d.diagnose(doc,path,certificates=certs)
        finally:s.source_index=original_provider
        assert before==t.finding_contract(s.check_exhibits(doc))
        old_tiers=[i['tier'] for i in old['proposal_tiers']];new_tiers=[i['tier'] for i in new['tiers']]
        assert old_tiers==[i['tier'] for i in expected['proposal_tiers']]
        assert old['original_A_findings']==new['original_A_findings']==expected['original_A_findings']
        assert old['original_rows']==new['original_rows']==expected['original_rows']
        assert old['other_original_rule_ids']==new['other_original_rule_ids']==expected['other_original_rule_ids']
        # Explicit extension impact expectation; ORIGINAL111 expectations stay.
        assert new_tiers==(['PENDING_CANDIDATE'] if mode=='date_guard' else old_tiers)
        changed=old_tiers!=new_tiers
        if changed:changes[mode]+=1
        counts['documents']+=1;counts['original_A']+=old['original_A_findings'];counts['changed_documents']+=changed
        for old_tier,new_tier in zip(old_tiers,new_tiers):
            counts['old_'+old_tier]+=1;counts['new_'+new_tier]+=1
            if expected['public_true_duplicate']:
                counts['detected_true']+=1
                counts['old_true_pending']+=old_tier=='PENDING_CANDIDATE'
                counts['new_true_pending']+=new_tier=='PENDING_CANDIDATE'
                counts['additional_true_confirmation_loss']+=changed and new_tier=='PENDING_CANDIDATE'
            else:
                counts['original_false_candidates']+=1
                counts['old_false_pending']+=old_tier=='PENDING_CANDIDATE'
                counts['new_false_pending']+=new_tier=='PENDING_CANDIDATE'
        records.append({'format':extension,'mode':mode,'example':number,'original_A':old['original_A_findings'],
                        'old_tiers':old_tiers,'amended_tiers':new_tiers,'changed':changed,
                        'public_true_duplicate':expected['public_true_duplicate'],
                        'original_rows_findings_unchanged':True,'other_original_rule_ids':new['other_original_rule_ids'],
                        'source_EOF_proved':new['source_EOF_proved'],
                        'same_original_owner_fault_simulation':mode=='missing_owner'})
    print(json.dumps({'counts':dict(counts),'changed_families':dict(changes),'records':records},ensure_ascii=False,indent=2))


if __name__=='__main__':
    import sys
    run(Path(sys.argv[1]))
