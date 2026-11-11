"""Public synthetic controls: temporal adjectives are not payment-rate bases."""
import pytest
from packages.claim_engine.calculation import CalculationEngine
from packages.common.schemas import Block,Page,NormalizedDocument

def findings(text):
    return CalculationEngine().verify_document(NormalizedDocument(document_id='d',filename='d.txt',mime_type='text/plain',sha256='0'*64,pages=[Page(page_number=1,blocks=[Block(block_id='b',text=text,page=1)])]))

@pytest.mark.parametrize('prefix',['당일 ','단기 계약을 체결한 ','장기 근속한 '])
@pytest.mark.parametrize('n,rate',[(4,25000),(5,80000),(8,45000)])
def test_non_rate_modifier_preserves_single_payment_mismatch(prefix,n,rate):
    text=prefix+f'직원 {n}명에게 각 {rate:,}원씩 지급하여 합계 {n*rate+10000:,}원이다.'
    assert any(f.type.value=='ARITHMETIC_MISMATCH' for f in findings(text))

@pytest.mark.parametrize('n,rate',[(4,25000),(5,80000),(8,45000)])
def test_real_repeated_rate_still_suspends(n,rate):
    text=f'매일 사흘 동안 직원 {n}명에게 각 {rate:,}원씩 지급하여 합계 {3*n*rate:,}원이다.'
    assert not findings(text)
