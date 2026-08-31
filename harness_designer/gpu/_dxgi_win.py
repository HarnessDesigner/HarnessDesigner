# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Windows-only: hand-bound DXGI COM interfaces (via ``comtypes``) backing
:func:`.os_vram_usage.get_current_usage_bytes`.

No typelib exists for DXGI to generate a wrapper from, so every interface
here is declared by hand from Microsoft's own public headers
(``dxgi.h``/``dxgi1_2.h``/``dxgi1_3.h``/``dxgi1_4.h``). The one thing that
has to be exactly right is vtable order: COM calls resolve to a function
pointer by slot index, so every ancestor interface's methods must be
declared in their real order even though only the ``IDXGIAdapter3``-added
ones (``QueryVideoMemoryInfo`` in particular) are ever actually called --
skip or misorder an inherited method and every method declared after it
calls through the wrong slot.

Inheritance chain implemented here, base to derived:
``IUnknown`` (built into comtypes) -> ``IDXGIObject`` -> ``IDXGIAdapter``
-> ``IDXGIAdapter1`` -> ``IDXGIAdapter2`` -> ``IDXGIAdapter3``, and
separately ``IDXGIObject`` -> ``IDXGIFactory`` -> ``IDXGIFactory1``.
"""

import ctypes
from ctypes import wintypes

import comtypes
from comtypes import GUID, IUnknown, COMMETHOD, HRESULT

from .. import check_types as _check_types


class LUID(ctypes.Structure):
    _fields_ = [
        ('LowPart', wintypes.DWORD),
        ('HighPart', wintypes.LONG),
    ]


class DXGI_ADAPTER_DESC(ctypes.Structure):
    _fields_ = [
        ('Description', ctypes.c_wchar * 128),
        ('VendorId', ctypes.c_uint32),
        ('DeviceId', ctypes.c_uint32),
        ('SubSysId', ctypes.c_uint32),
        ('Revision', ctypes.c_uint32),
        ('DedicatedVideoMemory', ctypes.c_size_t),
        ('DedicatedSystemMemory', ctypes.c_size_t),
        ('SharedSystemMemory', ctypes.c_size_t),
        ('AdapterLuid', LUID),
    ]


class DXGI_ADAPTER_DESC1(ctypes.Structure):
    _fields_ = [
        ('Description', ctypes.c_wchar * 128),
        ('VendorId', ctypes.c_uint32),
        ('DeviceId', ctypes.c_uint32),
        ('SubSysId', ctypes.c_uint32),
        ('Revision', ctypes.c_uint32),
        ('DedicatedVideoMemory', ctypes.c_size_t),
        ('DedicatedSystemMemory', ctypes.c_size_t),
        ('SharedSystemMemory', ctypes.c_size_t),
        ('AdapterLuid', LUID),
        ('Flags', ctypes.c_uint32),
    ]


class DXGI_ADAPTER_DESC2(ctypes.Structure):
    _fields_ = [
        ('Description', ctypes.c_wchar * 128),
        ('VendorId', ctypes.c_uint32),
        ('DeviceId', ctypes.c_uint32),
        ('SubSysId', ctypes.c_uint32),
        ('Revision', ctypes.c_uint32),
        ('DedicatedVideoMemory', ctypes.c_size_t),
        ('DedicatedSystemMemory', ctypes.c_size_t),
        ('SharedSystemMemory', ctypes.c_size_t),
        ('AdapterLuid', LUID),
        ('Flags', ctypes.c_uint32),
        ('GraphicsPreemptionGranularity', ctypes.c_uint32),
        ('ComputePreemptionGranularity', ctypes.c_uint32),
    ]


class DXGI_QUERY_VIDEO_MEMORY_INFO(ctypes.Structure):
    _fields_ = [
        ('Budget', ctypes.c_uint64),
        ('CurrentUsage', ctypes.c_uint64),
        ('AvailableForReservation', ctypes.c_uint64),
        ('CurrentReservation', ctypes.c_uint64),
    ]


DXGI_MEMORY_SEGMENT_GROUP_LOCAL = 0
DXGI_MEMORY_SEGMENT_GROUP_NON_LOCAL = 1


class IDXGIObject(IUnknown):
    _iid_ = GUID('{AEC22FB8-76F3-4639-9BE0-28EB43A67A2E}')
    _methods_ = [
        COMMETHOD([], HRESULT, 'SetPrivateData',
                  (['in'], ctypes.POINTER(GUID), 'Name'),
                  (['in'], ctypes.c_uint32, 'DataSize'),
                  (['in'], ctypes.c_void_p, 'pData')),
        COMMETHOD([], HRESULT, 'SetPrivateDataInterface',
                  (['in'], ctypes.POINTER(GUID), 'Name'),
                  (['in'], ctypes.POINTER(IUnknown), 'pUnknown')),
        COMMETHOD([], HRESULT, 'GetPrivateData',
                  (['in'], ctypes.POINTER(GUID), 'Name'),
                  (['in', 'out'], ctypes.POINTER(ctypes.c_uint32), 'pDataSize'),
                  (['out'], ctypes.c_void_p, 'pData')),
        COMMETHOD([], HRESULT, 'GetParent',
                  (['in'], ctypes.POINTER(GUID), 'riid'),
                  (['out'], ctypes.POINTER(ctypes.c_void_p), 'ppParent')),
    ]


class IDXGIAdapter(IDXGIObject):
    _iid_ = GUID('{2411E7E1-12AC-4CCF-BD14-9798E8534DC0}')
    _methods_ = [
        COMMETHOD([], HRESULT, 'EnumOutputs',
                  (['in'], ctypes.c_uint32, 'Output'),
                  (['out'], ctypes.POINTER(ctypes.c_void_p), 'ppOutput')),
        COMMETHOD([], HRESULT, 'GetDesc',
                  (['out'], ctypes.POINTER(DXGI_ADAPTER_DESC), 'pDesc')),
        COMMETHOD([], HRESULT, 'CheckInterfaceSupport',
                  (['in'], ctypes.POINTER(GUID), 'InterfaceName'),
                  (['out'], ctypes.POINTER(ctypes.c_int64), 'pUMDVersion')),
    ]


class IDXGIAdapter1(IDXGIAdapter):
    _iid_ = GUID('{29038F61-3839-4626-91FD-086879011A05}')
    _methods_ = [
        COMMETHOD([], HRESULT, 'GetDesc1',
                  (['out'], ctypes.POINTER(DXGI_ADAPTER_DESC1), 'pDesc')),
    ]


class IDXGIAdapter2(IDXGIAdapter1):
    _iid_ = GUID('{0AA1AE0A-FA0E-4B84-8644-E05FF8E5ACB5}')
    _methods_ = [
        COMMETHOD([], HRESULT, 'GetDesc2',
                  (['out'], ctypes.POINTER(DXGI_ADAPTER_DESC2), 'pDesc')),
    ]


class IDXGIAdapter3(IDXGIAdapter2):
    _iid_ = GUID('{645967A4-1392-4310-A798-8053CE3E93FD}')
    _methods_ = [
        COMMETHOD([], HRESULT, 'RegisterHardwareContentProtectionTeardownStatusEvent',
                  (['in'], wintypes.HANDLE, 'hEvent'),
                  (['out'], ctypes.POINTER(ctypes.c_uint32), 'pdwCookie')),
        COMMETHOD([], None, 'UnregisterHardwareContentProtectionTeardownStatus',
                  (['in'], ctypes.c_uint32, 'dwCookie')),
        COMMETHOD([], HRESULT, 'QueryVideoMemoryInfo',
                  (['in'], ctypes.c_uint32, 'NodeIndex'),
                  (['in'], ctypes.c_int, 'MemorySegmentGroup'),
                  (['out'], ctypes.POINTER(DXGI_QUERY_VIDEO_MEMORY_INFO), 'pVideoMemoryInfo')),
        COMMETHOD([], HRESULT, 'SetVideoMemoryReservation',
                  (['in'], ctypes.c_uint32, 'NodeIndex'),
                  (['in'], ctypes.c_int, 'MemorySegmentGroup'),
                  (['in'], ctypes.c_uint64, 'Reservation')),
        COMMETHOD([], HRESULT, 'RegisterVideoMemoryBudgetChangeNotificationEvent',
                  (['in'], wintypes.HANDLE, 'hEvent'),
                  (['out'], ctypes.POINTER(ctypes.c_uint32), 'pdwCookie')),
        COMMETHOD([], None, 'UnregisterVideoMemoryBudgetChangeNotification',
                  (['in'], ctypes.c_uint32, 'dwCookie')),
    ]


class IDXGIFactory(IDXGIObject):
    _iid_ = GUID('{7B7166EC-21C7-44AE-B21A-C9AE321AE369}')
    _methods_ = [
        COMMETHOD([], HRESULT, 'EnumAdapters',
                  (['in'], ctypes.c_uint32, 'Adapter'),
                  (['out'], ctypes.POINTER(ctypes.POINTER(IDXGIAdapter)), 'ppAdapter')),
        COMMETHOD([], HRESULT, 'MakeWindowAssociation',
                  (['in'], wintypes.HWND, 'WindowHandle'),
                  (['in'], ctypes.c_uint32, 'Flags')),
        COMMETHOD([], HRESULT, 'GetWindowAssociation',
                  (['out'], ctypes.POINTER(wintypes.HWND), 'pWindowHandle')),
        COMMETHOD([], HRESULT, 'CreateSwapChain',
                  (['in'], ctypes.POINTER(IUnknown), 'pDevice'),
                  (['in'], ctypes.c_void_p, 'pDesc'),
                  (['out'], ctypes.POINTER(ctypes.c_void_p), 'ppSwapChain')),
        COMMETHOD([], HRESULT, 'CreateSoftwareAdapter',
                  (['in'], wintypes.HMODULE, 'Module'),
                  (['out'], ctypes.POINTER(ctypes.POINTER(IDXGIAdapter)), 'ppAdapter')),
    ]


class IDXGIFactory1(IDXGIFactory):
    _iid_ = GUID('{770AAE78-F26F-4DBA-A829-253C83D1B387}')
    _methods_ = [
        COMMETHOD([], HRESULT, 'EnumAdapters1',
                  (['in'], ctypes.c_uint32, 'Adapter'),
                  (['out'], ctypes.POINTER(ctypes.POINTER(IDXGIAdapter1)), 'ppAdapter')),
        COMMETHOD([], ctypes.c_int, 'IsCurrent'),
    ]


_dxgi_dll = ctypes.windll.dxgi
_dxgi_dll.CreateDXGIFactory1.restype = ctypes.HRESULT
_dxgi_dll.CreateDXGIFactory1.argtypes = [ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p)]


@_check_types.do
def query_current_usage(adapter_index: int = 0):
    """Current (dedicated/local) VRAM usage, in bytes, attributed to *this
    process* on one adapter -- confirmed live: reads 0 with no GL/D3D
    context yet created in the calling process, and jumps by (very close
    to) the exact size of a VBO immediately after allocating one. Not an
    adapter-wide total across every process -- same scope as Task
    Manager's per-process GPU memory column, and conveniently the same
    scope as Linux's ``drm-total-memory`` (see :mod:`.os_vram_usage`).

    :param adapter_index: DXGI enumeration order (0 is typically, but not
        guaranteed to be, the primary adapter).
    :returns: Bytes currently in use by this process.
    :rtype: int
    :raises OSError: If any DXGI call fails (factory creation, enumeration,
        the ``IDXGIAdapter3`` interface not being supported, or the query
        itself) -- callers (:mod:`.os_vram_usage`) treat any exception here
        as "nothing available", not a hard failure.
    """
    factory_ptr = ctypes.c_void_p()
    hr = _dxgi_dll.CreateDXGIFactory1(ctypes.byref(IDXGIFactory1._iid_), ctypes.byref(factory_ptr))
    if hr < 0:
        raise OSError(f'CreateDXGIFactory1 failed: 0x{hr & 0xFFFFFFFF:08X}')

    factory = ctypes.cast(factory_ptr, ctypes.POINTER(IDXGIFactory1))

    adapter1 = factory.EnumAdapters1(adapter_index)
    adapter3 = adapter1.QueryInterface(IDXGIAdapter3)

    info = adapter3.QueryVideoMemoryInfo(0, DXGI_MEMORY_SEGMENT_GROUP_LOCAL)

    return int(info.CurrentUsage)
