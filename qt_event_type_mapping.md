# PySide6 QEvent.Type -> Event Class Mapping

Generated against the installed PySide6 build (verified via `__mro__`, not just the doc text).
Chain is most-derived class first, `QEvent` last -- every listed class is a valid `isinstance()` match
for that event, not just the first one.

| QEvent.Type | Class hierarchy (most-derived -> QEvent) | Notes |
|---|---|---|
| `None_` | QEvent |  |
| `ActionAdded` | QActionEvent → QEvent |  |
| `ActionChanged` | QActionEvent → QEvent |  |
| `ActionRemoved` | QActionEvent → QEvent |  |
| `ActivationChange` | QEvent |  |
| `ApplicationActivate` | QEvent |  |
| `ApplicationActivated` | QEvent |  |
| `ApplicationDeactivate` | QEvent |  |
| `ApplicationFontChange` | QEvent |  |
| `ApplicationLayoutDirectionChange` | QEvent |  |
| `ApplicationPaletteChange` | QEvent |  |
| `ApplicationStateChange` | QEvent |  |
| `ApplicationWindowIconChange` | QEvent |  |
| `ChildAdded` | QChildEvent → QEvent |  |
| `ChildPolished` | QChildEvent → QEvent |  |
| `ChildRemoved` | QChildEvent → QEvent |  |
| `ChildWindowAdded` | QEvent |  |
| `ChildWindowRemoved` | QEvent |  |
| `Clipboard` | QEvent |  |
| `Close` | QCloseEvent → QEvent |  |
| `CloseSoftwareInputPanel` | QEvent |  |
| `ContentsRectChange` | QEvent |  |
| `ContextMenu` | QContextMenuEvent → QInputEvent → QEvent |  |
| `CursorChange` | QEvent |  |
| `DeferredDelete` | QEvent | QDeferredDeleteEvent not exposed in PySide6 |
| `DevicePixelRatioChange` | QEvent |  |
| `DragEnter` | QDragEnterEvent → QDragMoveEvent → QDropEvent → QEvent |  |
| `DragLeave` | QDragLeaveEvent → QEvent |  |
| `DragMove` | QDragMoveEvent → QDropEvent → QEvent |  |
| `Drop` | QDropEvent → QEvent |  |
| `DynamicPropertyChange` | QEvent |  |
| `EnabledChange` | QEvent |  |
| `Enter` | QEnterEvent → QSinglePointEvent → QPointerEvent → QInputEvent → QEvent |  |
| `EnterEditFocus` | QEvent | enum member not present in this PySide6 build |
| `EnterWhatsThisMode` | QEvent |  |
| `Expose` | QEvent |  |
| `FileOpen` | QFileOpenEvent → QEvent |  |
| `FocusIn` | QFocusEvent → QEvent |  |
| `FocusOut` | QFocusEvent → QEvent |  |
| `FocusAboutToChange` | QFocusEvent → QEvent |  |
| `FontChange` | QEvent |  |
| `Gesture` | QGestureEvent → QEvent |  |
| `GestureOverride` | QGestureEvent → QEvent |  |
| `GrabKeyboard` | QEvent |  |
| `GrabMouse` | QEvent |  |
| `GraphicsSceneContextMenu` | QGraphicsSceneContextMenuEvent → QGraphicsSceneEvent → QEvent |  |
| `GraphicsSceneDragEnter` | QGraphicsSceneDragDropEvent → QGraphicsSceneEvent → QEvent |  |
| `GraphicsSceneDragLeave` | QGraphicsSceneDragDropEvent → QGraphicsSceneEvent → QEvent |  |
| `GraphicsSceneDragMove` | QGraphicsSceneDragDropEvent → QGraphicsSceneEvent → QEvent |  |
| `GraphicsSceneDrop` | QGraphicsSceneDragDropEvent → QGraphicsSceneEvent → QEvent |  |
| `GraphicsSceneHelp` | QHelpEvent → QEvent |  |
| `GraphicsSceneHoverEnter` | QGraphicsSceneHoverEvent → QGraphicsSceneEvent → QEvent |  |
| `GraphicsSceneHoverLeave` | QGraphicsSceneHoverEvent → QGraphicsSceneEvent → QEvent |  |
| `GraphicsSceneHoverMove` | QGraphicsSceneHoverEvent → QGraphicsSceneEvent → QEvent |  |
| `GraphicsSceneMouseDoubleClick` | QGraphicsSceneMouseEvent → QGraphicsSceneEvent → QEvent |  |
| `GraphicsSceneMouseMove` | QGraphicsSceneMouseEvent → QGraphicsSceneEvent → QEvent |  |
| `GraphicsSceneMousePress` | QGraphicsSceneMouseEvent → QGraphicsSceneEvent → QEvent |  |
| `GraphicsSceneMouseRelease` | QGraphicsSceneMouseEvent → QGraphicsSceneEvent → QEvent |  |
| `GraphicsSceneMove` | QGraphicsSceneMoveEvent → QGraphicsSceneEvent → QEvent |  |
| `GraphicsSceneResize` | QGraphicsSceneResizeEvent → QGraphicsSceneEvent → QEvent |  |
| `GraphicsSceneWheel` | QGraphicsSceneWheelEvent → QGraphicsSceneEvent → QEvent |  |
| `GraphicsSceneLeave` | QEvent | doc cites QGraphicsSceneWheelEvent -- looks like a docs error |
| `Hide` | QHideEvent → QEvent |  |
| `HideToParent` | QEvent |  |
| `HoverEnter` | QHoverEvent → QSinglePointEvent → QPointerEvent → QInputEvent → QEvent |  |
| `HoverLeave` | QHoverEvent → QSinglePointEvent → QPointerEvent → QInputEvent → QEvent |  |
| `HoverMove` | QHoverEvent → QSinglePointEvent → QPointerEvent → QInputEvent → QEvent |  |
| `IconDrag` | QIconDragEvent → QEvent |  |
| `IconTextChange` | QEvent |  |
| `InputMethod` | QInputMethodEvent → QEvent |  |
| `InputMethodQuery` | QInputMethodQueryEvent → QEvent |  |
| `KeyboardLayoutChange` | QEvent |  |
| `KeyPress` | QKeyEvent → QInputEvent → QEvent |  |
| `KeyRelease` | QKeyEvent → QInputEvent → QEvent |  |
| `LanguageChange` | QEvent |  |
| `LayoutDirectionChange` | QEvent |  |
| `LayoutRequest` | QEvent |  |
| `Leave` | QEvent |  |
| `LeaveEditFocus` | QEvent | enum member not present in this PySide6 build |
| `LeaveWhatsThisMode` | QEvent |  |
| `LocaleChange` | QEvent |  |
| `NonClientAreaMouseButtonDblClick` | QMouseEvent → QSinglePointEvent → QPointerEvent → QInputEvent → QEvent |  |
| `NonClientAreaMouseButtonPress` | QMouseEvent → QSinglePointEvent → QPointerEvent → QInputEvent → QEvent |  |
| `NonClientAreaMouseButtonRelease` | QMouseEvent → QSinglePointEvent → QPointerEvent → QInputEvent → QEvent |  |
| `NonClientAreaMouseMove` | QMouseEvent → QSinglePointEvent → QPointerEvent → QInputEvent → QEvent |  |
| `MacSizeChange` | QEvent |  |
| `MetaCall` | QEvent |  |
| `ModifiedChange` | QEvent |  |
| `MouseButtonDblClick` | QMouseEvent → QSinglePointEvent → QPointerEvent → QInputEvent → QEvent |  |
| `MouseButtonPress` | QMouseEvent → QSinglePointEvent → QPointerEvent → QInputEvent → QEvent |  |
| `MouseButtonRelease` | QMouseEvent → QSinglePointEvent → QPointerEvent → QInputEvent → QEvent |  |
| `MouseMove` | QMouseEvent → QSinglePointEvent → QPointerEvent → QInputEvent → QEvent |  |
| `MouseTrackingChange` | QEvent |  |
| `Move` | QMoveEvent → QEvent |  |
| `NativeGesture` | QNativeGestureEvent → QSinglePointEvent → QPointerEvent → QInputEvent → QEvent |  |
| `OrientationChange` | QEvent | QScreenOrientationChangeEvent not exposed in PySide6 |
| `Paint` | QPaintEvent → QEvent |  |
| `PaletteChange` | QEvent |  |
| `ParentAboutToChange` | QEvent |  |
| `ParentChange` | QEvent |  |
| `ParentWindowAboutToChange` | QEvent |  |
| `ParentWindowChange` | QEvent |  |
| `PlatformPanel` | QEvent |  |
| `PlatformSurface` | QPlatformSurfaceEvent → QEvent |  |
| `Polish` | QEvent |  |
| `PolishRequest` | QEvent |  |
| `QueryWhatsThis` | QHelpEvent → QEvent |  |
| `Quit` | QEvent |  |
| `ReadOnlyChange` | QEvent |  |
| `RequestSoftwareInputPanel` | QEvent |  |
| `Resize` | QResizeEvent → QEvent |  |
| `ScrollPrepare` | QScrollPrepareEvent → QEvent |  |
| `Scroll` | QScrollEvent → QEvent |  |
| `Shortcut` | QShortcutEvent → QEvent |  |
| `ShortcutOverride` | QKeyEvent → QInputEvent → QEvent |  |
| `Show` | QShowEvent → QEvent |  |
| `ShowToParent` | QEvent |  |
| `SockAct` | QEvent |  |
| `StateMachineSignal` | QEvent |  |
| `StateMachineWrapped` | QEvent |  |
| `StatusTip` | QStatusTipEvent → QEvent |  |
| `StyleChange` | QEvent |  |
| `TabletMove` | QTabletEvent → QSinglePointEvent → QPointerEvent → QInputEvent → QEvent |  |
| `TabletPress` | QTabletEvent → QSinglePointEvent → QPointerEvent → QInputEvent → QEvent |  |
| `TabletRelease` | QTabletEvent → QSinglePointEvent → QPointerEvent → QInputEvent → QEvent |  |
| `TabletEnterProximity` | QTabletEvent → QSinglePointEvent → QPointerEvent → QInputEvent → QEvent |  |
| `TabletLeaveProximity` | QTabletEvent → QSinglePointEvent → QPointerEvent → QInputEvent → QEvent |  |
| `TabletTrackingChange` | QEvent |  |
| `ThreadChange` | QEvent |  |
| `Timer` | QTimerEvent → QEvent |  |
| `ToolBarChange` | QEvent |  |
| `ToolTip` | QHelpEvent → QEvent |  |
| `ToolTipChange` | QEvent |  |
| `TouchBegin` | QTouchEvent → QPointerEvent → QInputEvent → QEvent |  |
| `TouchCancel` | QTouchEvent → QPointerEvent → QInputEvent → QEvent |  |
| `TouchEnd` | QTouchEvent → QPointerEvent → QInputEvent → QEvent |  |
| `TouchUpdate` | QTouchEvent → QPointerEvent → QInputEvent → QEvent |  |
| `UngrabKeyboard` | QEvent |  |
| `UngrabMouse` | QEvent |  |
| `UpdateLater` | QEvent |  |
| `UpdateRequest` | QEvent |  |
| `WhatsThis` | QHelpEvent → QEvent |  |
| `WhatsThisClicked` | QEvent |  |
| `Wheel` | QWheelEvent → QSinglePointEvent → QPointerEvent → QInputEvent → QEvent |  |
| `WinEventAct` | QEvent |  |
| `WindowActivate` | QEvent |  |
| `WindowBlocked` | QEvent |  |
| `WindowDeactivate` | QEvent |  |
| `WindowIconChange` | QEvent |  |
| `WindowStateChange` | QWindowStateChangeEvent → QEvent |  |
| `WindowTitleChange` | QEvent |  |
| `WindowUnblocked` | QEvent |  |
| `WinIdChange` | QEvent |  |
| `ZOrderChange` | QEvent |  |
| `SafeAreaMarginsChange` | QEvent |  |
