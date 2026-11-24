"""Emit only final speech sentences; never send reasoning to the speaker."""
import re
from answers import final_answer


class FinalSentences:
    def __init__(self, callback):
        self.callback = callback
        self.raw = ''
        self.emitted = 0
        self.deferred = False
        self.finished = False
        self.answer = None

    def add(self, text):
        if self.finished:
            raise ValueError('La respuesta ya ha terminado.')
        self.raw += text
        if self.deferred or self.raw.lstrip().startswith('<'):
            # Reasoning tags can be split across arbitrary network chunks.
            self.deferred = True
            return
        if '```' in self.raw:
            self.deferred = True
            return
        for match in re.compile(r'[.!?](?:\s+|$)').finditer(self.raw, self.emitted):
            end = match.end()
            if end == len(self.raw):
                # Wait for the next chunk: a period may belong to a decimal.
                break
            part = self.raw[self.emitted:end].strip()
            if part:
                self.callback(part)
            self.emitted = end

    def finish(self):
        if self.finished:
            return self.answer
        answer = final_answer(self.raw)
        remainder = answer if self.deferred and self.emitted == 0 else self.raw[self.emitted:].strip()
        self.answer = answer
        self.finished = True
        if remainder:
            self.callback(final_answer(remainder))
        return answer
