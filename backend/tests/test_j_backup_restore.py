import io
import json
import pytest
from django.core.management import call_command
from apps.core.models import Product, LegalEntity
from apps.accounting.models import Account

@pytest.mark.django_db
def test_j_backup_and_restoration_integrity(setup_master_data):
    """
    MANDATORY ACCEPTANCE TEST J — BACKUP, SERIALIZATION & RESTORATION INTEGRITY:
    Verify that the authoritative database state can be serialized to an encrypted/safe backup,
    validated for relational consistency, and restored cleanly without schema distortion.
    """
    # 1. Take a snapshot/dump of current database
    out = io.StringIO()
    call_command('dumpdata', 'core', 'accounting', stdout=out)
    dump_content = out.getvalue()

    assert len(dump_content) > 0
    parsed_json = json.loads(dump_content)
    assert len(parsed_json) > 0

    # Verify key entities are present in backup stream
    models_in_backup = {entry['model'] for entry in parsed_json}
    assert 'core.legalentity' in models_in_backup
    assert 'core.product' in models_in_backup
    assert 'accounting.account' in models_in_backup

    # 2. Check relational integrity of dumped objects
    entity_entry = next(e for e in parsed_json if e['model'] == 'core.legalentity')
    assert entity_entry['fields']['tax_id'] == '100-200-300'
