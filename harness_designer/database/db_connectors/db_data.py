# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Helpers for downloading and unpacking bundled database seed data."""

import requests
import tempfile
import os
import zipfile
import shutil


class DBData:

    """Download and expose external database seed data.
    """
    def __init__(self):
        """Initialize the data download helper.
        """
        self._data_dir = None
        self._alt_path = None

    def close(self):
        """Remove any downloaded data directory managed by this helper.

        :returns: ``None``.
        :rtype: None
        """
        if self._data_dir is not None:
            if os.path.exists(self._data_dir):
                shutil.rmtree(self._data_dir)

    def open(self, splash):
        """Download, unpack, and return the database data directory.

        :param splash: Splash-screen-like object used to report progress.
        :type splash: UNKNOWN

        :returns: Path to the unpacked database data directory.
        :rtype: str
        """
        if self._alt_path is not None:
            return self._alt_path





        if self._data_dir is None:
            response = requests.get('https://github.com/HarnessDesigner/database/archive/refs/heads/main.zip', stream=True)
            block_size = 1048576
            cur_size = 0

            splash.SetText(f'Downloading Database Data {cur_size}')
            splash.flush()

            tmpdir = tempfile.gettempdir()

            tmpzipdata = os.path.join(tmpdir, 'harness_designer.database_data')

            if os.path.exists(tmpzipdata):
                shutil.rmtree(tmpzipdata)

            os.makedirs(tmpzipdata)

            tmp_zipfile = os.path.join(tmpdir, 'harness_designer_data.zip')

            if not os.path.exists(tmp_zipfile):

                with open(tmp_zipfile, "wb") as file:
                    for data in response.iter_content(block_size):
                        if not data:
                            break

                        cur_size += len(data)
                        file.write(data)
                        splash.SetText(f'Downloading Database Data {cur_size}')

            splash.SetText(f'Decompressing Database Data...')
            splash.flush()

            with zipfile.ZipFile(tmp_zipfile) as zdata:
                zdata.extractall(tmpzipdata)

            splash.SetText('Finished Decompressing Data!')
            splash.flush()

            # os.remove(tmp_zipfile)
            self._data_dir = tmpzipdata

        return os.path.join(self._data_dir, 'database-main')

