"""Check continuity with synthetic data; require local Ollama by default."""
import argparse
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import load_config
from conversations import Conversations
from karen_app import KarenClient

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', help='Modelo Ollama instalado para esta prueba')
    parser.add_argument('--allow-remote', action='store_true',
                        help='Permitir explícitamente un servidor o modelo remoto')
    args = parser.parse_args(argv)
    config = load_config({'model': args.model} if args.model else None)
    if config.backend != 'ollama':
        parser.error('Esta prueba requiere el perfil Ollama.')
    if not args.allow_remote and (
        urlparse(config.server).hostname not in {'127.0.0.1', 'localhost', '::1'} or
        config.model.endswith('-cloud')
    ):
        parser.error('Elige un Ollama local y un modelo instalado, por ejemplo --model gemma3:1b.')
    with tempfile.TemporaryDirectory() as directory:
        archive = Conversations(Path(directory) / 'history.db')
        chat_id = archive.current()
        client = KarenClient(config.server, config.api_key, config.model,
                             config.backend, config.request_timeout)
        available, state = client.test_connection()
        if not available:
            raise SystemExit(state['label'])
        client.archive, client.chat_id = archive, chat_id
        first = client.ask('Para esta prueba, mi palabra clave inventada es mango-742. Confirma brevemente.')
        if first.startswith('Error de conexión:'):
            raise SystemExit(first)
        # Recreate both objects to prove context survives a restart.
        restored = KarenClient(config.server, config.api_key, config.model,
                               config.backend, config.request_timeout)
        restored.archive = Conversations(archive.path)
        restored.chat_id = restored.archive.current()
        second = restored.ask('¿Cuál es mi palabra clave inventada? Responde solo con la palabra.')
        if 'mango-742' not in second.casefold():
            raise SystemExit('Continuidad no confirmada: ' + second)
        print('Continuidad real confirmada después de recuperar el historial: ' + second)


if __name__ == '__main__':
    main()
