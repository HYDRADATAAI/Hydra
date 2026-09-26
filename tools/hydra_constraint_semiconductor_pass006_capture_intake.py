"""Bind existing semiconductor source registries to private T1 persisted receipts.

No acquisition, source-version minting, identity resolution, or runtime admission.
"""
from __future__ import annotations
import argparse
from datetime import datetime
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'constraint-t1-raw-artifact-store/src'))
from hydra_constraint_t1_raw.store import RawArtifactStore

SLICE = REPO / 'docs/constraint/second_slice/semiconductor_advanced_packaging_critical_materials_v1'
REGISTRIES = (
    SLICE / 'HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH019_SEMICONDUCTOR_FACILITY_MATERIAL_EQUIPMENT_SOURCE_REGISTRY_EXTENSION_V001_20260926.json',
    SLICE / 'HYDRA_CONSTRAINT_THREAD6_SUCCESSOR_BATCH018_SEMICONDUCTOR_ADVANCED_PACKAGING_CRITICAL_MATERIALS_SOURCE_REGISTRY_V001_20260926.json',
    SLICE / 'HYDRA_CONSTRAINT_SEMICONDUCTOR_PASS004_SOURCE_REGISTRY_20260926.json',
)

def timestamp(value):
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('timestamp requires timezone')
    return dt


def sources():
    records = {}
    for path in REGISTRIES:
        for source in json.loads(path.read_text())['sources']:
            if source['source_id'] in records:
                raise ValueError('duplicate registry source identity')
            records[source['source_id']] = source
    return records


def intake(store, receipt_map, *, release_id, created_at):
    registered = sources()
    if set(receipt_map) != set(registered):
        raise ValueError('receipt map must cover exactly the registered sources')
    created = timestamp(created_at)
    receipts = []
    for source_id, source in sorted(registered.items()):
        relative = Path(receipt_map[source_id])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('receipt path must stay inside private store')
        path = (store.root / relative).resolve()
        if not path.is_relative_to(store.root.resolve()):
            raise ValueError('receipt path escapes private store')
        receipt = json.loads(path.read_text())
        issues = store.validate_receipt(receipt)
        if issues:
            raise ValueError(f'{source_id}: {issues}')
        if receipt['source_id'] != source_id or receipt['source_locator'] != source['url']:
            raise ValueError('receipt source identity or locator mismatch')
        if receipt['processing_disposition'] != 'ELIGIBLE':
            raise ValueError('receipt is not eligible')
        acquired = timestamp(receipt['acquired_at'])
        available = timestamp(receipt['available_at'])
        if not acquired <= available <= created:
            raise ValueError('receipt/release temporal order invalid')
        if available < timestamp(source['available_at']):
            raise ValueError('receipt backdates this reviewed seed availability')
        receipts.append(receipt)
    # Existing T1 implementation validates exact stored records again and writes
    # its immutable release format. No alternative provenance format is created.
    return store.write_release_manifest(release_id=release_id, created_at=created_at, receipts=receipts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--list-sources', action='store_true')
    parser.add_argument('--private-root')
    parser.add_argument('--receipt-map', type=Path)
    parser.add_argument('--release-id')
    parser.add_argument('--created-at')
    args = parser.parse_args()
    if args.list_sources:
        print(json.dumps([{'source_id': key, 'url': value['url'], 'available_at_floor': value['available_at']} for key, value in sorted(sources().items())], indent=2))
        return
    if not all((args.private_root, args.receipt_map, args.release_id, args.created_at)):
        parser.error('intake requires private-root, receipt-map, release-id and created-at')
    store = RawArtifactStore(root=Path(args.private_root), public_repo_root=REPO)
    manifest = intake(store, json.loads(args.receipt_map.read_text()), release_id=args.release_id, created_at=args.created_at)
    print(json.dumps({'release_id': manifest['release_id'], 'members': len(manifest['members']), 'runtime_admitted': False}))

if __name__ == '__main__':
    main()
