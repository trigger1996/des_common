"""Exported observation-feedback supervisor: a single memory state C0.

This controller never reads the actual DFA state. All events remain enabled.
"""
import json
from pathlib import Path


class Supervisor:
    def __init__(self):
        data=json.loads((Path(__file__).parent/'supervisor_online.json').read_text(encoding='utf-8'))
        self.memory='C0'
        self._enabled=frozenset(data['full_pattern'])
        self.observable=frozenset(data['observable'])

    def enabled_events(self):
        return self._enabled

    def observe(self,event):
        if event not in self.observable:
            raise ValueError('Only observable events are passed to observe().')
        self.memory='C0'
        return self.memory
