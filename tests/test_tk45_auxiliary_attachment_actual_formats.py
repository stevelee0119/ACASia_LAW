"""Same approved direct-action/partitive contrasts in generated real formats."""
import pytest

from tests.test_tk45_case_attachment_actual_formats import (
    test_public_original_attachment_survives_actual_format_pipeline as _format_pipeline,
)


@pytest.mark.parametrize('first,expected', [
    ('상계의 의사표시를 해 둔 이후', False),
    ('상계의 의사표시를 일부 해 둔 이후', True),
])
@pytest.mark.parametrize('kind,width', [('pdf', 595), ('pdf', 720), ('docx', None)])
def test_public_auxiliary_action_survives_actual_format_pipeline(tmp_path, first, expected, kind, width):
    _format_pipeline(tmp_path, first, expected, kind, width)
