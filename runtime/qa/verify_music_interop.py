"""Actual Node/Python SQLite interop, only with synthetic data in a temporary Core."""
import json
from pathlib import Path
import subprocess
import tempfile
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from karen_core2.memory import ContextMemory


def main():
    root = Path(__file__).resolve().parents[1]
    pet = root.parent / 'pet' if (root.parent / 'pet/package.json').is_file() else root / 'desktop-pet'
    module = pet / 'dist-electron/electron/music-memory.js'
    if not module.is_file():
        raise SystemExit('Compila desktop-pet antes de verificar interoperabilidad musical.')
    script = '''
      import { DatabaseSync } from 'node:sqlite';
      const { MusicMemory } = await import(process.argv[2]);
      const db = new DatabaseSync(process.argv[1]); const memory = new MusicMemory(db);
      const song = {trackId:'synthetic-track',title:'Canción QA',artist:'Artista QA',platform:'spotify'};
      if (process.argv[3]==='clear') memory.clear();
      else {memory.observe(song,'synthetic-play',1000,45,false);memory.preference(song,1,false);}
      db.close();
    '''
    with tempfile.TemporaryDirectory(prefix='karen-music-interop-') as root:
        db = Path(root) / 'core.sqlite'
        memory = ContextMemory(db)
        memory.add('qa', 'Recuerdo sintético que debe conservarse.', source='user')
        args = ['node', '--input-type=module', '-e', script, str(db), module.as_uri()]
        subprocess.run(args, check=True, capture_output=True, text=True, timeout=15)
        result = memory.music.summary()
        assert result['plays'] == 1 and result['estimated_listening_seconds'] == 45
        assert len(result['explicit_likes']) == 1
        subprocess.run(args + ['clear'], check=True, capture_output=True, text=True, timeout=15)
        assert memory.music.history() == []
        with memory.base.connect() as connection:
            assert connection.execute('SELECT count(*) FROM core_memories').fetchone()[0] == 1
        print(json.dumps({'node_python_interop': True, 'explicit_preference': True,
                          'music_clear_preserves_other_memory': True, 'real_databases_touched': False}))


if __name__ == '__main__':
    main()
