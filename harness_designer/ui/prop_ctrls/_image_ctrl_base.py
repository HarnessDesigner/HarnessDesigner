# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import os
import io
import time
import tempfile
import zipfile

from PIL import Image

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt

from ...image import utils as _image_utils
from ... import image as _image
from ... import resources as _resources


def _pil_to_pixmap(pil_img) -> QPixmap:
    """Convert a PIL RGBA image to QPixmap."""
    pil_img = pil_img.convert('RGBA')
    data = pil_img.tobytes('raw', 'RGBA')
    qimg = QImage(data, pil_img.width, pil_img.height, QImage.Format_RGBA8888)
    return QPixmap.fromImage(qimg)


def _no_image_pixmap() -> QPixmap:
    """Execute the no image pixmap operation.

    UNKNOWN details are inferred from the callable name and signature.

    :returns: Return value. UNKNOWN details.
    :rtype: :class:`QPixmap`
    """
    return _pil_to_pixmap(_image.images.no_image.resize(100, 100).pil_image)


class ImageCtrl(QWidget):
    """Represent an image ctrl in :mod:`harness_designer.ui.prop_ctrls._image_ctrl_base`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent, file_types, original_path, saved_path,
                 support_pdf=False):
        """Initialise the :class:`ImageCtrl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        :param file_types: Value for ``file_types``.
        :type file_types: UNKNOWN
        :param original_path: Value for ``original_path``.
        :type original_path: UNKNOWN
        :param saved_path: Value for ``saved_path``.
        :type saved_path: UNKNOWN
        :param support_pdf: Value for ``support_pdf``.
        :type support_pdf: UNKNOWN
        """
        QWidget.__init__(self, parent)
        self._support_pdf = support_pdf
        self.file_types = file_types

        self._pdf_widget = None  # populated lazily if PDF support needed
        self._path = original_path or ''

        self._image_label = QLabel(self)
        self._image_label.setFrameShape(QFrame.Panel)
        self._image_label.setFrameShadow(QFrame.Sunken)
        self._image_label.setAlignment(Qt.AlignCenter)
        self._image_label.setFixedSize(100, 100)
        self._image_label.setPixmap(_no_image_pixmap())

        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        row.addWidget(self._image_label, stretch=1)
        layout.addLayout(row, stretch=1)
        self.setLayout(layout)

        if saved_path is not None:
            self._load_pil(saved_path)
        elif original_path:
            self.get_image(original_path)

    def SetFileTypes(self, file_types):
        """Execute the set file types operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param file_types: Value for ``file_types``.
        :type file_types: UNKNOWN
        """
        self.file_types = file_types

    def _set_pixmap(self, pixmap: QPixmap):
        """Set the pixmap.

        UNKNOWN details are inferred from the callable name and signature.

        :param pixmap: Value for ``pixmap``.
        :type pixmap: :class:`QPixmap`
        """
        self._image_label.setPixmap(
            pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _set_pdf(self, path):
        """Render the first page of a PDF as a thumbnail in the image label."""
        rendered = False

        # Primary: QPdfDocument (Qt 6.4+)
        try:
            from PySide6.QtPdf import QPdfDocument
            from PySide6.QtCore import QSizeF

            doc = QPdfDocument(None)
            doc.load(path)
            if doc.pageCount() > 0:
                page_size = doc.pagePointSize(0)
                if page_size.width() > 0 and page_size.height() > 0:
                    scale = min(100 / page_size.width(), 100 / page_size.height())
                    render_size = QSizeF(
                        page_size.width() * scale,
                        page_size.height() * scale
                    ).toSize()
                    from PySide6.QtGui import QImage
                    img = doc.render(0, render_size)
                    if not img.isNull():
                        from PySide6.QtGui import QPixmap
                        self._set_pixmap(QPixmap.fromImage(img))
                        rendered = True
            doc.close()
        except (ImportError, Exception):
            pass

        # Fallback: pymupdf
        if not rendered:
            try:
                import fitz
                from PySide6.QtGui import QImage, QPixmap

                doc = fitz.open(path)
                if doc.page_count > 0:
                    page = doc[0]
                    mat = fitz.Matrix(100 / max(page.rect.width, 1),
                                      100 / max(page.rect.height, 1))
                    pix = page.get_pixmap(matrix=mat)
                    img = QImage(pix.samples, pix.width, pix.height,
                                 pix.stride, QImage.Format.Format_RGB888)
                    self._set_pixmap(QPixmap.fromImage(img))
                    rendered = True
                doc.close()
            except (ImportError, Exception):
                pass

        if not rendered:
            self._image_label.setText(f'PDF\n{os.path.basename(path)}')

    def _load_pil(self, path):
        """Load the pil.

        UNKNOWN details are inferred from the callable name and signature.

        :param path: Filesystem path.
        :type path: UNKNOWN
        """
        try:
            img = Image.open(path).convert('RGBA').resize(
                (100, 100), Image.Resampling.LANCZOS)
            self._set_pixmap(_pil_to_pixmap(img))
        except Exception:  # NOQA
            self._set_pixmap(_no_image_pixmap())

    def get_image(self, path) -> bool:
        """Return the image.

        UNKNOWN details are inferred from the callable name and signature.

        :param path: Filesystem path.
        :type path: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        mime_types = self.file_types
        extensions = {'.' + v: k for k, v in self.file_types.items()}

        if path.startswith('http'):
            time.sleep(0.01)
            try:
                response, content_type = _resources.requests_get(path, timeout=1000)
            except Exception:  # NOQA
                self._set_pixmap(_no_image_pixmap())
                return False

            if content_type is not None:
                if content_type in ('application/zip', 'application/x-zip-compressed'):
                    buf = io.BytesIO(response.content)
                    zf = zipfile.ZipFile(buf)
                    for file_name in zf.namelist():
                        ext = os.path.splitext(file_name)[-1]
                        if ext in extensions:
                            break
                    else:
                        self._set_pixmap(_no_image_pixmap())
                        return False
                    data = zf.read(file_name)
                elif content_type in mime_types:
                    ext = mime_types[content_type]
                    data = response.content
                else:
                    self._set_pixmap(_no_image_pixmap())
                    return False
            else:
                matches = [e for e in extensions if e[1:] in path]
                if matches:
                    ext = matches[0]
                    data = response.content
                else:
                    self._set_pixmap(_no_image_pixmap())
                    return False

            tempdir = tempfile.gettempdir()
            image_path = os.path.join(
                tempdir, 'harness_designer_temp_image' + ext)
            with open(image_path, 'wb') as f:
                f.write(data)
        else:
            for ext in extensions:
                if path.endswith(ext):
                    image_path = path
                    break
            else:
                self._set_pixmap(_no_image_pixmap())
                return False

        if image_path.endswith('.pdf') and self._support_pdf:
            self._set_pdf(image_path)
            return True

        try:
            img = Image.open(image_path)
        except Exception:  # NOQA
            self._set_pixmap(_no_image_pixmap())
            return False

        w, h = img.size
        if w > h:
            ratio = h / w
            w, h = 100, int(100 * ratio)
        else:
            ratio = w / h
            w, h = int(100 * ratio), 100

        img = img.resize((w, h), Image.Resampling.LANCZOS)
        canvas = Image.new('RGBA', (100, 100), (0, 0, 0, 0))
        canvas.paste(img, (100 - w, 100 - h))
        self._set_pixmap(_pil_to_pixmap(canvas))
        return True

    def GetValue(self):
        """Execute the get value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        return self._path

    def SetValue(self, value) -> bool:
        """Execute the set value operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        if self.get_image(value):
            self._path = value
            return True
        self._path = ''
        return False
