"""Detect GPU vendor from OpenGL strings"""

from OpenGL import GL

GPU_UNKNOWN = 0x00
GPU_NVIDIA = 0x01
GPU_AMD = 0x02
GPU_APPLE = 0x03
GPU_INTEL = 0x04


def get() -> str:
    """
    Get GPU vendor from OpenGL

    Returns:
        GPU_UNKNOWN, GPU_NVIDIA, GPU_AMD, GPU_APPLE, GPU_INTEL
    """
    try:
        vendor = GL.glGetString(GL.GL_VENDOR)
        renderer = GL.glGetString(GL.GL_RENDERER)

        # Decode bytes to string
        if isinstance(vendor, bytes):
            vendor = vendor.decode('utf-8', errors='ignore')

        if isinstance(renderer, bytes):
            renderer = renderer.decode('utf-8', errors='ignore')

        # Convert to lowercase for comparison
        vendor = vendor.lower()
        renderer = renderer.lower()

        # Check vendor string
        if 'nvidia' in vendor:
            return GPU_NVIDIA

        if 'ati' in vendor or 'amd' in vendor:
            return GPU_AMD

        if 'intel' in vendor:
            return GPU_INTEL

        if 'apple' in vendor:
            return GPU_APPLE

        # Fallback: check renderer string
        if 'nvidia' in renderer or 'geforce' in renderer or 'quadro' in renderer:
            return GPU_NVIDIA

        if 'radeon' in renderer or 'amd' in renderer:
            return GPU_AMD

        if 'intel' in renderer or 'iris' in renderer:
            return GPU_INTEL

        if 'apple' in renderer:
            return GPU_APPLE

        return GPU_UNKNOWN

    except:  # NOQA
        return GPU_UNKNOWN
