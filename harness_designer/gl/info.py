from OpenGL import GL
import wx
import wx.glcanvas as glcanvas


def _safe_gl_get_string(param) -> str:
    """Safely retrieve a GL string parameter."""
    try:
        result = GL.glGetString(param)
        if result is None:
            return "N/A"
        return result.decode('utf-8') if isinstance(result, bytes) else str(
            result
            )
    except Exception as e:  # NOQA
        return f"Error: {e}"


def _safe_gl_get_integer(param):
    """Safely retrieve a GL integer parameter."""
    try:
        return GL.glGetInteger(param)
    except Exception:  # NOQA
        return None


def _safe_gl_get_integerv(param):
    """Safely retrieve GL integer array parameters."""
    try:
        return GL.glGetIntegerv(param)
    except Exception:  # NOQA
        return None


_info = None


def get(parent=None):
    """
    Get or collect OpenGL information.
    
    When called WITH a parent frame:
        - Collects GL info using the parent frame as the GLCanvas parent
        - Caches the info globally
        - Returns None (info is cached for later retrieval)
    
    When called WITHOUT a parent:
        - Returns previously cached GL info
        - Raises RuntimeError if info was never collected
    """
    global _info

    if parent is not None:
        # Parent provided - collect and cache GL info
        # Create GL canvas as child of provided parent frame
        try:
            canvas = glcanvas.GLCanvas(parent, wx.ID_ANY, size=(1, 1))
            context = glcanvas.GLContext(canvas)
            
            # Make the context current to query GL information
            canvas.SetCurrent(context)

            # Query OpenGL information
            _info = {
                'GFX Vendor': _safe_gl_get_string(GL.GL_VENDOR),
                'GFX Adapter': _safe_gl_get_string(GL.GL_RENDERER),
                'OpenGL Version': _safe_gl_get_string(GL.GL_VERSION),
                'GLSL Version': _safe_gl_get_string(GL.GL_SHADING_LANGUAGE_VERSION),
                'Extension Count': _safe_gl_get_integer(GL.GL_NUM_EXTENSIONS),
                'Element Limits': {
                    'Max Elements Indices': _safe_gl_get_integer(GL.GL_MAX_ELEMENTS_INDICES),
                    'Max Elements Vertices': _safe_gl_get_integer(GL.GL_MAX_ELEMENTS_VERTICES)
                },
                'Texture Capabilities': {
                    'Max Texture Size': _safe_gl_get_integer(GL.GL_MAX_TEXTURE_SIZE),
                    'Max 3D Texture Size': _safe_gl_get_integer(GL.GL_MAX_3D_TEXTURE_SIZE),
                    'Max Cube Map Texture Size': _safe_gl_get_integer(GL.GL_MAX_CUBE_MAP_TEXTURE_SIZE),
                    'Max Array Texture Layers': _safe_gl_get_integer(GL.GL_MAX_ARRAY_TEXTURE_LAYERS),
                    'Max Texture Image Units': _safe_gl_get_integer(GL.GL_MAX_TEXTURE_IMAGE_UNITS),
                    'Max Combined Texture Image Units': _safe_gl_get_integer(GL.GL_MAX_COMBINED_TEXTURE_IMAGE_UNITS),
                    'Max Texture Buffer Size': _safe_gl_get_integer(GL.GL_MAX_TEXTURE_BUFFER_SIZE)
                },
                'Vertex Processing': {
                    'Max Vertex Attributes': _safe_gl_get_integer(GL.GL_MAX_VERTEX_ATTRIBS),
                    'Max Vertex Uniform Components': _safe_gl_get_integer(GL.GL_MAX_VERTEX_UNIFORM_COMPONENTS),
                    'Max Vertex Texture Units': _safe_gl_get_integer(GL.GL_MAX_VERTEX_TEXTURE_IMAGE_UNITS),
                    'Max Vertex Output Components': _safe_gl_get_integer(GL.GL_MAX_VERTEX_OUTPUT_COMPONENTS)
                },
                'Fragment Processing': {
                    'Max Fragment Uniform Components': _safe_gl_get_integer(GL.GL_MAX_FRAGMENT_UNIFORM_COMPONENTS),
                    'Max Fragment Input Components': _safe_gl_get_integer(GL.GL_MAX_FRAGMENT_INPUT_COMPONENTS)
                },
                'Rendering Capabilities': {
                    'Max Draw Buffers': _safe_gl_get_integer(GL.GL_MAX_DRAW_BUFFERS),
                    'Max Color Attachments': _safe_gl_get_integer(GL.GL_MAX_COLOR_ATTACHMENTS),
                    'Max Samples (MSAA)': _safe_gl_get_integer(GL.GL_MAX_SAMPLES),
                    'Max Viewport Dimensions': _safe_gl_get_integerv(GL.GL_MAX_VIEWPORT_DIMS),
                    'Max Renderbuffer Size': _safe_gl_get_integer(GL.GL_MAX_RENDERBUFFER_SIZE)
                },
                'Buffer Capabilities': {
                    'Max Uniform Buffer Bindings': _safe_gl_get_integer(GL.GL_MAX_UNIFORM_BUFFER_BINDINGS),
                    'Max Uniform Block Size': _safe_gl_get_integer(GL.GL_MAX_UNIFORM_BLOCK_SIZE),
                    'Max Vertex Uniform Blocks': _safe_gl_get_integer(GL.GL_MAX_VERTEX_UNIFORM_BLOCKS),
                    'Max Fragment Uniform Blocks': _safe_gl_get_integer(GL.GL_MAX_FRAGMENT_UNIFORM_BLOCKS)
                },
                'Geometry Shader Capabilities': {
                    'Max Geometry Uniform Components': _safe_gl_get_integer(GL.GL_MAX_GEOMETRY_UNIFORM_COMPONENTS),
                    'Max Geometry Output Vertices': _safe_gl_get_integer(GL.GL_MAX_GEOMETRY_OUTPUT_VERTICES)
                },
                'Compute Shader Capabilities': {
                    'Max Compute Work Group Count': _safe_gl_get_integerv(GL.GL_MAX_COMPUTE_WORK_GROUP_COUNT),
                    'Max Compute Work Group Size': _safe_gl_get_integerv(GL.GL_MAX_COMPUTE_WORK_GROUP_SIZE)
                },
                'Additional': {
                    'Max Clip Distances': _safe_gl_get_integer(GL.GL_MAX_CLIP_DISTANCES)
                },
                'Atomic Counters': {
                    'Max Vertex Atomic Counters': _safe_gl_get_integer(GL.GL_MAX_VERTEX_ATOMIC_COUNTERS),
                    'Max Fragment Atomic Counters': _safe_gl_get_integer(GL.GL_MAX_FRAGMENT_ATOMIC_COUNTERS)
                },
            }
        finally:
            # Always destroy the canvas, even if collection fails
            canvas.Destroy()
        
        # Return None when collecting (caller doesn't need return value)
        return None
    else:
        # No parent - return cached data
        if _info is None:
            raise RuntimeError(
                "GL info has not been collected yet. "
                "Call get(parent=frame) first to collect the data."
            )
        return _info


# GL_MAX_COLOR_ATTACHMENTS 8
# GL_MAX_SAMPLES 64
# GL_MAX_LIGHTS 8
# GL_MAX_CLIP_PLANES 8
# GL_MAX_MODELVIEW_STACK_DEPTH 32
# GL_MAX_PROJECTION_STACK_DEPTH 2
# GL_MAX_TEXTURE_STACK_DEPTH 2
# GL_MAX_NAME_STACK_DEPTH 64
# GL_MAX_ATTRIB_STACK_DEPTH 16
# GL_MAX_CLIENT_ATTRIB_STACK_DEPTH 16
# GL_AUX_BUFFERS 0
# GL_RGBA_MODE 1
# GL_INDEX_MODE 0
# GL_DOUBLEBUFFER 1
# GL_STEREO 0
# GL_RENDER_MODE 7168
# GL_PERSPECTIVE_CORRECTION_HINT 4352
# GL_POINT_SMOOTH_HINT 4352
# GL_LINE_SMOOTH_HINT 4352
# GL_POLYGON_SMOOTH_HINT 4352
# GL_FOG_HINT 4352
# GL_TEXTURE_GEN_S 0
# GL_TEXTURE_GEN_T 0
# GL_TEXTURE_GEN_R 0
# GL_TEXTURE_GEN_Q 0
# GL_PIXEL_MAP_I_TO_I_SIZE 1
# GL_PIXEL_MAP_S_TO_S_SIZE 1
# GL_PIXEL_MAP_I_TO_R_SIZE 1
# GL_PIXEL_MAP_I_TO_G_SIZE 1
# GL_PIXEL_MAP_I_TO_B_SIZE 1
# GL_PIXEL_MAP_I_TO_A_SIZE 1
# GL_PIXEL_MAP_R_TO_R_SIZE 1
# GL_PIXEL_MAP_G_TO_G_SIZE 1
# GL_PIXEL_MAP_B_TO_B_SIZE 1
# GL_PIXEL_MAP_A_TO_A_SIZE 1
# GL_UNPACK_SWAP_BYTES 0
# GL_UNPACK_LSB_FIRST 0
# GL_UNPACK_ROW_LENGTH 0
# GL_UNPACK_SKIP_ROWS 0
# GL_UNPACK_SKIP_PIXELS 0
# GL_UNPACK_ALIGNMENT 4
# GL_PACK_SWAP_BYTES 0
# GL_PACK_LSB_FIRST 0
# GL_PACK_ROW_LENGTH 0
# GL_PACK_SKIP_ROWS 0
# GL_PACK_SKIP_PIXELS 0
# GL_PACK_ALIGNMENT 4
# GL_MAP_COLOR 0
# GL_MAP_STENCIL 0
# GL_INDEX_SHIFT 0
# GL_INDEX_OFFSET 0
# GL_RED_SCALE 1.0
# GL_RED_BIAS 0.0
# GL_ZOOM_X 1.0
# GL_ZOOM_Y 1.0
# GL_GREEN_SCALE 1.0
# GL_GREEN_BIAS 0.0
# GL_BLUE_SCALE 1.0
# GL_BLUE_BIAS 0.0
# GL_ALPHA_SCALE 1.0
# GL_ALPHA_BIAS 0.0
# GL_DEPTH_SCALE 1.0
# GL_DEPTH_BIAS 0.0
