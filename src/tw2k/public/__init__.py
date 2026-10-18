"""selfhost-beta-v1 (NOTE 61): the Galaxy War Command beta lobby and its game workers.

Nothing here runs unless `tw2k lobby` is started or a worker gets the lobby's env
(``TW2K_PUBLIC_MODE``, ``TW2K_BASE_PATH``, ``TW2K_BRAND``, ...). A plain ``tw2k serve``
with none of them set is the old server.
"""
