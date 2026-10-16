"""Small dependency-free helpers. No network access or model calls."""
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
import sys
import tempfile

IDENTITIES = ('assistant', 'harness', 'model', 'agent', 'session_id', 'chat_reference')


def cli_encoding():
    """Use UTF-8 for redirected CLI output too, including Windows pipes."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')


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
    if 'model_note' in value and not isinstance(value['model_note'], str):
        raise ValueError('model_note must be text')
    if value['model'] == 'unknown' and not value.get('model_note', '').strip():
        raise ValueError('An unknown model requires model_note')
    return value


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError('Timestamp must be ISO text with a timezone offset')
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
    # Publish a fully written file exclusively. A failed write never leaves a
    # truncated final file, and a concurrent create cannot be overwritten.
    fd, temporary = tempfile.mkstemp(prefix='.memory-write-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if path.read_bytes() != data:
                raise ValueError(f'Concurrent content differs; preserved: {path}')
            return False
    finally:
        Path(temporary).unlink(missing_ok=True)
    if path.read_bytes() != data:
        raise OSError(f'Readback failed: {path}')
    return True


def storage(c):
    """Legacy OneDrive configs remain valid; new setups must choose a provider."""
    value = c.get('storage')
    legacy = c.get('onedrive_relative_path')
    if value is None:
        value = {'provider': 'onedrive' if legacy else 'local', 'relative_path': legacy or ''}
    if not isinstance(value, dict):
        raise ValueError('storage must be an object')
    if value.get('provider') not in ('onedrive', 'google-drive', 'dropbox', 'icloud', 'network-share', 'other', 'local'):
        raise ValueError('Choose a supported storage provider or other/local')
    if not isinstance(value.get('relative_path', ''), str):
        raise ValueError('storage.relative_path must be text')
    if legacy and (value['provider'] != 'onedrive' or value.get('relative_path') != legacy):
        raise ValueError('Conflicting legacy OneDrive and storage settings')
    return {'provider': value['provider'], 'relative_path': value.get('relative_path', '')}
