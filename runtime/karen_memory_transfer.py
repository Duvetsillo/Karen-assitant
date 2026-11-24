"""One-turn, reviewed memory context for Karen classic."""

import json
import time


class MemoryTransfer:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.snapshot = None
        self.armed = False

    def cancel(self):
        self.snapshot = None
        self.armed = False

    def _valid(self, store, key):
        snapshot = self.snapshot
        if not snapshot or snapshot['key'] != key or self.clock() > snapshot['expires']:
            self.cancel()
            return False
        for memory_id, content in snapshot['rows']:
            current = store.get(memory_id)
            if not current or current['status'] != 'confirmed' or current['content'] != content:
                self.cancel()
                return False
        return True

    def prepare(self, store, project, query, key):
        self.cancel()
        if not isinstance(query, str) or not query.strip() or len(query) > 200:
            raise ValueError('Consulta inválida (1 a 200 caracteres).')
        rows = [row for row in store.list(project, query.strip(), limit=10)
                if row['status'] == 'confirmed'][:3]
        if not rows:
            return 'No encontré recuerdos confirmados y no sensibles para esa consulta.'
        selected = [(row['id'], row['content']) for row in rows]
        self.snapshot = {'key': key, 'rows': selected, 'expires': self.clock() + 300}
        preview = '\n'.join(f"{memory_id}: {content[:400]}" for memory_id, content in selected)
        return ('Vista previa de recuerdos para una sola consulta al modelo. '
                'Pueden salir del PC si el proveedor es remoto.\n' + preview +
                '\nEscribe /memoria enviar para autorizar o /memoria cancelar.')

    def confirm(self, store, key):
        if not self._valid(store, key):
            raise ValueError('La preparación caducó o cambió. Prepara de nuevo.')
        self.armed = True
        return len(self.snapshot['rows'])

    def consume(self, store, key):
        if not self.armed:
            return None
        if not self._valid(store, key):
            return None
        rows = self.snapshot['rows']
        self.cancel()
        return {'rows': rows,
                'context': json.dumps([content[:400] for _, content in rows], ensure_ascii=False)}
