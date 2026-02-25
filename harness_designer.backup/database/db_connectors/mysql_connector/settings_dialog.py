import sys

import wx
import wx.lib.filebrowsebutton as filebrowse
import mysql.connector.constants

from harness_designer import Config

DBConfig = Config.database
Config = Config.database.mysql


class BoxedGroup(wx.StaticBox):
    def __init__(self, parent, label=""):
        wx.StaticBox.__init__(self, parent, wx.ID_ANY, label)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.items = []
        topBorder, otherBorder = self.GetBordersForSizer()
        self.sizer.AddSpacer(topBorder)

        self.SetSizer(self.sizer)

        self.Add = self.sizer.Add

    def AppendItems(self, *items):
        line_sizer = wx.BoxSizer(wx.HORIZONTAL)

        ret = []

        for item in items:
            if isinstance(item, str):
                label_ctrl = wx.StaticText(self, label=item)
                line_sizer.Add(label_ctrl, 0,
                               wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 5)
                self.items.append([label_ctrl])
                ret.append(label_ctrl)

            elif isinstance(item, (list, tuple)):
                line_items = []
                for subitem in item:
                    if isinstance(subitem, str):
                        subitem = wx.StaticText(self, label=subitem)
                        line_sizer.Add(subitem, 0,
                                       wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 5)
                        ret.append(subitem)
                    else:
                        line_sizer.Add(subitem, 1, wx.ALL | wx.EXPAND, 5)
                    line_items.append(subitem)

                self.items.append(line_items)

            else:
                line_sizer.Add(item, 1, wx.ALL | wx.EXPAND, 5)
                self.items.append([item])

            self.sizer.Add(line_sizer, 0, wx.EXPAND)

        return ret


MODE_TOOLTIPS = {
    'ALLOW_INVALID_DATES': (
        'Do not perform full checking of dates.'
    ),
    'ANSI_QUOTES': (
        'Treat " as an identifier quote character (like the ` quote character)\n'
        'and not as a string quote character.'
    ),
    'ERROR_FOR_DIVISION_BY_ZERO': (
        'Affects handling of division by zero, which includes MOD(N,0).'
    ),
    'HIGH_NOT_PRECEDENCE': (
        'The precedence of the NOT operator is such that expressions such\n'
        'as NOT a BETWEEN b AND c are parsed as NOT (a BETWEEN b AND c).'
    ),
    'IGNORE_SPACE': (
        'Permit spaces between a function name and the "(" character.'
    ),
    'NO_AUTO_VALUE_ON_ZERO': (
        'Affects handling of AUTO_INCREMENT columns.'
    ),
    'NO_BACKSLASH_ESCAPES': (
        'Disables the use of the backslash character (\\) as an escape\n'
        'character within strings and identifiers.'
    ),
    'NO_DIR_IN_CREATE': (
        'When creating a table, ignore all INDEX DIRECTORY and\n'
        'DATA DIRECTORY directives.'
    ),
    'NO_ENGINE_SUBSTITUTION': (
        'Control automatic substitution of the default storage engine when a\n'
        'statement such as CREATE TABLE or ALTER TABLE specifies a storage\n'
        'engine that is disabled or not compiled in.'
    ),
    'NO_UNSIGNED_SUBTRACTION': (
        'Subtraction between integer values, where one is of type UNSIGNED,\n'
        'produces an unsigned result by default.'
    ),
    'NO_ZERO_DATE': (
        'Whether the server permits "0000-00-00" as a valid date.'
    ),
    'NO_ZERO_IN_DATE': (
        'Whether the server permits dates in which the year part is nonzero\n'
        'but the month or day part is 0.'
    ),
    'ONLY_FULL_GROUP_BY': (
        'Reject queries for which the select list, HAVING condition, or\n'
        'ORDER BY list refer to nonaggregated columns that are neither\n'
        'named in the GROUP BY clause nor are functionally dependent on\n'
        '(uniquely determined by) GROUP BY columns.'
    ),
    'PAD_CHAR_TO_FULL_LENGTH': (
        'Trimming does not occur and retrieved CHAR values\n'
        'are padded to their full length.'
    ),
    'PIPES_AS_CONCAT': (
        'Treat "||" as a string concatenation operator\n'
        '(same as CONCAT()) rather than as a synonym for OR.'
    ),
    'REAL_AS_FLOAT': (
        'Treat REAL as a synonym for FLOAT. By default,\n'
        'MySQL treats REAL as a synonym for DOUBLE.'
    ),
    'STRICT_ALL_TABLES': (
        'Enable strict SQL mode for all storage engines.'
    ),
    'STRICT_TRANS_TABLES': (
        'Enable strict SQL mode for transactional storage engines,\n'
        'and when possible for nontransactional storage engines.'
    ),
    'TIME_TRUNCATE_FRACTIONAL': (
        'Control whether rounding or truncation occurs when\n'
        'inserting a TIME, DATE, or TIMESTAMP value.'
    ),
    'ANSI': (
        'Equivalent to REAL_AS_FLOAT, PIPES_AS_CONCAT,\n'
        'ANSI_QUOTES, IGNORE_SPACE, and ONLY_FULL_GROUP_BY.'
    ),
    'TRADITIONAL': (
        'Equivalent to STRICT_TRANS_TABLES, STRICT_ALL_TABLES,\n'
        'NO_ZERO_IN_DATE, NO_ZERO_DATE, ERROR_FOR_DIVISION_BY_ZERO,\n'
        'and NO_ENGINE_SUBSTITUTION.'
    )
}


class SQLOptionsDialog(wx.Dialog):

    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, wx.ID_ANY, size=Config.settings_dialog.size,
                           title='MySQL Options', pos=Config.settings_dialog.pos,
                           style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.STAY_ON_TOP)

        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_MOVE, self.on_move)

        con_group = BoxedGroup(self, 'Connection Settings')
        misc_group = BoxedGroup(self, 'Misc Settings')

        host_ctrl = wx.TextCtrl(con_group, wx.ID_ANY, value=Config.host)
        con_group.AppendItems(('Host:', host_ctrl))

        port_ctrl = wx.SpinCtrl(
            con_group, wx.ID_ANY, value=str(Config.port),
            initial=Config.port, min=1, max=65535)

        con_group.AppendItems(('Port:', port_ctrl))

        force_ipv6_ctrl = wx.CheckBox(con_group, wx.ID_ANY, label='')
        force_ipv6_ctrl.SetValue(Config.force_ipv6)
        con_group.AppendItems(('Force IPV6:', force_ipv6_ctrl))

        compress_ctrl = wx.CheckBox(con_group, wx.ID_ANY, label='')
        compress_ctrl.SetValue(Config.compress)
        con_group.AppendItems(('Compress Protocol:', compress_ctrl))

        buffer_ctrl = wx.CheckBox(misc_group, wx.ID_ANY, label='')
        buffer_ctrl.SetValue(Config.buffered)
        misc_group.AppendItems(('Buffer responses:', buffer_ctrl))

        if Config.write_timeout is None:
            write_timeout = 0
        else:
            write_timeout = Config.write_timeout

        write_timeout_ctrl = wx.SpinCtrl(
            misc_group, wx.ID_ANY, value=str(write_timeout),
            initial=write_timeout, min=0, max=60)

        misc_group.AppendItems(('Write Timeout (sec):', write_timeout_ctrl))

        if Config.read_timeout is None:
            read_timeout = 0
        else:
            read_timeout = Config.read_timeout

        read_timeout_ctrl = wx.SpinCtrl(
            misc_group, wx.ID_ANY, value=str(read_timeout),
            initial=read_timeout, min=0, max=60)

        misc_group.AppendItems(('Read Timeout (sec):', read_timeout_ctrl))

        if Config.connection_timeout is None:
            connection_timeout = 0
        else:
            connection_timeout = Config.connection_timeout

        connection_timeout_ctrl = wx.SpinCtrl(
            misc_group, wx.ID_ANY, value=str(connection_timeout),
            initial=connection_timeout, min=0, max=60)

        misc_group.AppendItems(('Connection Timeout (sec):', connection_timeout_ctrl))

        auth_group = BoxedGroup(self, 'Authentication Settings')

        auth_plugin_ctrl = wx.TextCtrl(
            auth_group, wx.ID_ANY, value=Config.auth_plugin)
        auth_group.AppendItems(('Auth plugin:', auth_plugin_ctrl))

        auth_plugin_ctrl.Bind(wx.EVT_CHAR, self.on_auth_plugin)

        oci_group = BoxedGroup(auth_group, 'OCI Settings')
        auth_group.Add(oci_group, 1, wx.EXPAND | wx.ALL, 10)

        oci_file_ctrl = filebrowse.FileBrowseButton(
            oci_group, wx.ID_ANY, labelText='File:')
        oci_config_profile_ctrl = wx.TextCtrl(
            oci_group, wx.ID_ANY, value=Config.oci_config_profile)

        oci_group.AppendItems(oci_file_ctrl)
        self.oci_config_profile_label = oci_group.AppendItems(
            ('Config Profile:', oci_config_profile_ctrl))[0]

        if Config.oci_config_file:
            oci_file_ctrl.SetValue(Config.oci_config_file)
        else:
            oci_config_profile_ctrl.Enable(False)
            self.oci_config_profile_label.Enable(False)

        oci_file_ctrl.Bind(wx.EVT_FILECTRL_SELECTIONCHANGED, self.on_oci_file)

        openid_group = BoxedGroup(auth_group, 'Open ID Settings')
        auth_group.Add(openid_group, 1, wx.EXPAND | wx.ALL, 10)

        openid_token_file_ctrl = filebrowse.FileBrowseButton(
            openid_group, wx.ID_ANY, labelText='Token File:')

        if Config.openid_token_file:
            openid_token_file_ctrl.SetValue(Config.openid_token_file)

        if Config.auth_plugin != 'authentication_openid_connect_client':
            openid_token_file_ctrl.Enable(False)

        openid_group.AppendItems(openid_token_file_ctrl)

        if sys.platform.startswith('win'):
            kerberos_group = BoxedGroup(auth_group, 'Kerberos Settings')
            auth_group.Add(kerberos_group, 1, wx.EXPAND | wx.ALL, 10)

            kerberos_auth_mode_ctrl = wx.Choice(
                kerberos_group, wx.ID_ANY, choices=['SSPI', 'GSSAPI'])
            kerberos_auth_mode_ctrl.SetStringSelection(Config.kerberos_auth_mode)

            self.kerberos_auth_mode_label = kerberos_group.AppendItems(
                ('Auth Mode:', kerberos_auth_mode_ctrl))[0]
            self.kerberos_auth_mode_ctrl = kerberos_auth_mode_ctrl

            self.kerberos_auth_mode_label.Enable(
                Config.auth_plugin == 'authentication_kerberos_client')
            kerberos_auth_mode_ctrl.Enable(
                Config.auth_plugin == 'authentication_kerberos_client')

        ssl_group = BoxedGroup(auth_group, 'SSL')
        auth_group.Add(ssl_group, 1, wx.EXPAND | wx.ALL, 10)

        h_sizer = wx.BoxSizer(wx.HORIZONTAL)

        ssl_enabled_label = wx.StaticText(ssl_group, wx.ID_ANY, label='Enable:')
        ssl_enabled_ctrl = wx.CheckBox(ssl_group, wx.ID_ANY, label='')
        ssl_enabled_ctrl.SetValue(not Config.ssl_disabled)

        h_sizer.Add(ssl_enabled_label, 0, wx.EXPAND | wx.LEFT | wx.TOP | wx.BOTTOM, 10)
        h_sizer.Add(ssl_enabled_ctrl, 0, wx.EXPAND | wx.ALL, 10)

        ssl_enabled_ctrl.Bind(wx.EVT_CHECKBOX, self.on_ssl_enabled)

        tls_12_label = wx.StaticText(ssl_group, wx.ID_ANY, label='Use TLS 1.2:')
        tls_12_ctrl = wx.CheckBox(ssl_group, wx.ID_ANY, label='')
        tls_12_ctrl.SetValue('TLSv1.2' in Config.tls_versions)
        h_sizer.Add(tls_12_label, 0, wx.EXPAND | wx.LEFT | wx.TOP | wx.BOTTOM, 10)
        h_sizer.Add(tls_12_ctrl, 0, wx.EXPAND | wx.ALL, 10)

        tls_13_label = wx.StaticText(ssl_group, wx.ID_ANY, label='Use TLS 1.3:')
        tls_13_ctrl = wx.CheckBox(ssl_group, wx.ID_ANY, label='')
        tls_13_ctrl.SetValue('TLSv1.2' in Config.tls_versions)
        h_sizer.Add(tls_13_label, 0, wx.EXPAND | wx.LEFT | wx.TOP | wx.BOTTOM, 10)
        h_sizer.Add(tls_13_ctrl, 0, wx.EXPAND | wx.ALL, 10)

        ssl_group.Add(h_sizer, 1, wx.EXPAND)

        self.tls_12_label = tls_12_label
        self.tls_13_label = tls_13_label

        ssl_key_file_ctrl = filebrowse.FileBrowseButton(
            ssl_group, wx.ID_ANY, labelText='Key File:')

        if Config.ssl_key:
            ssl_key_file_ctrl.SetValue(Config.ssl_key)

        ssl_group.AppendItems(ssl_key_file_ctrl)

        ssl_cert_file_ctrl = filebrowse.FileBrowseButton(
            ssl_group, wx.ID_ANY, labelText='Certificate File:')

        if Config.ssl_cert:
            ssl_cert_file_ctrl.SetValue(Config.ssl_cert)

        ssl_group.AppendItems(ssl_cert_file_ctrl)

        ssl_verify_cert_ctrl = wx.CheckBox(ssl_group, wx.ID_ANY, label='')
        ssl_verify_cert_ctrl.SetValue(Config.ssl_verify_cert)

        self.ssl_verify_cert_label = ssl_group.AppendItems(
            ('Verify Certificate:', ssl_verify_cert_ctrl))[0]

        ssl_ca_file_ctrl = filebrowse.FileBrowseButton(
            ssl_group, wx.ID_ANY, labelText='CA File:')

        if Config.ssl_ca:
            ssl_ca_file_ctrl.SetValue(Config.ssl_ca)

        ssl_group.AppendItems(ssl_ca_file_ctrl)

        ssl_verify_identity_ctrl = wx.CheckBox(ssl_group, wx.ID_ANY, label='')
        ssl_verify_identity_ctrl.SetValue(Config.ssl_verify_identity)

        self.ssl_verify_identity_label = ssl_group.AppendItems(
            ('Verify Identity:', ssl_verify_identity_ctrl))[0]

        tls_12_ctrl.Enable(not Config.ssl_disabled)
        tls_13_ctrl.Enable(not Config.ssl_disabled)
        ssl_key_file_ctrl.Enable(not Config.ssl_disabled)
        ssl_cert_file_ctrl.Enable(not Config.ssl_disabled)
        ssl_verify_cert_ctrl.Enable(not Config.ssl_disabled)
        ssl_ca_file_ctrl.Enable(not Config.ssl_disabled)
        ssl_verify_identity_ctrl.Enable(not Config.ssl_disabled)

        database_group = BoxedGroup(self, 'Database Settings')
        sql_modes_group = BoxedGroup(database_group, 'SQL Modes')

        database_name_ctrl = wx.TextCtrl(
            database_group, wx.ID_ANY, value=Config.database_name)

        database_group.AppendItems(
            ('Database Name:', database_name_ctrl))

        current_modes = Config.sql_mode
        modes = mysql.connector.constants.SQLMode.get_full_info()

        gbs = wx.GridBagSizer(vgap=0, hgap=5)

        available_modes = {}
        row_count = -1

        for i, name in enumerate(modes):
            is_set = name in current_modes

            label = wx.StaticText(
                sql_modes_group, wx.ID_ANY, label=name + ': ')

            ctrl = wx.CheckBox(sql_modes_group, wx.ID_ANY, label='')
            ctrl.SetValue(is_set)

            if not i % 2:
                row_count += 1
                gbs.Add(label, (row_count, 0), (0, 0), wx.EXPAND | wx.LEFT, 10)
                gbs.Add(ctrl, (row_count, 1), (0, 0), wx.EXPAND | wx.RIGHT, 10)
            else:
                gbs.Add(label, (row_count, 2), (0, 0), wx.EXPAND | wx.LEFT, 10)
                gbs.Add(ctrl, (row_count, 3), (0, 0), wx.EXPAND | wx.RIGHT, 10)

            if name in MODE_TOOLTIPS:
                label.SetToolTip(MODE_TOOLTIPS[name])
                ctrl.SetToolTip(MODE_TOOLTIPS[name])

            available_modes[name] = ctrl

        sql_modes_group.Add(gbs, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 30)
        database_group.Add(sql_modes_group, 1, wx.EXPAND | wx.ALL, 10)

        client_flags_group = BoxedGroup(database_group, 'Client Flags')

        gbs = wx.GridBagSizer(vgap=0, hgap=5)

        available_client_flags = {}
        row_count = -1

        for line in mysql.connector.constants.ClientFlag.get_full_info():
            name, description = line.split(' : ')
            value = getattr(mysql.connector.constants.ClientFlag, name)

            available_client_flags[name] = dict(description=description, value=value)

        for i, (name, flag_data) in enumerate(list(available_client_flags.items())):
            is_set = bool(Config.client_flags & flag_data['value'])

            label = wx.StaticText(
                client_flags_group, wx.ID_ANY, label=name + ': ')

            ctrl = wx.CheckBox(client_flags_group, wx.ID_ANY, label='')
            ctrl.SetValue(is_set)

            if not i % 2:
                row_count += 1
                gbs.Add(label, (row_count, 0), (0, 0), wx.EXPAND | wx.LEFT, 10)
                gbs.Add(ctrl, (row_count, 1), (0, 0), wx.EXPAND | wx.RIGHT, 10)
            else:
                gbs.Add(label, (row_count, 2), (0, 0), wx.EXPAND | wx.LEFT, 10)
                gbs.Add(ctrl, (row_count, 3), (0, 0), wx.EXPAND | wx.RIGHT, 10)

            label.SetToolTip(flag_data['description'])
            ctrl.SetToolTip(flag_data['description'])

            flag_data['ctrl'] = ctrl

        client_flags_group.Add(gbs, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 30)
        database_group.Add(client_flags_group, 1, wx.EXPAND | wx.ALL, 10)

        button_sizer = self.CreateSeparatedButtonSizer(wx.OK | wx.CANCEL)

        sizer = wx.BoxSizer(wx.VERTICAL)
        h_sizer = wx.BoxSizer(wx.HORIZONTAL)

        h_sizer.Add(con_group, 1, wx.EXPAND | wx.ALL, 5)
        h_sizer.Add(misc_group, 1, wx.EXPAND | wx.ALL, 5)
        sizer.Add(h_sizer, 1, wx.EXPAND | wx.ALL, 5)

        h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        h_sizer.Add(auth_group, 1, wx.EXPAND | wx.ALL, 5)
        h_sizer.Add(database_group, 1, wx.EXPAND | wx.ALL, 5)
        sizer.Add(h_sizer, 1, wx.EXPAND | wx.ALL, 5)
        sizer.Add(button_sizer, 0, wx.EXPAND | wx.ALL, 10)

        self.SetSizer(sizer)

        self.host_ctrl = host_ctrl
        self.port_ctrl = port_ctrl
        self.force_ipv6_ctrl = force_ipv6_ctrl
        self.compress_ctrl = compress_ctrl
        self.oci_file_ctrl = oci_file_ctrl
        self.oci_config_profile_ctrl = oci_config_profile_ctrl
        self.buffer_ctrl = buffer_ctrl
        self.write_timeout_ctrl = write_timeout_ctrl
        self.read_timeout_ctrl = read_timeout_ctrl
        self.connection_timeout_ctrl = connection_timeout_ctrl
        self.auth_plugin_ctrl = auth_plugin_ctrl
        self.openid_token_file_ctrl = openid_token_file_ctrl
        self.database_name_ctrl = database_name_ctrl
        self.ssl_verify_identity_ctrl = ssl_verify_identity_ctrl
        self.ssl_verify_cert_ctrl = ssl_verify_cert_ctrl
        self.ssl_enabled_ctrl = ssl_enabled_ctrl
        self.ssl_key_file_ctrl = ssl_key_file_ctrl
        self.ssl_cert_file_ctrl = ssl_cert_file_ctrl
        self.ssl_ca_file_ctrl = ssl_ca_file_ctrl
        self.tls_12_ctrl = tls_12_ctrl
        self.tls_13_ctrl = tls_13_ctrl

        self.available_modes = available_modes
        self.available_client_flags = available_client_flags

        self.CenterOnParent()

    def GetValue(self):
        tls_versions = []
        if self.tls_12_ctrl.GetValue():
            tls_versions.append('TLSv1.2')
        if self.tls_13_ctrl.GetValue():
            tls_versions.append('TLSv1.3')

        wt = self.connection_timeout_ctrl.GetValue()
        if wt == 0:
            wt = None

        rt = self.connection_timeout_ctrl.GetValue()
        if rt == 0:
            rt = None

        ct = self.connection_timeout_ctrl.GetValue()
        if ct == 0:
            ct = None

        sql_mode = []
        for name, ctrl in self.available_modes.items():
            if ctrl.GetValue():
                sql_mode.append(name)

        client_flags = 0

        for value in self.available_client_flags.values():
            if value['ctrl'].GetValue():
                client_flags |= value['value']

        res = dict(
            host=self.host_ctrl.GetValue(),
            port=self.port_ctrl.GetValue(),
            compress=self.compress_ctrl.GetValue(),
            oci_config_file=self.oci_file_ctrl.GetValue(),
            oci_config_profile=self.oci_config_profile_ctrl.GetValue(),
            force_ipv6=self.force_ipv6_ctrl.GetValue(),
            ssl_verify_identity=self.ssl_verify_identity_ctrl.GetValue(),
            ssl_verify_cert=self.ssl_verify_cert_ctrl.GetValue(),
            ssl_key=self.ssl_key_file_ctrl.GetValue(),
            ssl_disabled=not self.ssl_enabled_ctrl.GetValue(),
            ssl_cert=self.ssl_cert_file_ctrl.GetValue(),
            ssl_ca=self.ssl_ca_file_ctrl.GetValue(),
            tls_versions=tls_versions,
            buffered=self.buffer_ctrl.GetValue(),
            write_timeout=wt,
            read_timeout=rt,
            connection_timeout=ct,
            client_flags=client_flags,
            sql_mode=sql_mode,
            auth_plugin=self.auth_plugin_ctrl.GetValue(),
            openid_token_file=self.openid_token_file_ctrl.GetValue(),
            database_name=self.database_name_ctrl.GetValue(),
        )

        if sys.platform.startswith('win'):
            res['kerberos_auth_mode'] = self.kerberos_auth_mode_ctrl.GetStringSelection()

        return res

    def on_oci_file(self, evt):
        import os

        value = self.oci_file_ctrl.GetValue()
        if value and os.path.exists(value):
            self.oci_config_profile_ctrl.Enable(True)
            self.oci_config_profile_label.Enable(True)
        else:
            self.oci_config_profile_ctrl.Enable(False)
            self.oci_config_profile_label.Enable(False)

        evt.Skip()

    def on_size(self, evt):  # NOQA
        Config.size = evt.GetSize()[:2]
        evt.Skip()

    def on_move(self, evt):  # NOQA
        Config.pos = evt.GetPosition()[:2]
        evt.Skip()

    def on_ssl_enabled(self, evt):
        value = self.ssl_enabled_ctrl.GetValue()
        self.tls_12_ctrl.Enable(value)
        self.tls_13_ctrl.Enable(value)
        self.ssl_key_file_ctrl.Enable(value)
        self.ssl_cert_file_ctrl.Enable(value)
        self.ssl_verify_cert_ctrl.Enable(value)
        self.ssl_ca_file_ctrl.Enable(value)
        self.ssl_verify_identity_ctrl.Enable(value)
        self.ssl_verify_identity_label.Enable(value)
        self.ssl_verify_cert_label.Enable(value)
        self.tls_12_label.Enable(value)
        self.tls_13_label.Enable(value)
        evt.Skip()

    def on_auth_plugin(self, evt):

        def _do():
            value = self.auth_plugin_ctrl.GetValue()
            self.openid_token_file_ctrl.Enable(
                value == 'authentication_openid_connect_client')

            if sys.platform.startswith('win'):
                self.kerberos_auth_mode_label.Enable(
                    value == 'authentication_kerberos_client')

                self.kerberos_auth_mode_ctrl.Enable(
                    value == 'authentication_kerberos_client')

        wx.CallAfter(_do)
        evt.Skip()
