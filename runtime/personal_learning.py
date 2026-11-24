"""Explicit personal-source enrollment; no scraping, model training or remote sends."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from urllib.parse import parse_qs, urlsplit

from karen_core2.memory import ContextMemory

PROVIDERS = {'facebook', 'instagram', 'spotify'}


def canonical_profile(provider, value):
    if provider not in PROVIDERS or not isinstance(value, str) or len(value) > 1000:
        raise ValueError('Proveedor o enlace de perfil inválido.')
    parsed = urlsplit(value)
    if parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port is not None or parsed.fragment:
        raise ValueError('Usa un enlace HTTPS público sin credenciales, puerto ni fragmento.')
    host = parsed.hostname
    if provider == 'facebook' and host in {'facebook.com', 'www.facebook.com'}:
        query = parse_qs(parsed.query, keep_blank_values=True)
        if parsed.path != '/profile.php' or set(query) != {'id'} or len(query['id']) != 1 or not re.fullmatch(r'\d{5,30}', query['id'][0]):
            raise ValueError('Usa el enlace Facebook profile.php?id=ID del propietario.')
        return 'https://www.facebook.com/profile.php?id=' + query['id'][0]
    if provider == 'instagram' and host in {'instagram.com', 'www.instagram.com'}:
        handle = parsed.path.strip('/')
        if parsed.query or not re.fullmatch(r'[A-Za-z0-9._]{1,30}', handle):
            raise ValueError('Usa el enlace del perfil Instagram, sin seguimiento ni publicaciones.')
        return 'https://www.instagram.com/' + handle.lower() + '/'
    if provider == 'spotify' and host == 'open.spotify.com':
        match = re.fullmatch(r'/user/([A-Za-z0-9_-]{1,80})/?', parsed.path)
        if parsed.query or not match:
            raise ValueError('Usa un enlace Spotify /user/ID sin parámetros de seguimiento.')
        return 'https://open.spotify.com/user/' + match[1]
    raise ValueError('El dominio no coincide con el proveedor seleccionado.')


class PersonalLearning:
    def __init__(self, path=None, *, project='Personal'):
        self.memory = ContextMemory(path)
        self.project = self.memory.base._project(project)

    def register(self, provider, url):
        """Only a direct user instruction can establish that a profile is theirs."""
        url = canonical_profile(provider, url)
        return self.memory.add(self.project, f'Perfil de {provider} compartido como propio por el usuario: {url}',
            kind='relational', status='confirmed', source='user', priority=5,
            fact_key='profile.' + provider, tags=['perfil', provider],
            details={'record_type': 'personal_source', 'provider': provider,
                     'source_url': url, 'consent': 'explicit_user_instruction'})

    def source(self, identity):
        with self.memory.base.connect() as db:
            row = db.execute('''SELECT m.*,d.details,c.retired FROM core_memories m
                JOIN core2_memory_details d ON d.memory_id=m.id
                JOIN core2_memory c ON c.memory_id=m.id
                WHERE m.id=? AND m.project=? AND m.sensitive=0''', (identity, self.project)).fetchone()
        if not row or row['retired'] or row['status'] != 'confirmed':
            raise ValueError('La fuente debe ser un perfil confirmado y activo de este proyecto.')
        if row['expires_at'] and row['expires_at'] <= datetime.now(timezone.utc).isoformat():
            raise ValueError('La fuente ha caducado.')
        details = json.loads(row['details'])
        if details.get('record_type') != 'personal_source':
            raise ValueError('El recuerdo no es una fuente personal registrada.')
        canonical_profile(details['provider'], details['source_url'])
        return details

    def observe(self, identity, text, *, claim=False, observed_at=None, evidence_url=None):
        """A page observation is a fact about that source, never a verified biography."""
        source = self.source(identity)
        evidence_url = evidence_url or source['source_url']
        if evidence_url != source['source_url']:
            parsed = urlsplit(evidence_url)
            if (source['provider'] != 'spotify' or parsed.scheme != 'https' or parsed.hostname != 'open.spotify.com'
                    or parsed.username or parsed.password or parsed.port is not None or parsed.query or parsed.fragment
                    or not re.fullmatch(r'/playlist/[A-Za-z0-9]{22}', parsed.path)):
                raise ValueError('La evidencia debe ser el perfil registrado o una lista pública Spotify del mismo proveedor.')
        if not isinstance(text, str) or not text.strip() or len(text) > 1800 or type(claim) is not bool:
            raise ValueError('Observación inválida o demasiado extensa.')
        observed_at = observed_at or datetime.now(timezone.utc).isoformat()
        if not isinstance(observed_at, str) or datetime.fromisoformat(observed_at).utcoffset() is None:
            raise ValueError('La fecha de observación requiere zona horaria.')
        day = datetime.fromisoformat(observed_at).astimezone(timezone.utc).date().isoformat()
        label = 'Afirmación pública pendiente de confirmar' if claim else 'Observación de fuente pública'
        content = f'{label} ({day}, {source["provider"]}): {text.strip()}'
        saved = self.memory.add(self.project, content, kind='episodic',
            status='hypothesis' if claim else 'confirmed', state='PENDIENTE' if claim else 'VERIFICADO',
            confidence=.5 if claim else 1.0, source='local-observation', priority=3,
            tags=['fuente-publica', source['provider']],
            details={'record_type': 'source_claim' if claim else 'source_observation',
                     'source_id': identity, 'source_url': source['source_url'],
                     'evidence_url': evidence_url,
                     'observed_at': observed_at, 'biography_confirmed': False})
        self.memory.relate(saved['id'], identity, 'related')
        return saved

    def list(self, query=''):
        return self.memory.retrieve(self.project, query, limit=20)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path)
    parser.add_argument('--project', default='Personal')
    sub = parser.add_subparsers(dest='action', required=True)
    register = sub.add_parser('register')
    register.add_argument('provider', choices=sorted(PROVIDERS))
    register.add_argument('url')
    observe = sub.add_parser('observe')
    observe.add_argument('source_id')
    observe.add_argument('text', help='Hecho observado en la fuente; no inferencias personales.')
    observe.add_argument('--claim', action='store_true', help='La fuente lo afirma; el usuario no lo ha confirmado.')
    observe.add_argument('--observed-at')
    observe.add_argument('--evidence-url', help='Perfil registrado o página Spotify de la lista observada.')
    listing = sub.add_parser('list')
    listing.add_argument('--query', default='')
    args = parser.parse_args()
    engine = PersonalLearning(args.db, project=args.project)
    if args.action == 'register':
        result = engine.register(args.provider, args.url)
    elif args.action == 'observe':
        result = engine.observe(args.source_id, args.text, claim=args.claim, observed_at=args.observed_at,
                                evidence_url=args.evidence_url)
    else:
        result = engine.list(args.query)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
