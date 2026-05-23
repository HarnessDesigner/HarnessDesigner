# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Qt dialog helpers for editing MySQL connector settings."""

import sys

import mysql.connector.constants

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QLineEdit,
    QCheckBox, QSpinBox, QGridLayout, QDialogButtonBox, QFileDialog,
    QPushButton, QComboBox, QScrollArea, QWidget, QSizePolicy,
    QToolTip
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCursor

from .... import config as _config

DBConfig = _config.Config.database
Config = _config.Config.database.mysql

MODE_TOOLTIPS = {
    'ALLOW_INVALID_DATES': 'Do not perform full checking of dates.',
    'ANSI_QUOTES': (
        'Treat " as an identifier quote character (like the ` quote character) '
        'and not as a string quote character.'),
    'ERROR_FOR_DIVISION_BY_ZERO': (
        'Affects handling of division by zero, which includes MOD(N,0).'),
    'HIGH_NOT_PRECEDENCE': (
        'The precedence of the NOT operator is such that expressions such '
        'as NOT a BETWEEN b AND c are parsed as NOT (a BETWEEN b AND c).'),
    'IGNORE_SPACE': 'Permit spaces between a function name and the "(" character.',
    'NO_AUTO_VALUE_ON_ZERO': 'Affects handling of AUTO_INCREMENT columns.',
    'NO_BACKSLASH_ESCAPES': (
        'Disables the use of the backslash character as an escape character '
        'within strings and identifiers.'),
    'NO_DIR_IN_CREATE': (
        'When creating a table, ignore all INDEX DIRECTORY and DATA DIRECTORY directives.'),
    'NO_ENGINE_SUBSTITUTION': (
        'Control automatic substitution of the default storage engine.'),
    'NO_UNSIGNED_SUBTRACTION': (
        'Subtraction between integer values, where one is UNSIGNED, produces unsigned results.'),
    'NO_ZERO_DATE': 'Whether the server permits "0000-00-00" as a valid date.',
    'NO_ZERO_IN_DATE': (
        'Whether the server permits dates in which the year part is nonzero '
        'but the month or day part is 0.'),
    'ONLY_FULL_GROUP_BY': (
        'Reject queries for which the select list, HAVING condition, or ORDER BY list '
        'refer to nonaggregated columns not named in the GROUP BY clause.'),
    'PAD_CHAR_TO_FULL_LENGTH': (
        'Trimming does not occur and retrieved CHAR values are padded to their full length.'),
    'PIPES_AS_CONCAT': (
        'Treat "||" as a string concatenation operator rather than as a synonym for OR.'),
    'REAL_AS_FLOAT': 'Treat REAL as a synonym for FLOAT.',
    'STRICT_ALL_TABLES': 'Enable strict SQL mode for all storage engines.',
    'STRICT_TRANS_TABLES': (
        'Enable strict SQL mode for transactional storage engines.'),
    'TIME_TRUNCATE_FRACTIONAL': (
        'Control whether rounding or truncation occurs when inserting a TIME, DATE, or TIMESTAMP.'),
    'ANSI': 'Equivalent to REAL_AS_FLOAT, PIPES_AS_CONCAT, ANSI_QUOTES, IGNORE_SPACE, ONLY_FULL_GROUP_BY.',
    'TRADITIONAL': (
        'Equivalent to STRICT_TRANS_TABLES, STRICT_ALL_TABLES, NO_ZERO_IN_DATE, '
        'NO_ZERO_DATE, ERROR_FOR_DIVISION_BY_ZERO, and NO_ENGINE_SUBSTITUTION.'),
}


def _file_browse_button(parent, label, initial_value=''):
    """Return (row_widget, line_edit) for a file-browse row."""
    widget = QWidget(parent)
    row = QHBoxLayout(widget)
    row.setContentsMargins(0, 0, 0, 0)
    lbl = QLabel(label, widget)
    row.addWidget(lbl)
    edit = QLineEdit(widget)
    edit.setText(initial_value or '')
    row.addWidget(edit, 1)
    btn = QPushButton('...', widget)
    btn.setFixedWidth(28)

    def _browse():
        """Perform the ``_browse`` operation. UNKNOWN.
        """
        path, _ = QFileDialog.getOpenFileName(widget, f'Select {label}')
        if path:
            edit.setText(path)

    btn.clicked.connect(_browse)
    row.addWidget(btn)
    return widget, edit


class SQLOptionsDialog(QDialog):

    """Collect editable MySQL connector settings from the user.
    """
    def __init__(self, parent):
        """Build the MySQL options dialog.

        :param parent: Parent Qt widget for the options dialog.
        :type parent: UNKNOWN

        :returns: Return value for this callable. UNKNOWN.
        :rtype: UNKNOWN
        """
        super().__init__(parent,
                         Qt.Dialog | Qt.WindowStaysOnTopHint | Qt.WindowCloseButtonHint)
        self.setWindowTitle('MySQL Options')
        size = getattr(Config, 'settings_dialog', None)
        if size and hasattr(size, 'size'):
            w, h = size.size
            self.resize(w, h)
        else:
            self.resize(900, 700)

        pos = getattr(Config, 'settings_dialog', None)
        if pos and hasattr(pos, 'pos') and pos.pos:
            self.move(*pos.pos)

        self.resizeEvent = self._on_size
        self.moveEvent = self._on_move

        outer = QVBoxLayout(self)

        top_row = QHBoxLayout()

        # Connection Settings
        con_group = QGroupBox('Connection Settings', self)
        con_lay = QVBoxLayout(con_group)

        con_lay.addWidget(QLabel('Host:', con_group))
        self.host_ctrl = QLineEdit(Config.host, con_group)
        con_lay.addWidget(self.host_ctrl)

        con_lay.addWidget(QLabel('Port:', con_group))
        self.port_ctrl = QSpinBox(con_group)
        self.port_ctrl.setRange(1, 65535)
        self.port_ctrl.setValue(Config.port)
        con_lay.addWidget(self.port_ctrl)

        ipv6_row = QHBoxLayout()
        ipv6_row.addWidget(QLabel('Force IPV6:', con_group))
        self.force_ipv6_ctrl = QCheckBox(con_group)
        self.force_ipv6_ctrl.setChecked(Config.force_ipv6)
        ipv6_row.addWidget(self.force_ipv6_ctrl)
        con_lay.addLayout(ipv6_row)

        comp_row = QHBoxLayout()
        comp_row.addWidget(QLabel('Compress Protocol:', con_group))
        self.compress_ctrl = QCheckBox(con_group)
        self.compress_ctrl.setChecked(Config.compress)
        comp_row.addWidget(self.compress_ctrl)
        con_lay.addLayout(comp_row)

        top_row.addWidget(con_group)

        # Misc Settings
        misc_group = QGroupBox('Misc Settings', self)
        misc_lay = QVBoxLayout(misc_group)

        buf_row = QHBoxLayout()
        buf_row.addWidget(QLabel('Buffer responses:', misc_group))
        self.buffer_ctrl = QCheckBox(misc_group)
        self.buffer_ctrl.setChecked(Config.buffered)
        buf_row.addWidget(self.buffer_ctrl)
        misc_lay.addLayout(buf_row)

        def _timeout_spin(parent, label, value):
            """Create a labeled timeout spin box row.

            :param parent: Parent widget that owns the spin box.
            :type parent: UNKNOWN
            :param label: Label text displayed for the timeout control.
            :type label: UNKNOWN
            :param value: Initial timeout value, in seconds.
            :type value: UNKNOWN

            :returns: Return value for this callable. UNKNOWN.
            :rtype: UNKNOWN
            """
            r = QHBoxLayout()
            r.addWidget(QLabel(label, parent))
            sp = QSpinBox(parent)
            sp.setRange(0, 60)
            sp.setValue(value or 0)
            r.addWidget(sp)
            misc_lay.addLayout(r)
            return sp

        self.write_timeout_ctrl = _timeout_spin(
            misc_group, 'Write Timeout (sec):', Config.write_timeout)
        self.read_timeout_ctrl = _timeout_spin(
            misc_group, 'Read Timeout (sec):', Config.read_timeout)
        self.connection_timeout_ctrl = _timeout_spin(
            misc_group, 'Connection Timeout (sec):', Config.connection_timeout)

        top_row.addWidget(misc_group)
        outer.addLayout(top_row)

        mid_row = QHBoxLayout()

        # Auth Settings
        auth_group = QGroupBox('Authentication Settings', self)
        auth_lay = QVBoxLayout(auth_group)

        auth_lay.addWidget(QLabel('Auth plugin:', auth_group))
        self.auth_plugin_ctrl = QLineEdit(Config.auth_plugin, auth_group)
        self.auth_plugin_ctrl.textChanged.connect(self._on_auth_plugin)
        auth_lay.addWidget(self.auth_plugin_ctrl)

        # OCI
        oci_group = QGroupBox('OCI Settings', auth_group)
        oci_lay = QVBoxLayout(oci_group)
        oci_file_widget, self.oci_file_ctrl = _file_browse_button(
            oci_group, 'File:', Config.oci_config_file or '')
        self.oci_file_ctrl.textChanged.connect(self._on_oci_file)
        oci_lay.addWidget(oci_file_widget)
        oci_profile_row = QHBoxLayout()
        self.oci_config_profile_label = QLabel('Config Profile:', oci_group)
        oci_profile_row.addWidget(self.oci_config_profile_label)
        self.oci_config_profile_ctrl = QLineEdit(Config.oci_config_profile or '', oci_group)
        oci_profile_row.addWidget(self.oci_config_profile_ctrl)
        oci_lay.addLayout(oci_profile_row)
        if not Config.oci_config_file:
            self.oci_config_profile_ctrl.setEnabled(False)
            self.oci_config_profile_label.setEnabled(False)
        auth_lay.addWidget(oci_group)

        # Open ID
        openid_group = QGroupBox('Open ID Settings', auth_group)
        openid_lay = QVBoxLayout(openid_group)
        openid_widget, self.openid_token_file_ctrl = _file_browse_button(
            openid_group, 'Token File:', Config.openid_token_file or '')
        if Config.auth_plugin != 'authentication_openid_connect_client':
            openid_widget.setEnabled(False)
        openid_lay.addWidget(openid_widget)
        auth_lay.addWidget(openid_group)

        # Kerberos (Windows only)
        if sys.platform.startswith('win'):
            kerb_group = QGroupBox('Kerberos Settings', auth_group)
            kerb_lay = QVBoxLayout(kerb_group)
            kerb_row = QHBoxLayout()
            self.kerberos_auth_mode_label = QLabel('Auth Mode:', kerb_group)
            kerb_row.addWidget(self.kerberos_auth_mode_label)
            self.kerberos_auth_mode_ctrl = QComboBox(kerb_group)
            self.kerberos_auth_mode_ctrl.addItems(['SSPI', 'GSSAPI'])
            idx = self.kerberos_auth_mode_ctrl.findText(
                getattr(Config, 'kerberos_auth_mode', 'SSPI'))
            self.kerberos_auth_mode_ctrl.setCurrentIndex(max(0, idx))
            kerb_row.addWidget(self.kerberos_auth_mode_ctrl)
            kerb_lay.addLayout(kerb_row)
            enabled = Config.auth_plugin == 'authentication_kerberos_client'
            self.kerberos_auth_mode_label.setEnabled(enabled)
            self.kerberos_auth_mode_ctrl.setEnabled(enabled)
            auth_lay.addWidget(kerb_group)

        # SSL
        ssl_group = QGroupBox('SSL', auth_group)
        ssl_lay = QVBoxLayout(ssl_group)

        ssl_top = QHBoxLayout()
        ssl_en_lbl = QLabel('Enable:', ssl_group)
        ssl_top.addWidget(ssl_en_lbl)
        self.ssl_enabled_ctrl = QCheckBox(ssl_group)
        self.ssl_enabled_ctrl.setChecked(not Config.ssl_disabled)
        self.ssl_enabled_ctrl.stateChanged.connect(self._on_ssl_enabled)
        ssl_top.addWidget(self.ssl_enabled_ctrl)

        self.tls_12_label = QLabel('Use TLS 1.2:', ssl_group)
        ssl_top.addWidget(self.tls_12_label)
        self.tls_12_ctrl = QCheckBox(ssl_group)
        self.tls_12_ctrl.setChecked('TLSv1.2' in Config.tls_versions)
        ssl_top.addWidget(self.tls_12_ctrl)

        self.tls_13_label = QLabel('Use TLS 1.3:', ssl_group)
        ssl_top.addWidget(self.tls_13_label)
        self.tls_13_ctrl = QCheckBox(ssl_group)
        self.tls_13_ctrl.setChecked('TLSv1.3' in Config.tls_versions)
        ssl_top.addWidget(self.tls_13_ctrl)
        ssl_lay.addLayout(ssl_top)

        ssl_key_widget, self.ssl_key_file_ctrl = _file_browse_button(
            ssl_group, 'Key File:', Config.ssl_key or '')
        ssl_lay.addWidget(ssl_key_widget)

        ssl_cert_widget, self.ssl_cert_file_ctrl = _file_browse_button(
            ssl_group, 'Certificate File:', Config.ssl_cert or '')
        ssl_lay.addWidget(ssl_cert_widget)

        vc_row = QHBoxLayout()
        self.ssl_verify_cert_label = QLabel('Verify Certificate:', ssl_group)
        vc_row.addWidget(self.ssl_verify_cert_label)
        self.ssl_verify_cert_ctrl = QCheckBox(ssl_group)
        self.ssl_verify_cert_ctrl.setChecked(Config.ssl_verify_cert)
        vc_row.addWidget(self.ssl_verify_cert_ctrl)
        ssl_lay.addLayout(vc_row)

        ssl_ca_widget, self.ssl_ca_file_ctrl = _file_browse_button(
            ssl_group, 'CA File:', Config.ssl_ca or '')
        ssl_lay.addWidget(ssl_ca_widget)

        vi_row = QHBoxLayout()
        self.ssl_verify_identity_label = QLabel('Verify Identity:', ssl_group)
        vi_row.addWidget(self.ssl_verify_identity_label)
        self.ssl_verify_identity_ctrl = QCheckBox(ssl_group)
        self.ssl_verify_identity_ctrl.setChecked(Config.ssl_verify_identity)
        vi_row.addWidget(self.ssl_verify_identity_ctrl)
        ssl_lay.addLayout(vi_row)

        ssl_enabled = not Config.ssl_disabled
        for w in (self.tls_12_ctrl, self.tls_13_ctrl, ssl_key_widget,
                  ssl_cert_widget, self.ssl_verify_cert_ctrl,
                  ssl_ca_widget, self.ssl_verify_identity_ctrl):
            w.setEnabled(ssl_enabled)

        auth_lay.addWidget(ssl_group)
        mid_row.addWidget(auth_group)

        # Database Settings
        db_group = QGroupBox('Database Settings', self)
        db_lay = QVBoxLayout(db_group)

        db_name_row = QHBoxLayout()
        db_name_row.addWidget(QLabel('Database Name:', db_group))
        self.database_name_ctrl = QLineEdit(Config.database_name or '', db_group)
        db_name_row.addWidget(self.database_name_ctrl)
        db_lay.addLayout(db_name_row)

        # SQL Modes
        sql_modes_group = QGroupBox('SQL Modes', db_group)
        sql_modes_lay = QVBoxLayout(sql_modes_group)
        modes_scroll = QScrollArea(sql_modes_group)
        modes_scroll.setWidgetResizable(True)
        modes_container = QWidget()
        gbs = QGridLayout(modes_container)

        current_modes = Config.sql_mode
        modes = mysql.connector.constants.SQLMode.get_full_info()
        self.available_modes = {}
        row_count = -1

        for i, name in enumerate(modes):
            is_set = name in current_modes
            label = QLabel(name + ': ', modes_container)
            ctrl = QCheckBox(modes_container)
            ctrl.setChecked(is_set)
            if name in MODE_TOOLTIPS:
                label.setToolTip(MODE_TOOLTIPS[name])
                ctrl.setToolTip(MODE_TOOLTIPS[name])
            if not i % 2:
                row_count += 1
                gbs.addWidget(label, row_count, 0)
                gbs.addWidget(ctrl, row_count, 1)
            else:
                gbs.addWidget(label, row_count, 2)
                gbs.addWidget(ctrl, row_count, 3)
            self.available_modes[name] = ctrl

        modes_scroll.setWidget(modes_container)
        sql_modes_lay.addWidget(modes_scroll)
        db_lay.addWidget(sql_modes_group)

        # Client Flags
        client_flags_group = QGroupBox('Client Flags', db_group)
        cf_lay = QVBoxLayout(client_flags_group)
        cf_scroll = QScrollArea(client_flags_group)
        cf_scroll.setWidgetResizable(True)
        cf_container = QWidget()
        cf_gbs = QGridLayout(cf_container)

        available_client_flags = {}
        for line in mysql.connector.constants.ClientFlag.get_full_info():
            name, description = line.split(' : ')
            value = getattr(mysql.connector.constants.ClientFlag, name)
            available_client_flags[name] = dict(description=description, value=value)

        row_count = -1
        for i, (name, flag_data) in enumerate(list(available_client_flags.items())):
            is_set = bool(Config.client_flags & flag_data['value'])
            label = QLabel(name + ': ', cf_container)
            ctrl = QCheckBox(cf_container)
            ctrl.setChecked(is_set)
            label.setToolTip(flag_data['description'])
            ctrl.setToolTip(flag_data['description'])
            if not i % 2:
                row_count += 1
                cf_gbs.addWidget(label, row_count, 0)
                cf_gbs.addWidget(ctrl, row_count, 1)
            else:
                cf_gbs.addWidget(label, row_count, 2)
                cf_gbs.addWidget(ctrl, row_count, 3)
            flag_data['ctrl'] = ctrl

        cf_scroll.setWidget(cf_container)
        cf_lay.addWidget(cf_scroll)
        db_lay.addWidget(client_flags_group)

        self.available_client_flags = available_client_flags
        mid_row.addWidget(db_group)
        outer.addLayout(mid_row)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        outer.addWidget(btn_box)

    def GetValue(self):
        """Return the values selected in the MySQL options dialog.

        :returns: The current values collected by the dialog.
        :rtype: UNKNOWN
        """
        tls_versions = []
        if self.tls_12_ctrl.isChecked():
            tls_versions.append('TLSv1.2')
        if self.tls_13_ctrl.isChecked():
            tls_versions.append('TLSv1.3')

        def _timeout(ctrl):
            """Normalize a timeout control value to ``None`` when disabled.

            :param ctrl: Spin box whose timeout value should be normalized.
            :type ctrl: UNKNOWN

            :returns: Return value for this callable. UNKNOWN.
            :rtype: UNKNOWN
            """
            v = ctrl.value()
            return None if v == 0 else v

        sql_mode = [name for name, ctrl in self.available_modes.items()
                    if ctrl.isChecked()]

        client_flags = 0
        for value in self.available_client_flags.values():
            if value['ctrl'].isChecked():
                client_flags |= value['value']

        res = dict(
            host=self.host_ctrl.text(),
            port=self.port_ctrl.value(),
            compress=self.compress_ctrl.isChecked(),
            oci_config_file=self.oci_file_ctrl.text(),
            oci_config_profile=self.oci_config_profile_ctrl.text(),
            force_ipv6=self.force_ipv6_ctrl.isChecked(),
            ssl_verify_identity=self.ssl_verify_identity_ctrl.isChecked(),
            ssl_verify_cert=self.ssl_verify_cert_ctrl.isChecked(),
            ssl_key=self.ssl_key_file_ctrl.text(),
            ssl_disabled=not self.ssl_enabled_ctrl.isChecked(),
            ssl_cert=self.ssl_cert_file_ctrl.text(),
            ssl_ca=self.ssl_ca_file_ctrl.text(),
            tls_versions=tls_versions,
            buffered=self.buffer_ctrl.isChecked(),
            write_timeout=_timeout(self.write_timeout_ctrl),
            read_timeout=_timeout(self.read_timeout_ctrl),
            connection_timeout=_timeout(self.connection_timeout_ctrl),
            client_flags=client_flags,
            sql_mode=sql_mode,
            auth_plugin=self.auth_plugin_ctrl.text(),
            openid_token_file=self.openid_token_file_ctrl.text(),
            database_name=self.database_name_ctrl.text(),
        )

        if sys.platform.startswith('win'):
            res['kerberos_auth_mode'] = self.kerberos_auth_mode_ctrl.currentText()

        return res

    def _on_oci_file(self, value):
        """Enable or disable OCI profile controls based on the selected file.

        :param value: Value or state to persist.
        :type value: UNKNOWN

        :returns: ``None``.
        :rtype: None
        """
        import os
        has_file = bool(value) and os.path.exists(value)
        self.oci_config_profile_ctrl.setEnabled(has_file)
        self.oci_config_profile_label.setEnabled(has_file)

    def _on_size(self, evt):
        """Persist the dialog size when the window is resized.

        :param evt: Qt event object associated with the callback.
        :type evt: UNKNOWN

        :returns: ``None``.
        :rtype: None
        """
        s = evt.size()
        if hasattr(Config, 'settings_dialog') and Config.settings_dialog:
            Config.settings_dialog.size = (s.width(), s.height())
        super().resizeEvent(evt)

    def _on_move(self, evt):
        """Persist the dialog position when the window is moved.

        :param evt: Qt event object associated with the callback.
        :type evt: UNKNOWN

        :returns: ``None``.
        :rtype: None
        """
        p = evt.pos()
        if hasattr(Config, 'settings_dialog') and Config.settings_dialog:
            Config.settings_dialog.pos = (p.x(), p.y())
        super().moveEvent(evt)

    def _on_ssl_enabled(self, state):
        """Enable or disable SSL-related controls.

        :param state: Qt check-state value.
        :type state: UNKNOWN

        :returns: ``None``.
        :rtype: None
        """
        value = bool(state)
        for w in (self.tls_12_ctrl, self.tls_13_ctrl,
                  self.ssl_key_file_ctrl, self.ssl_cert_file_ctrl,
                  self.ssl_verify_cert_ctrl, self.ssl_ca_file_ctrl,
                  self.ssl_verify_identity_ctrl,
                  self.ssl_verify_identity_label, self.ssl_verify_cert_label,
                  self.tls_12_label, self.tls_13_label):
            w.setEnabled(value)

    def _on_auth_plugin(self):
        """Refresh auth-plugin dependent controls after the plugin changes.

        :returns: ``None``.
        :rtype: None
        """
        def _do():
            """Apply delayed auth-plugin UI updates.
            """
            value = self.auth_plugin_ctrl.text()
            self.openid_token_file_ctrl.setEnabled(
                value == 'authentication_openid_connect_client')

            if sys.platform.startswith('win'):
                is_kerb = value == 'authentication_kerberos_client'
                self.kerberos_auth_mode_label.setEnabled(is_kerb)
                self.kerberos_auth_mode_ctrl.setEnabled(is_kerb)

        QTimer.singleShot(0, _do)
