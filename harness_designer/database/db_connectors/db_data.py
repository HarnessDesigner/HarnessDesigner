import requests
import tempfile
import os
import zipfile
import shutil


class DBData:

    def __init__(self):
        self._data_dir = None

    def close(self):
        if self._data_dir is not None:
            if os.path.exists(self._data_dir):
                shutil.rmtree(self._data_dir)

    def open(self, splash):
        if self._data_dir is None:
            response = requests.get('https://github.com/HarnessDesigner/database/archive/refs/heads/main.zip', stream=True)
            block_size = 1048576
            cur_size = 0

            splash.SetText(f'Downloading Database Data {cur_size}')

            tmpdir = tempfile.gettempdir()
            tmp_zipfile = os.path.join(tmpdir, 'harness_designer_data.zip')

            if os.path.exists(tmp_zipfile):
                os.remove(tmp_zipfile)

            tmpzipdata = os.path.join(tmpdir, 'harness_designer.database_data')

            if os.path.exists(tmpzipdata):
                shutil.rmtree(tmpzipdata)

            os.makedirs(tmpzipdata)

            with open(tmp_zipfile, "wb") as file:
                for data in response.iter_content(block_size):
                    if not data:
                        break

                    cur_size += len(data)
                    file.write(data)
                    splash.SetText(f'Downloading Database Data {cur_size}')

            splash.SetText(f'Decompressing Database Data...')

            with zipfile.ZipFile(tmp_zipfile) as zdata:
                zdata.extractall(tmpzipdata)

            splash.SetText('Finished Decompressing Data!')

            os.remove(tmp_zipfile)
            self._data_dir = tmpzipdata

        return os.path.join(self._data_dir, 'database-main')

