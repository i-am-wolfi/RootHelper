# Shim de compatibilidade Python 3.10+ para o Kanna-X.
# O pyrogram 1.4.16 chama asyncio.get_event_loop() no import (pyrogram/sync.py),
# o que levanta RuntimeError no Python >= 3.10 quando não há loop rodando.
# Este sitecustomize é importado automaticamente no startup se o diretório
# que o contém estiver no PYTHONPATH (o run-kanna.sh já faz isso).
import asyncio

try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

# Backport do MsgId do pyrogram 2.x (wall-clock).
# O MsgId do 1.4.16 calcula perf_counter() - reference_clock + server_time,
# mas server_time só é definido ao RECEBER a primeira mensagem. Numa sessão
# importada (string), o primeiro Ping sai com msg_id ~0 e o Telegram rejeita
# com BadMsgNotification [16]. O 2.x usa time.time() direto — fazemos igual.
try:
    import time as _time
    from pyrogram.session.internals.msg_id import MsgId as _MsgId

    def _wall_clock_new(cls):
        now = int(_time.time())
        cls.msg_id_offset = (cls.msg_id_offset + 4) if now == cls.last_time else 0
        msg_id = (now * 2**32) + cls.msg_id_offset
        cls.last_time = now
        return msg_id

    _MsgId.__new__ = _wall_clock_new
except ImportError:
    pass

# IDs de canais/grupos atuais passam de 2^31 (ex.: -1002707819246).
# O pyrogram 1.4.16 limita MIN_CHANNEL_ID a 32-bit e rejeita esses peers
# ("Peer id invalid"), quebrando logger e comandos no canal de log.
try:
    import pyrogram.utils as _u
    _u.MIN_CHANNEL_ID = -1009999999999999
except ImportError:
    pass

# Aliases ABC removidos de `collections` no Python 3.10+ (ex.: stagger usa
# collections.MutableMapping). Restaura a partir de collections.abc.
try:
    import collections as _c
    import collections.abc as _abc

    for _n in (
        "Callable", "Container", "Hashable", "ItemsView", "Iterable",
        "Iterator", "KeysView", "Mapping", "MappingView", "MutableMapping",
        "MutableSequence", "MutableSet", "Sequence", "Set", "Sized",
        "ValuesView",
    ):
        if not hasattr(_c, _n) and hasattr(_abc, _n):
            setattr(_c, _n, getattr(_abc, _n))
    del _n
except ImportError:
    pass
