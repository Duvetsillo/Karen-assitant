"""Scoped HA conversation bridge. Reuses Karen's archive, memory and local Core.

The credential grants conversation only. It never grants plans, PC tools,
Home Assistant control, arbitrary chat access, or mobile administration.
"""
from datetime import datetime, timezone
import hashlib
import hmac
from pathlib import Path
import re
import secrets
import uuid

from karen_core2.privacy import seal, unseal

KEY_PATH = Path(__file__).resolve().parent / '.private' / 'ha-conversation.dpapi'


def provision(path=KEY_PATH):
    """Explicit provisioning only. Never prints the credential."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    key = secrets.token_urlsafe(32)
    with path.open('x', encoding='ascii') as out:
        out.write(seal({'scope': 'ha.conversation', 'key': key}))
    return key


def credential(header, path=KEY_PATH):
    try:
        config = unseal(Path(path).read_text(encoding='ascii'))
        candidate = header.removeprefix('Bearer ')
        if (not header.startswith('Bearer ') or len(candidate) < 32 or config['scope'] != 'ha.conversation'
                or not hmac.compare_digest(config['key'], candidate)):
            return None
        return hashlib.sha256(candidate.encode()).hexdigest()
    except (OSError, ValueError, KeyError, TypeError):
        return None


def converse(app, identity, data):
    if app.core2 is None:
        raise RuntimeError('Core local no disponible.')
    if set(data) - {'text', 'conversation_id', 'user_id'} or 'text' not in data:
        raise ValueError('Contrato de conversación inválido.')
    text = data['text']
    conversation_id = data.get('conversation_id') or uuid.uuid4().hex
    user = data.get('user_id') or 'local-ha'
    if (not isinstance(text, str) or not 1 <= len(text.strip()) <= 4000 or '\0' in text
            or not isinstance(conversation_id, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,128}', conversation_id)
            or not isinstance(user, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,128}', user)):
        raise ValueError('Texto o contexto de conversación inválido.')
    owner = hashlib.sha256((identity + '\0' + user).encode()).hexdigest()
    with app.archive.connect() as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('''CREATE TABLE IF NOT EXISTS core_ha_conversations (
            owner TEXT NOT NULL, ha_id TEXT NOT NULL, chat_id TEXT NOT NULL,
            PRIMARY KEY(owner,ha_id))''')
        row = db.execute('''SELECT b.chat_id FROM core_ha_conversations b JOIN chats c ON c.id=b.chat_id
            WHERE b.owner=? AND b.ha_id=?''', (owner, conversation_id)).fetchone()
        if row:
            chat_id = row[0]
        else:
            chat_id = uuid.uuid4().hex
            db.execute('INSERT INTO chats(id,title) VALUES (?,?)', (chat_id, 'Home Assistant · Karen'))
            db.execute('INSERT OR REPLACE INTO core_ha_conversations VALUES (?,?,?)', (owner, conversation_id, chat_id))
            # Do not switch the active desktop/mobile conversation.
    answer = app.core2.chat(text.strip(), app.archive.context(chat_id), preferred=app.config.model)
    from answers import final_answer
    answer = final_answer(answer)
    app.archive.append(chat_id, text.strip(), answer, True)
    return {'answer': answer, 'conversation_id': conversation_id, 'name': 'Karen'}
