from typing import Self


class ContextBase:
    _update_disabled = False
    _ref_count = 0

    def _update_artist(self):
        raise NotImplementedError

    def __enter__(self) -> Self:
        if self._ref_count == 0:
            self._update_disabled = True

        self._ref_count += 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._ref_count -= 1
        if self._ref_count == 0:
            self._update_disabled = False
            self._update_artist()
