"""
This implements an interface to Valkey

If we have 10 failures in a row, stop trying to use the cache.
"""

import os
from typing import Union

from orso.tools import single_item_cache

from opteryx.exceptions import MissingDependencyError
from opteryx.managers.kvstores import BaseKeyValueStore

MAXIMUM_CONSECUTIVE_FAILURES: int = 10


@single_item_cache
def _valkey_server(**kwargs):
    """
    Handling connecting to Valkey
    """
    # the server must be set in the environment
    valkey_config = kwargs.get("server", os.environ.get("REDIS_CONNECTION"))

    if valkey_config is None:
        return None

    try:
        import valkey  # Assuming `valkey` is the client library's name
    except ImportError as err:  # pragma: no cover
        raise MissingDependencyError(err.name) from err

    return valkey.from_url(valkey_config)  # Example instantiation of the client


class ValkeyCache(BaseKeyValueStore):
    """
    Cache object
    """

    def __init__(self, **kwargs):
        """
        Parameters:
            server: string (optional)
                Sets the Valkey server and port (server:port). If not provided
                the value will be obtained from the OS environment.
        """
        self._server = _valkey_server(**kwargs)
        if self._server is None:
            import datetime

            print(f"{datetime.datetime.now()} [CACHE] Unable to set up valkey cache.")
            self._consecutive_failures: int = MAXIMUM_CONSECUTIVE_FAILURES
        else:
            self._consecutive_failures = 0
        self.hits: int = 0
        self.misses: int = 0
        self.skips: int = 0
        self.errors: int = 0
        self.sets: int = 0

    def get(self, key: bytes) -> Union[bytes, None]:
        if self._consecutive_failures >= MAXIMUM_CONSECUTIVE_FAILURES:
            self.skips += 1
            return None
        try:
            response = self._server.get(key)  # Adjust based on Valkey's API
            self._consecutive_failures = 0
            if response:
                self.hits += 1
                return bytes(response)
        except Exception as err:  # pragma: no cover
            self._consecutive_failures += 1
            if self._consecutive_failures >= MAXIMUM_CONSECUTIVE_FAILURES:
                import datetime

                print(
                    f"{datetime.datetime.now()} [CACHE] Disabling remote Valkey cache due to persistent errors ({err})."
                )
            self.errors += 1
            return None

        self.misses += 1
        return None

    def set(self, key: bytes, value: bytes) -> None:
        if self._consecutive_failures < MAXIMUM_CONSECUTIVE_FAILURES:
            try:
                self._server.set(key, value)  # Adjust based on Valkey's API
                self.sets += 1
            except Exception as err:  # pragma: no cover
                # if we fail to set, stop trying
                self._consecutive_failures = MAXIMUM_CONSECUTIVE_FAILURES
                self.errors += 1
                import datetime

                print(
                    f"{datetime.datetime.now()} [CACHE] Disabling remote Valkey cache due to persistent errors ({err}) [SET]."
                )
        else:
            self.skips += 1

    def __del__(self):
        pass
        # DEBUG: log(f"Valkey <hits={self.hits} misses={self.misses} sets={self.sets} skips={self.skips} errors={self.errors}>")