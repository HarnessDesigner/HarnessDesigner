# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""About dialog: application info, update check, and third-party package credits."""

import os
import sys
import platform
import importlib.metadata as _importlib_metadata
from typing import TYPE_CHECKING

import requests
import requests.exceptions

from PySide6 import QtWidgets
from PySide6 import QtCore
from PySide6 import QtGui

from . import dialog_base as _dialog_base
from ... import __version__ as _version

if TYPE_CHECKING:
    from ... import ui as _ui


_RELEASES_URL = (
    'https://api.github.com/repos/HarnessDesigner/HarnessDesigner/releases/latest')
_HOMEPAGE_URL = 'https://github.com/HarnessDesigner/HarnessDesigner'

_LICENSE_FILENAMES = frozenset([
    'LICENSE', 'LICENSE.txt', 'LICENSE.md', 'LICENSE.rst',
    'LICENCE', 'LICENCE.txt', 'LICENCE.md',
    'COPYING', 'COPYING.txt', 'COPYING.rst',
    'NOTICE', 'NOTICE.txt',
])


class _PackageInfo:
    """Metadata for one credited package (a third-party dist, or the interpreter)."""

    def __init__(self, name: str, version: str, summary: str,
                 author: str, homepage: str, license_text: str):
        self.name = name
        self.version = version
        self.summary = summary
        self.author = author
        self.homepage = homepage
        self.license_text = license_text


def _dist_license_text(dist: _importlib_metadata.Distribution) -> str:
    """Read the bundled license file out of a distribution's dist-info, if any."""

    for f in dist.files or ():
        if f.name in _LICENSE_FILENAMES:
            try:
                text = dist.locate_file(f).read_text(encoding='utf-8', errors='replace')
            except (OSError, AttributeError):
                continue
            if text:
                return text

    license_field = (dist.metadata.get('License') or '').strip()
    if license_field and license_field.upper() != 'UNKNOWN':
        return license_field

    return 'No license information was found for this package.'


def _dist_homepage(dist: _importlib_metadata.Distribution) -> str:
    """Best-effort project URL from dist-info metadata."""

    meta = dist.metadata
    home = meta.get('Home-page')
    if home:
        return home

    for entry in meta.get_all('Project-URL') or ():
        label, _, url = entry.partition(',')
        url = url.strip() or label.strip()
        if 'home' in label.lower() or 'source' in label.lower() or url:
            return url

    return ''


def _python_license_text() -> str:
    """Read the CPython license file, falling back to the interpreter's copyright banner."""

    candidate = os.path.join(sys.prefix, 'LICENSE.txt')
    try:
        with open(candidate, 'r', encoding='utf-8') as f:
            return f.read()
    except OSError:
        return sys.copyright


def _collect_packages() -> list[_PackageInfo]:
    """Enumerate every installed distribution plus the Python interpreter.

    Every third-party dependency is bundled into the compiled app alongside its
    ``*.dist-info`` directory (see ``builder/build.py`` ``_clean_dist``), so the
    same ``importlib.metadata`` lookup used here works identically in the dev
    environment and the frozen build.
    """

    packages = []
    seen = set()

    for dist in _importlib_metadata.distributions():
        meta = dist.metadata
        name = meta.get('Name') or dist.name
        if not name:
            continue

        key = name.lower()
        if key in seen:
            continue
        seen.add(key)

        packages.append(_PackageInfo(
            name=name,
            version=dist.version or '',
            summary=meta.get('Summary') or '',
            author=meta.get('Author') or meta.get('Author-email') or '',
            homepage=_dist_homepage(dist),
            license_text=_dist_license_text(dist),
        ))

    packages.append(_PackageInfo(
        name='Python',
        version=platform.python_version(),
        summary='The Python programming language interpreter.',
        author='Python Software Foundation',
        homepage='https://www.python.org',
        license_text=_python_license_text(),
    ))

    packages.sort(key=lambda p: p.name.lower())
    return packages


def _version_tuple(v: str) -> tuple[int, ...]:
    """Numeric (major, minor, micro, ...) parts of a version string, ignoring any suffix."""

    parts = []
    for chunk in v.split('.'):
        digits = ''
        for ch in chunk:
            if not ch.isdigit():
                break
            digits += ch
        parts.append(int(digits) if digits else 0)

    return tuple(parts)


class _UpdateCheckWorker(QtCore.QThread):
    """Fetch the latest GitHub release tag off the main thread."""

    finished_check: QtCore.SignalInstance = QtCore.Signal(bool, str, str)  # success, latest, error

    def run(self):
        try:
            resp = requests.get(
                _RELEASES_URL, timeout=8,
                headers={'Accept': 'application/vnd.github+json'})

            resp.raise_for_status()
            tag = resp.json().get('tag_name', '')
            self.finished_check.emit(True, tag.lstrip('v'), '')

        except (requests.exceptions.RequestException, ValueError) as err:
            self.finished_check.emit(False, '', str(err))


class AboutDialog(_dialog_base.BaseDialog):
    """About box: application info, update check, and third-party package credits."""

    def __init__(self, parent: "_ui.MainFrame"):
        """Initialise the :class:`AboutDialog` instance.

        :param parent: Main application frame.
        :type parent: :class:`_ui.MainFrame`
        """

        _dialog_base.BaseDialog.__init__(
            self, parent, 'About Harness Designer', size=(820, 560),
            button_ids=QtWidgets.QDialogButtonBox.StandardButton.Ok)

        self._update_worker: _UpdateCheckWorker | None = None
        self._packages = _collect_packages()

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal, self.panel)

        self._package_list = QtWidgets.QListWidget(splitter)
        self._package_list.setSelectionMode(
            QtWidgets.QListWidget.SelectionMode.SingleSelection)

        for pkg in self._packages:
            self._package_list.addItem(pkg.name)

        self._package_list.currentRowChanged.connect(self._on_package_selected)

        self._stack = QtWidgets.QStackedWidget(splitter)
        self._about_page = self._build_about_page()
        self._package_page = self._build_package_page()
        self._stack.addWidget(self._about_page)
        self._stack.addWidget(self._package_page)
        self._stack.setCurrentWidget(self._about_page)

        splitter.addWidget(self._package_list)
        splitter.addWidget(self._stack)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([220, 600])

        root = QtWidgets.QVBoxLayout(self.panel)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(splitter)

    # ------------------------------------------------------------------
    # About page
    # ------------------------------------------------------------------
    def _build_about_page(self) -> QtWidgets.QWidget:
        """Build the default "about the software" page."""

        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignTop)

        layout.addSpacing(20)

        name_lbl = QtWidgets.QLabel('Harness Designer')
        font = name_lbl.font()
        font.setPointSize(font.pointSize() + 8)
        font.setBold(True)
        name_lbl.setFont(font)
        name_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(name_lbl)

        version_lbl = QtWidgets.QLabel(f'Version {_version.string}')
        version_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(version_lbl)

        desc_lbl = QtWidgets.QLabel('Wiring harness design software.')
        desc_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(desc_lbl)

        copyright_lbl = QtWidgets.QLabel('© 2025-2026 Kevin G. Schlosser')
        copyright_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(copyright_lbl)

        link_lbl = QtWidgets.QLabel(f'<a href="{_HOMEPAGE_URL}">{_HOMEPAGE_URL}</a>')
        link_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        link_lbl.setOpenExternalLinks(True)
        link_lbl.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextBrowserInteraction)
        layout.addWidget(link_lbl)

        layout.addSpacing(20)

        self._update_btn = QtWidgets.QPushButton('Check for Updates')
        self._update_btn.setFixedWidth(180)
        self._update_btn.clicked.connect(self._on_check_updates)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        btn_row.addWidget(self._update_btn)
        layout.addLayout(btn_row)

        self._update_status_lbl = QtWidgets.QLabel('')
        self._update_status_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        self._update_status_lbl.setWordWrap(True)
        layout.addWidget(self._update_status_lbl)

        layout.addStretch(1)
        return page

    def _on_check_updates(self):
        """Kick off a background check against the GitHub releases API."""

        if self._update_worker is not None and self._update_worker.isRunning():
            return

        self._update_btn.setEnabled(False)
        self._update_status_lbl.setText('Checking for updates…')

        self._update_worker = _UpdateCheckWorker(self)
        self._update_worker.finished_check.connect(self._on_update_check_finished)
        self._update_worker.start()

    def _on_update_check_finished(self, success: bool, latest: str, error: str):
        """Handle the result of the background update check."""

        self._update_btn.setEnabled(True)

        if not success:
            self._update_status_lbl.setText(f'Update check failed: {error}')
            return

        if not latest:
            self._update_status_lbl.setText('No release information was found.')
            return

        if _version_tuple(latest) > _version_tuple(_version.string):
            self._update_status_lbl.setText(
                f'A new version is available: {latest} (you have {_version.string})')
        else:
            self._update_status_lbl.setText('You are running the latest version.')

    # ------------------------------------------------------------------
    # Package detail page
    # ------------------------------------------------------------------
    def _build_package_page(self) -> QtWidgets.QWidget:
        """Build the per-package metadata + license page."""

        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)

        info_layout = QtWidgets.QVBoxLayout()
        info_layout.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignTop)

        self._pkg_name_lbl = QtWidgets.QLabel()
        font = self._pkg_name_lbl.font()
        font.setPointSize(font.pointSize() + 4)
        font.setBold(True)
        self._pkg_name_lbl.setFont(font)
        self._pkg_name_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        info_layout.addWidget(self._pkg_name_lbl)

        self._pkg_version_lbl = QtWidgets.QLabel()
        self._pkg_version_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        info_layout.addWidget(self._pkg_version_lbl)

        self._pkg_summary_lbl = QtWidgets.QLabel()
        self._pkg_summary_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        self._pkg_summary_lbl.setWordWrap(True)
        info_layout.addWidget(self._pkg_summary_lbl)

        self._pkg_author_lbl = QtWidgets.QLabel()
        self._pkg_author_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        self._pkg_author_lbl.setWordWrap(True)
        info_layout.addWidget(self._pkg_author_lbl)

        self._pkg_homepage_lbl = QtWidgets.QLabel()
        self._pkg_homepage_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignHCenter)
        self._pkg_homepage_lbl.setOpenExternalLinks(True)
        self._pkg_homepage_lbl.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextBrowserInteraction)
        info_layout.addWidget(self._pkg_homepage_lbl)

        layout.addLayout(info_layout)
        layout.addSpacing(10)
        layout.addWidget(QtWidgets.QLabel('License:'))

        self._pkg_license_txt = QtWidgets.QPlainTextEdit()
        self._pkg_license_txt.setReadOnly(True)
        mono = QtGui.QFont('Courier New', 9)
        mono.setStyleHint(QtGui.QFont.StyleHint.Monospace)
        self._pkg_license_txt.setFont(mono)
        layout.addWidget(self._pkg_license_txt, 1)

        return page

    def _on_package_selected(self, row: int):
        """Populate the package page for the clicked list entry."""

        if row < 0 or row >= len(self._packages):
            self._stack.setCurrentWidget(self._about_page)
            return

        pkg = self._packages[row]
        self._pkg_name_lbl.setText(pkg.name)
        self._pkg_version_lbl.setText(f'Version {pkg.version}' if pkg.version else '')
        self._pkg_summary_lbl.setText(pkg.summary)
        self._pkg_author_lbl.setText(pkg.author)

        if pkg.homepage:
            self._pkg_homepage_lbl.setText(f'<a href="{pkg.homepage}">{pkg.homepage}</a>')
        else:
            self._pkg_homepage_lbl.setText('')

        self._pkg_license_txt.setPlainText(pkg.license_text)
        self._stack.setCurrentWidget(self._package_page)

    def closeEvent(self, event: QtGui.QCloseEvent):
        """Give the background update-check thread a chance to wind down."""

        if self._update_worker and self._update_worker.isRunning():
            self._update_worker.wait(2000)

        super().closeEvent(event)
