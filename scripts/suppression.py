"""Private hashed suppression records and a local state-operation lock.

The lock coordinates processes on one filesystem; it is not a distributed lock
for independent cloud-synced copies. Suppression records never retain source text.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
import sys

from common import create_once, digest, encoded, provenance, safe_path, timestamp, within


def valid_hash(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


@contextmanager
def state_lock(root):
    """Fail rather than wait when another local writer owns memory state."""
    path = within(root, '.memory-state/operation.lock')
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    stream = os.fdopen(fd, 'r+b')
    locked = False
    try:
        if sys.platform == 'win32':
            import msvcrt
            if os.fstat(stream.fileno()).st_size == 0:
                stream.write(b'0')
                stream.flush()
            stream.seek(0)
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise ValueError('Another local memory operation is active; retry after it finishes') from exc
        else:
            import fcntl
            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise ValueError('Another local memory operation is active; retry after it finishes') from exc
        locked = True
        yield
    finally:
        if locked:
            if sys.platform == 'win32':
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        stream.close()


def selector(source_id=None, session_id=None, harness=None):
    """Return only hashed identity; session IDs are scoped to their harness."""
    if (source_id is None) == (session_id is None):
        raise ValueError('Choose exactly one source ID or session ID to suppress')
    identity = source_id if source_id is not None else session_id
    if not isinstance(identity, str) or not identity.strip() or identity.casefold() in ('unknown', 'unavailable'):
        raise ValueError('Suppression needs a known explicit source or session ID')
    if source_id is not None:
        if harness is not None:
            raise ValueError('Harness is only used with session suppression')
        return {'scope': 'source', 'source_hash': digest(source_id.encode())}
    if not isinstance(harness, str) or not harness.strip() or harness.casefold() in ('unknown', 'unavailable'):
        raise ValueError('Session suppression requires its known harness')
    return {'scope': 'session', 'session_hash': digest(encoded([harness.strip().casefold(), session_id]))}


def suppression_id(selected):
    return digest(encoded(selected))


def entries(root):
    result = []
    for path in sorted(within(root, '.memory-state/suppressions').glob('*.json')):
        value = json.loads(safe_path(path).read_text(encoding='utf-8'))
        if not isinstance(value, dict) or value.get('version') != 1 or value.get('scope') not in ('source', 'session'):
            raise ValueError('Invalid suppression record; preserve it and repair before ingestion')
        field = value['scope'] + '_hash'
        if set(value) != {'version', 'scope', field, 'created_at', 'editor'} or not valid_hash(value.get(field)):
            raise ValueError('Invalid suppression record fields')
        selected = {'scope': value['scope'], field: value[field]}
        if path.stem != suppression_id(selected):
            raise ValueError('Suppression record identity changed')
        timestamp(value['created_at'])
        provenance(value['editor'])
        result.append(value)
    return result


def matches(selected, data):
    if selected['scope'] == 'source':
        source_id = data.get('source_id')
        return isinstance(source_id, str) and digest(source_id.encode()) == selected['source_hash']
    session_id, harness = data.get('session_id'), data.get('harness')
    if not isinstance(session_id, str) or not isinstance(harness, str):
        return False
    return digest(encoded([harness.strip().casefold(), session_id])) == selected['session_hash']


def is_suppressed(root, data):
    """Return bool; corrupted tombstones raise rather than permit ingestion."""
    if not isinstance(data, dict):
        raise ValueError('Suppression lookup requires source metadata')
    return any(matches(entry, data) for entry in entries(root))


def save(root, selected, editor):
    """Caller must hold state_lock. Preserve the original suppression provenance."""
    provenance(editor)
    existing = entries(root)
    field = selected['scope'] + '_hash'
    for entry in existing:
        if entry['scope'] == selected['scope'] and entry.get(field) == selected[field]:
            return entry
    value = {**selected, 'version': 1, 'created_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
             'editor': {key: editor[key] for key in ('assistant', 'harness', 'model', 'agent', 'session_id',
                                                    'chat_reference', 'model_note') if key in editor}}
    create_once(within(root, f'.memory-state/suppressions/{suppression_id(selected)}.json'), encoded(value))
    return value


def cleanup_history(root, selected):
    """Recover only hashed IDs from previous interrupted cleanup batches."""
    key = suppression_id(selected)
    inputs, runs = set(), set()
    for path in sorted(within(root, f'.memory-state/forget-plans/{key}').glob('*.json')):
        value = json.loads(safe_path(path).read_text(encoding='utf-8'))
        if (not isinstance(value, dict) or set(value) != {'version', 'suppression_id', 'input_ids', 'run_ids'}
                or value['version'] != 1 or value['suppression_id'] != key
                or digest(encoded(value)) != path.stem):
            raise ValueError('Invalid forgetting recovery record')
        for field in ('input_ids', 'run_ids'):
            if not isinstance(value[field], list) or any(not valid_hash(x) for x in value[field]):
                raise ValueError('Invalid forgetting recovery identifiers')
        inputs.update(value['input_ids'])
        runs.update(value['run_ids'])
    return inputs, runs


def save_cleanup(root, selected, inputs, runs):
    """Save recoverable paths by hash before deleting any selected evidence."""
    key = suppression_id(selected)
    value = {'version': 1, 'suppression_id': key, 'input_ids': sorted(inputs), 'run_ids': sorted(runs)}
    path = within(root, f'.memory-state/forget-plans/{key}/{digest(encoded(value))}.json')
    create_once(path, encoded(value))
