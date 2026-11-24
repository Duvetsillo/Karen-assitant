"""Read-only/invalid-request checks against the real authenticated local TTS API."""
import json
from pathlib import Path
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def main():
    token = (ROOT / 'voice-models/.expressive-token').read_text().strip()
    active = json.loads((ROOT / 'voice-models/active-voice.json').read_text())
    identity = {'profileId': active['id'], 'referenceSha256': active['reference_sha256']}
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def check(label, path, expected, payload=None, auth=token, origin=None):
        headers = {'Authorization': 'Bearer ' + auth, 'Content-Type': 'application/json'}
        if origin:
            headers['Origin'] = origin
        req = urllib.request.Request('http://127.0.0.1:18790' + path,
            data=None if payload is None else json.dumps(payload).encode(), headers=headers)
        try:
            with opener.open(req, timeout=5) as response:
                status = response.status
                value = json.load(response)
        except urllib.error.HTTPError as error:
            status = error.code
            value = json.load(error)
        assert status == expected, (label, status)
        print(f'{label}: {status}', flush=True)
        return value

    before = check('health', '/health', 200)
    assert before['protocol'] == 2 and all(before[k] == v for k, v in identity.items())
    check('authentication required', '/health', 403, auth='synthetic-invalid-token')
    check('browser origin rejected', '/health', 403, origin='https://example.com')
    check('profile mismatch', '/speech', 409, dict(identity, profileId='synthetic-other', text='Hola.'))
    check('invalid JSON shape', '/speech', 400, [])
    check('invalid style', '/speech', 400, dict(identity, text='Hola.', style='invented'))
    check('empty text', '/speech', 400, dict(identity, text=''))
    after = check('health unchanged', '/health', 200)
    assert before.get('lastSynthesis') == after.get('lastSynthesis')
    print('No synthesis requested by this test.')


if __name__ == '__main__':
    main()
