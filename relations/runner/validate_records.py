#!/usr/bin/env python3
"""Validate retained run records with the published JSON Schema (test-only dependency)."""
import json
from pathlib import Path
import sys
from jsonschema import Draft202012Validator, FormatChecker

schema = json.loads((Path(__file__).resolve().parent/'run-record.schema.json').read_text())
Draft202012Validator.check_schema(schema)
validator = Draft202012Validator(schema, format_checker=FormatChecker())
count = 0
for root in sys.argv[1:]:
    records = list(Path(root).glob('*/run.json'))
    if not records:
        raise SystemExit('No run records: '+root)
    for path in records:
        validator.validate(json.loads(path.read_text()))
        count += 1
if not count:
    raise SystemExit('Usage: validate_records.py OUTPUT_DIRECTORY ...')
print(f'Validated {count} run records against the v1 schema.')
