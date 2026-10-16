"""Small dependency-free helpers. No network access or model calls."""
import hashlib
import json
from datetime import datetime
from pathlib import Path
import sys

IDENTITIES = ('assistant', 'harness', 'model', 'agent', 'session_id', 'chat_reference')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()


def safe_path(value):
    path = Path(value).expanduser().absolute()
    for part in (path, *path.parents):
        if part.is_symlink():
            if sys.platform == 'darwin' and str(part) in ('/tmp', '/var'):
                continue
            raise ValueError(f'Symlink destination is not supported: {part}')
    return path.resolve()


def within(root, relative):
    if Path(relative).is_absolute() or '..' in Path(relative).parts:
        raise ValueError('Expected a relative path within the vault')
    path = safe_path(root / relative)
    if not path.is_relative_to(root):
        raise ValueError('Path escapes the vault')
    return path


def provenance(value):
    if not isinstance(value, dict):
        raise ValueError('Provenance must be an object')
    for key in IDENTITIES:
        if not isinstance(value.get(key), str) or not value[key].strip():
            raise ValueError(f'Missing provenance: {key}')
    if value['model'] == 'unknown' and not value.get('model_note'):
        raise ValueError('An unknown model requires model_note')
    return value


def timestamp(value):
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError('Timestamp needs a timezone offset')
    return dt


def note(body, kind, description, editor, now):
    provenance(editor)
    meta = {'type': kind, 'status': 'active', 'description': description, 'updated': now,
            'last_edited_by': editor['assistant'], 'last_edited_harness': editor['harness'],
            'last_edited_model': editor['model'], 'last_edited_agent': editor['agent'],
            'last_edited_session_id': editor['session_id'],
            'last_edited_chat': editor['chat_reference'],
            'last_edited_model_note': editor.get('model_note', '')}
    return ('---\n' + ''.join(f'{k}: {json.dumps(v, ensure_ascii=False)}\n' for k, v in meta.items())
            + '---\n\n' + body.rstrip() + '\n').encode()


def create_once(path, data):
    """Exclusive create, or verify an exact existing file; never overwrite."""
    path = safe_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if not path.is_file() or path.read_bytes() != data:
            raise ValueError(f'Existing content differs; preserved: {path}')
        return False
    with path.open('xb') as stream:
        stream.write(data)
    if path.read_bytes() != data:
        raise OSError(f'Readback failed: {path}')
    return True
