import os

try:
    from . import utils_
except ImportError:
    import utils_

IGNORE_FILES = [
    'dbg.py',
    'sliceshell.py',
    'crustslices.py',
    'pydocview.py',
    'xmltopicdefnprovider.py',
    'basic.py',
    'imagelist.py',
    'timectrl.py',
    'maskededit.py',
    'langlistctrl.py',
    'intctrl.py',
    'inspection.py',
    'graphics.py',
    'evtmgr.py',
    'docview.py',
    'dialogs.py',
    'CDate.py',
    'ultimatelistctrl.py'
]


def run():
    import wx

    wx_path = os.path.dirname(wx.__file__)

    cfiles = utils_.iter_mod_path(wx_path, ignore_files=IGNORE_FILES)

    from Cython.Build import Cythonize

    try:
        Cythonize.main(['-3', '--build', f'--parallel={os.cpu_count()}', '--inplace', '--keep-going'] + cfiles)
    except RuntimeError:
        pass
    else:
        utils_.cleanup_after_compile(wx_path, False)


r'''
[1/1] Cythonizing c:\python3.11.14\Lib\site-packages\wx\tools\dbg.py

Error compiling Cython file:
------------------------------------------------------------
...
        self._outstream = sys.stdout  # default output stream
        self._outstream_stack = []    # for restoration of streams as necessary


    def IsEnabled():
        return self._dbg
               ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\tools\dbg.py:135:15: undeclared name not builtin: self

Error compiling Cython file:
------------------------------------------------------------
...

    def IsEnabled():
        return self._dbg

    def IsSuspended():
        return _suspend
               ^
------------------------------------------------------------





[1/1] Cythonizing c:\python3.11.14\Lib\site-packages\wx\py\sliceshell.py

Error compiling Cython file:
------------------------------------------------------------
...
        self.SetCurrentPos(endpos)
        self.SetSelection(startpos, endpos)
        self.ReplaceSelection('')

        hasSyntaxError=False
        result = self.BreakTextIntoCommands(command)
                                            ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\py\sliceshell.py:3473:44: local variable 'command' referenced before assignment

Error compiling Cython file:
------------------------------------------------------------
...
        self.ReplaceSelection('')

        hasSyntaxError=False
        result = self.BreakTextIntoCommands(command)
        if result[0] is None:
            commands=[command]
                      ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\py\sliceshell.py:3475:22: local variable 'command' referenced before assignment

Error compiling Cython file:
------------------------------------------------------------
...
        """Create new buffer."""
        self.bufferDestroy()
        buffer = Buffer()
        self.panel = panel = wx.Panel(parent=self, id=-1)
        panel.Bind (wx.EVT_ERASE_BACKGROUND, lambda x: x)
        editor = Editor(parent=panel)
                 ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\py\sliceshell.py:300:17: undeclared name not builtin: Editor

Error compiling Cython file:
------------------------------------------------------------
...
        #unique (no duplicate words
        #oneliner from german python forum => unique list
        unlist = [thlist[i] for i in xrange(len(thlist)) if thlist[i] not in thlist[:i]]

        #sort lowercase
        unlist.sort(key=cmp_to_key(lambda a, b: cmp(a.lower(), b.lower())))
                                                ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\py\sliceshell.py:2149:48: undeclared name not builtin: cmp



[1/1] Cythonizing c:\python3.11.14\Lib\site-packages\wx\py\crustslices.py

Error compiling Cython file:
------------------------------------------------------------
...
        return False

    def bufferCreate(self, filename=None):
        """Create new buffer."""
        self.bufferDestroy()
        buffer = Buffer()
                 ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\py\crustslices.py:231:17: undeclared name not builtin: Buffer

Error compiling Cython file:
------------------------------------------------------------
...
        """Create new buffer."""
        self.bufferDestroy()
        buffer = Buffer()
        self.panel = panel = wx.Panel(parent=self, id=-1)
        panel.Bind (wx.EVT_ERASE_BACKGROUND, lambda x: x)
        editor = Editor(parent=panel)
                 ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\py\crustslices.py:234:17: undeclared name not builtin: Editor







[1/1] Cythonizing c:\python3.11.14\Lib\site-packages\wx\lib\pydocview.py

Error compiling Cython file:
------------------------------------------------------------
...
        Processes an event, searching event tables and calling zero or more
        suitable event handler function(s).  Note that the ProcessEvent
        method is called from the wxPython docview framework directly since
        wxPython does not have a virtual ProcessEvent function.
        """
        if not self._childView or not self._childView.ProcessEvent(event):
               ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\lib\pydocview.py:691:15: undeclared name not builtin: self

Error compiling Cython file:
------------------------------------------------------------
...
        else:
            self._docManager.RemoveFileFromHistory(n)
            msgTitle = wx.GetApp().GetAppName()
            if not msgTitle:
                msgTitle = _("File Error")
            wx.MessageBox("The file '%s' doesn't exist and couldn't be opened.\nIt has been removed from the most recently used files list" % FileNameFromPath(file),
                                                                                                                                              ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\lib\pydocview.py:1075:142: undeclared name not builtin: FileNameFromPath

Error compiling Cython file:
------------------------------------------------------------
...
        else:
            self._docManager.RemoveFileFromHistory(n)
            msgTitle = wx.GetApp().GetAppName()
            if not msgTitle:
                msgTitle = _("File Error")
            wx.MessageBox("The file '%s' doesn't exist and couldn't be opened.\nIt has been removed from the most recently used files list" % FileNameFromPath(file),
                                                                                                                                                               ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\lib\pydocview.py:1075:159: undeclared name not builtin: file

Error compiling Cython file:
------------------------------------------------------------
...
    def SetSupportedModes(self, _supportedModessupportedModes):
        """
        Sets the modes supported by the application.  Use docview.DOC_SDI and
        docview.DOC_MDI flags to set if SDI and/or MDI modes are supported.
        """
        self._supportedModes = supportedModes
                               ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\lib\pydocview.py:1446:31: undeclared name not builtin: supportedModes

Error compiling Cython file:
------------------------------------------------------------
...
                if icon:
                    if icon.GetHeight() != 16 or icon.GetWidth() != 16:
                        icon.SetHeight(16)
                        icon.SetWidth(16)
                        if wx.GetApp().GetDebug():
                            print("Warning: icon for '%s' isn't 16x16, not crossplatform" % template._docTypeName)
                                                                                            ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\lib\pydocview.py:1523:92: undeclared name not builtin: template

Error compiling Cython file:
------------------------------------------------------------
...
        else:
            self._docManager.RemoveFileFromHistory(n)
            msgTitle = wx.GetApp().GetAppName()
            if not msgTitle:
                msgTitle = _("File Error")
            wx.MessageBox("The file '%s' doesn't exist and couldn't be opened.\nIt has been removed from the most recently used files list" % docview.FileNameFromPath(file),
                                                                                                                                              ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\lib\pydocview.py:2390:142: undeclared name not builtin: docview







[1/1] Cythonizing c:\python3.11.14\Lib\site-packages\wx\lib\pubsub\utils\xmltopicdefnprovider.py

Error compiling Cython file:
------------------------------------------------------------
...
            with open(xml, mode="r") as fid:
                self._parse_tree(_get_elem(fid.read()))
        elif format == TOPIC_TREE_FROM_STRING:
            self._parse_tree(_get_elem(xml))
        else:
            raise UnrecognizedSourceFormatError()
                  ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\lib\pubsub\utils\xmltopicdefnprovider.py:105:18: undeclared name not builtin: UnrecognizedSourceFormatError

Error compiling Cython file:
------------------------------------------------------------
...
        else:
            desc = ' '.join(descNode.text.split())

        node_id = node.get('id')
        if node_id is None:
            raise XmlParserError("topic element must have an id attribute")
                  ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\lib\pubsub\utils\xmltopicdefnprovider.py:132:18: undeclared name not builtin: XmlParserError






[1/1] Cythonizing c:\python3.11.14\Lib\site-packages\wx\lib\ogl\basic.py

Error compiling Cython file:
------------------------------------------------------------
...
                    y = bottom + (nth + 1) * self._height / (no_arcs + 1.0)
                else:
                    y = self._ypos
                return DrawArcToEllipse(self._xpos, self._ypos, self._width, self._height, self._xpos - self._width - 500, y, self._xpos, y)
            else:
                return Shape.GetAttachmentPosition(self, attachment, x, y, nth, no_arcs, line)
                                                                     ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\lib\ogl\basic.py:3524:69: local variable 'x' referenced before assignment

Error compiling Cython file:
------------------------------------------------------------
...
                    y = bottom + (nth + 1) * self._height / (no_arcs + 1.0)
                else:
                    y = self._ypos
                return DrawArcToEllipse(self._xpos, self._ypos, self._width, self._height, self._xpos - self._width - 500, y, self._xpos, y)
            else:
                return Shape.GetAttachmentPosition(self, attachment, x, y, nth, no_arcs, line)
                                                                        ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\lib\ogl\basic.py:3524:72: local variable 'y' referenced before assignment





[1/1] Cythonizing c:\python3.11.14\Lib\site-packages\wx\lib\mixins\imagelist.py

Error compiling Cython file:
------------------------------------------------------------
...
    ### Local methods...
    def AddIcon(self, icon, mask = wx.NullBitmap):
        """Add an icon to the image list, or get the index if already there"""
        index = self.__magicImageListMapping.get (id (icon))
        if index is None:
            if isinstance( icon, wxIconPtr ):
                                 ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\lib\mixins\imagelist.py:57:33: undeclared name not builtin: wxIconPtr






[1/1] Cythonizing c:\python3.11.14\Lib\site-packages\wx\lib\masked\timectrl.py

Error compiling Cython file:
------------------------------------------------------------
...

            # Validate initial value and set if appropriate
            try:
                self.SetBounds(min, max)
                self.SetLimited(limited)
                self.SetValue(value)
                              ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\lib\masked\timectrl.py:623:30: undeclared name not builtin: value

Error compiling Cython file:
------------------------------------------------------------
...
            valid = wxdt.ParseTime(value)

            if not valid:
                # deal with bug/deficiency in wx.DateTime:
                try:
                    if wxdt.Format('%p') not in ('AM', 'PM') and checkTime in (5,8):
                                                                 ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\lib\masked\timectrl.py:776:65: undeclared name not builtin: checkTime

Error compiling Cython file:
------------------------------------------------------------
...
        else:
            # Convert string 1st to wxDateTime, then use components, since
            # mx' DateTime.Parser.TimeFromString() doesn't handle AM/PM:
            wxdt = self.GetWxDateTime(value)
            hour, minute, second = wxdt.GetHour(), wxdt.GetMinute(), wxdt.GetSecond()
            t = DateTime.DateTime(1970,1,1) + DateTimeDelta(0, hour, minute, second)
                                              ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\lib\masked\timectrl.py:836:46: undeclared name not builtin: DateTimeDelta





[1/1] Cythonizing c:\python3.11.14\Lib\site-packages\wx\lib\masked\maskededit.py
warning: c:\python3.11.14\Lib\site-packages\wx\lib\masked\maskededit.py:6663:0: Global name __test2 matched from within class scope in contradiction to Python 'class private name' rules. This may change in a future release.

Error compiling Cython file:
------------------------------------------------------------
...
                    newvalue, signpos, right_signpos = self._getSignedValue(value)
##                    dbg('old value: "%s"' % value)
##                    dbg('new value: "%s"' % newvalue)
                    try:
                        self._ChangeValue(newvalue)
                    except e:
                           ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\lib\masked\maskededit.py:2795:27: local variable 'e' referenced before assignment

Error compiling Cython file:
------------------------------------------------------------
...
                if( (not field._moveOnFieldFull
                     and (not self._signOk
                          or (self._signOk and field._index == 0 and pos > 0) ) )

                    or (field._stopFieldChangeIfInvalid
                        and not field.IsValid(self._GetValue()[start:end]) ) ):
                                                               ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\lib\masked\maskededit.py:4412:63: local variable 'start' referenced before assignment

Error compiling Cython file:
------------------------------------------------------------
...
                if( (not field._moveOnFieldFull
                     and (not self._signOk
                          or (self._signOk and field._index == 0 and pos > 0) ) )

                    or (field._stopFieldChangeIfInvalid
                        and not field.IsValid(self._GetValue()[start:end]) ) ):
                                                                     ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\lib\masked\maskededit.py:4412:69: local variable 'end' referenced before assignment

Error compiling Cython file:
------------------------------------------------------------
...
            else:
##                dbg(indent=0)
                return new_text, replace_to
        elif just_return_value:
##            dbg(indent=0)
            return self._GetValue(), sel_to
                                     ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\lib\masked\maskededit.py:5991:37: local variable 'sel_to' referenced before assignment
warning: c:\python3.11.14\Lib\site-packages\wx\lib\masked\maskededit.py:6663:0: Global name __test2 matched from within class scope in contradiction to Python 'class private name' rules. This may change in a future release.

Error compiling Cython file:
------------------------------------------------------------
...
            try:
                groupchar = self._fields[0]._groupChar
                value = float(text.replace(groupchar,'').replace(self._decimalChar, '.').replace('(', '-').replace(')','').replace(' ', ''))
##                dbg('value:', value)
            except:
                value = None
                        ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\lib\masked\maskededit.py:4898:24: Cannot assign None to double

Error compiling Cython file:
------------------------------------------------------------
...
                self.sizer.Add( wx.StaticText( self.panel, -1, control[1]),row=rowcount, col=1,border=5, flag=wx.ALL)
                self.sizer.Add( wx.StaticText( self.panel, -1, control[3]),row=rowcount, col=2,border=5, flag=wx.ALL)
                self.sizer.Add( wx.StaticText( self.panel, -1, control[4][:20]),row=rowcount, col=3,border=5, flag=wx.ALL)

                if control in controls[:]:#-2]:
                    newControl  = MaskedTextCtrl( self.panel, -1, "",
                                  ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\lib\masked\maskededit.py:6590:34: undeclared name not builtin: MaskedTextCtrl

Error compiling Cython file:
------------------------------------------------------------
...
                                                    choices      = control[6],
                                                    defaultValue = control[7],
                                                    demo         = True)
                    if control[6]: newControl.SetCtrlParameters(choiceRequired = True)
                else:
                    newControl = MaskedComboBox(  self.panel, -1, "",
                                 ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\lib\masked\maskededit.py:6602:33: undeclared name not builtin: MaskedComboBox
warning: c:\python3.11.14\Lib\site-packages\wx\lib\masked\maskededit.py:6663:0: Global name __test2 matched from within class scope in contradiction to Python 'class private name' rules. This may change in a future release.
warning: c:\python3.11.14\Lib\site-packages\wx\lib\masked\maskededit.py:6663:0: Global name __test2 matched from within class scope in contradiction to Python 'class private name' rules. This may change in a future release.

Error compiling Cython file:
------------------------------------------------------------
...
                    self.sizer.Add( MaskedTextCtrl( self.panel, -1, "",
                                                      autoformat  = control[1],
                                                      demo        = True),
                                row=rowcount,col=2,flag=wx.ALL,border=5)
                else:
                    self.sizer.Add( IpAddrCtrl( self.panel, -1, "", demo=True ),
                                    ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\lib\masked\maskededit.py:6727:36: undeclared name not builtin: IpAddrCtrl






[1/1] Cythonizing c:\python3.11.14\Lib\site-packages\wx\lib\langlistctrl.py

Error compiling Cython file:
------------------------------------------------------------
...
    f=wx.Frame(None, -1)
    f.p=wx.Panel(f, -1)
    s=wx.BoxSizer(wx.VERTICAL)
    f.p.SetSizer(s)
    try:
        f.lc=LanguageChoice(f.p, pos = (220, 10), size = (200, 25))
             ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\lib\langlistctrl.py:466:13: undeclared name not builtin: LanguageChoice






[1/1] Cythonizing c:\python3.11.14\Lib\site-packages\wx\lib\intctrl.py

Error compiling Cython file:
------------------------------------------------------------
...
        key = event.GetKeyCode()
        ctrl = event.GetEventObject()

        if 'wxMac' in wx.PlatformInfo:
            if event.CmdDown() and key == ord('c'):
                key = WXK_CTRL_C
                      ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\lib\intctrl.py:137:22: undeclared name not builtin: WXK_CTRL_C

Error compiling Cython file:
------------------------------------------------------------
...
        do = wx.TextDataObject()
        do.SetText(textval[sel_start:sel_to])
        wx.TheClipboard.Open()
        wx.TheClipboard.SetData(do)
        wx.TheClipboard.Close()
        if select_len == len(wxTextCtrl.GetValue(self)):
                             ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\lib\intctrl.py:870:29: undeclared name not builtin: wxTextCtrl






[1/1] Cythonizing c:\python3.11.14\Lib\site-packages\wx\lib\inspection.py

Error compiling Cython file:
------------------------------------------------------------
...
                x+= sizer.HGap
                dc.DrawLine(x, rect.y, x, rect.y+rect.height)

        # Anything else is probably a custom sizer, just highlight the items
        else:
            del dc, odc
                    ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\lib\inspection.py:991:20: local variable 'odc' referenced before assignment






[1/1] Cythonizing c:\python3.11.14\Lib\site-packages\wx\lib\graphics.py

Error compiling Cython file:
------------------------------------------------------------
...
        two colours to be used as the starting and ending gradient colours.
        """
        if len(args) == 1:
            stops = args[0]
        elif len(args) == 2:
            c1 = _makeColour(c1)
                             ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\lib\graphics.py:1285:29: local variable 'c1' referenced before assignment

Error compiling Cython file:
------------------------------------------------------------
...
        """
        if len(args) == 1:
            stops = args[0]
        elif len(args) == 2:
            c1 = _makeColour(c1)
            c2 = _makeColour(c2)
                             ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\lib\graphics.py:1286:29: local variable 'c2' referenced before assignment

Error compiling Cython file:
------------------------------------------------------------
...
        colours to be used as the starting and ending gradient colours.
        """
        if len(args) ==1:
            stops = args[0]
        elif len(args) == 2:
            oColour = _makeColour(oColour)
                                  ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\lib\graphics.py:1310:34: local variable 'oColour' referenced before assignment

Error compiling Cython file:
------------------------------------------------------------
...
        """
        if len(args) ==1:
            stops = args[0]
        elif len(args) == 2:
            oColour = _makeColour(oColour)
            cColour = _makeColour(cColour)
                                  ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\lib\graphics.py:1311:34: local variable 'cColour' referenced before assignment








[1/1] Cythonizing c:\python3.11.14\Lib\site-packages\wx\lib\evtmgr.py

Error compiling Cython file:
------------------------------------------------------------
...
    def GetStats(self):
        """
        Return a dictionary with data about my state.
        """
        stats = {}
        stats['Adapters: Message'] = reduce(lambda x,y: x+y, [0] + map(len, self.messageAdapterDict.values()))
                                     ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\lib\evtmgr.py:189:37: undeclared name not builtin: reduce







[1/1] Cythonizing c:\python3.11.14\Lib\site-packages\wx\lib\docview.py

Error compiling Cython file:
------------------------------------------------------------
...
                    i += 1
                    backupFilename = "%s.bak%s" % (filename, i)
                shutil.copy(filename, backupFilename)
                copied = True

            fileObject = file(filename, 'w')
                         ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\lib\docview.py:475:25: undeclared name not builtin: file

Error compiling Cython file:
------------------------------------------------------------
...

    def SetIcon(self, flags):
        """
        Sets the icon.
        """
        self._icon = icon
                     ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\lib\docview.py:1185:21: undeclared name not builtin: icon

Error compiling Cython file:
------------------------------------------------------------
...
            view = temp.CreateView(doc, flags)
            if view:
                view.SetViewName(temp.GetViewName())
            return view

        temp = SelectViewType(templates)
               ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\lib\docview.py:1944:15: undeclared name not builtin: SelectViewType

Error compiling Cython file:
------------------------------------------------------------
...
        """
        Returns a suitable title for a document frame. This is implemented by
        appending the document name to the application name.
        """
        appName = wx.GetApp().GetAppName()
        if not doc:
               ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\lib\docview.py:2002:15: undeclared name not builtin: doc

Error compiling Cython file:
------------------------------------------------------------
...
        elif len(templates) == 1:
            return templates[0]

        if sort:
            def tempcmp(a, b):
                return cmp(a.GetDescription(), b.GetDescription())
                       ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\lib\docview.py:2222:23: undeclared name not builtin: cmp

Error compiling Cython file:
------------------------------------------------------------
...
    def ProcessEvent(event):
        """
        Processes an event, searching event tables and calling zero or more
        suitable event handler function(s).
        """
        if self._activeEvent == event:
           ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\lib\docview.py:2760:11: undeclared name not builtin: self







[1/1] Cythonizing c:\python3.11.14\Lib\site-packages\wx\lib\CDate.py

Error compiling Cython file:
------------------------------------------------------------
...
    daywk = day_name[daywk]
    return(daywk)


def FormatDay(value):
    date = FromFormat(value)
           ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\lib\CDate.py:108:11: undeclared name not builtin: FromFormat

Error compiling Cython file:
------------------------------------------------------------
...
    return(daywk)


def FormatDay(value):
    date = FromFormat(value)
    daywk = DateCalc.dayOfWeek(date)
            ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\lib\CDate.py:109:12: undeclared name not builtin: DateCalc








[1/1] Cythonizing c:\python3.11.14\Lib\site-packages\wx\lib\agw\ultimatelistctrl.py

Error compiling Cython file:
------------------------------------------------------------
...
        data2 = item2._data

        if self.__func:
            return self.__func(data1, data2)
        else:
            return cmp(data1, data2)
                   ^
------------------------------------------------------------
c:\python3.11.14\Lib\site-packages\wx\lib\agw\ultimatelistctrl.py:10411:19: undeclared name not builtin: cmp
'''