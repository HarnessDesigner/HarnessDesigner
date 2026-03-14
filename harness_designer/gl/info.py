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


def get():
    global _info

    if _info is None:
        # Create a temporary wx.App if one doesn't exist
        # This is necessary for wx.glcanvas to work
        temp_app = None
        if not wx.App.Get():
            temp_app = wx.App(False)  # Don't redirect stdout/stderr
        
        try:
            # Create a minimal hidden frame for GL context
            # Position it off-screen and use flags to prevent it from showing
            frame = wx.Frame(
                None, 
                -1, 
                "GL Info", 
                pos=(-10000, -10000),  # Far off-screen
                size=(1, 1),
                style=wx.FRAME_NO_TASKBAR | wx.NO_BORDER | wx.STAY_ON_TOP
            )
            
            try:
                # Create GL canvas with minimal attributes
                canvas = glcanvas.GLCanvas(frame, -1, size=(1, 1))
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
                # Clean up - destroy the frame
                frame.Destroy()
        finally:
            # Clean up temporary app if we created one
            if temp_app:
                temp_app.Destroy()

    return _info


# GL_MAX_COLOR_ATTACHMENTS 	8
# GL_MAX_SAMPLES 	64
# GL_MAX_LIGHTS 	8
# GL_MAX_CLIP_PLANES 	8
# GL_MAX_MODELVIEW_STACK_DEPTH 	32
# GL_MAX_PROJECTION_STACK_DEPTH 	4
# GL_MAX_TEXTURE_STACK_DEPTH 	10
# GL_MAX_ATTRIB_STACK_DEPTH 	16
# GL_MAX_COLOR_MATRIX_STACK_DEPTH 	2
# GL_MAX_LIST_NESTING 	64
# GL_MAX_TEXTURE_UNITS 	4
# GL_MAX_TEXTURE_COORDS 	8
# GL_MIN_PROGRAM_TEXTURE_GATHER_OFFSET 	-32
# GL_MAX_PROGRAM_TEXTURE_GATHER_OFFSET 	31
# GL_MAX_SUBROUTINES 	1,024
# GL_MAX_SUBROUTINE_UNIFORM_LOCATIONS 	1,024
# GL_MAX_COMBINED_TESS_CONTROL_UNIFORM_COMPONENTS 	231,424
# GL_MAX_COMBINED_TESS_EVALUATION_UNIFORM_COMPONENTS 	231,424
# GL_MAX_GEOMETRY_OUTPUT_VERTICES 	1,024
# GL_MAX_GEOMETRY_TOTAL_OUTPUT_COMPONENTS 	1,024
# GL_MAX_GEOMETRY_SHADER_INVOCATIONS 	32
# GL_MAX_VERTEX_STREAMS 	4
# GL_MAX_TESS_GEN_LEVEL 	64
# GL_MAX_PATCH_VERTICES 	32
# GL_MAX_TESS_CONTROL_UNIFORM_COMPONENTS 	2,048
# GL_MAX_TESS_VALUATION_UNIFORM_COMPONENTS 	2,048
# GL_MAX_TESS_CONTROL_TEXTURE_IMAGE_UNITS 	32
# GL_MAX_TESS_EVALUATION_TEXTURE_IMAGE_UNITS 	32
# GL_MAX_TESS_CONTROL_OUTPUT_COMPONENTS 	128
# GL_MAX_TESS_PATCH_COMPONENTS 	120
# GL_MAX_TESS_CONTROL_TOTAL_OUTPUT_COMPONENTS 	4,216
# GL_MAX_TESS_EVALUATION_OUTPUT_COMPONENTS 	128
# GL_MAX_TESS_CONTROL_INPUT_COMPONENTS 	128
# GL_MAX_TESS_EVALUATION_INPUT_COMPONENTS 	128
# GL_MAX_TESS_CONTROL_UNIFORM_BLOCKS 	14
# GL_MAX_TESS_EVALUATION_UNIFORM_BLOCKS 	14
# GL_MAX_TRANSFORM_FEEDBACK_INTERLEAVED_COMPONENTS 	128
# GL_MAX_TRANSFORM_FEEDBACK_SEPARATE_ATTRIBS 	4
# GL_MAX_TRANSFORM_FEEDBACK_SEPARATE_COMPONENTS 	4
# GL_MAX_TRANSFORM_FEEDBACK_BUFFERS 	4
# GL_NUM_SHADING_LANGUAGE_VERSIONS 	26
# GL_MAX_FRAGMENT_INTERPOLATION_OFFSET 	1
# GL_MIN_FRAGMENT_INTERPOLATION_OFFSET 	-1
# GL_MAX_PROGRAM_TEXTURE_GATHER_COMPONENTS 	4
# GL_MIN_SAMPLE_SHADING_VALUE 	0
# GL_MAX_ATOMIC_COUNTER_BUFFER_BINDINGS 	8
# GL_MAX_ATOMIC_COUNTER_BUFFER_SIZE 	65,536
# GL_MAX_COMBINED_ATOMIC_COUNTER_BUFFERS 	48
# GL_MAX_FRAGMENT_ATOMIC_COUNTER_BUFFERS 	8
# GL_MAX_GEOMETRY_ATOMIC_COUNTER_BUFFERS 	8
# GL_MAX_TESS_EVALUATION_ATOMIC_COUNTER_BUFFERS 	8
# GL_MAX_TESS_CONTROL_ATOMIC_COUNTER_BUFFERS 	8
# GL_MAX_VERTEX_ATOMIC_COUNTER_BUFFERS 	8
# GL_MAX_VERTEX_ATTRIB_STRIDE 	2,04
# GL_MAX_GEOMETRY_VARYING_COMPONENTS_ARB 	124
# GL_MAX_VERTEX_VARYING_COMPONENTS_ARB 	124
# GL_MAX_COMBINED_SHADER_OUTPUT_RESOURCES 	16
# GL_MAX_SHADER_STORAGE_BLOCK_SIZE 	2,147,483,647
# GL_MAX_COMPUTE_SHARED_MEMORY_SIZE 	49,152
# GL_MAX_COMPUTE_IMAGE_UNIFORMS 	8
# GL_MAX_COMPUTE_FIXED_GROUP_INVOCATIONS_ARB 	1,024
# GL_MAX_COMPUTE_FIXED_GROUP_SIZE_ARB
# GL_MAX_COMPUTE_VARIABLE_GROUP_INVOCATIONS_ARB 	1,024
# GL_MAX_COMPUTE_VARIABLE_GROUP_SIZE_ARB
# GL_MAX_DEBUG_MESSAGE_LENGTH_ARB 	1,024
# GL_MAX_DEBUG_LOGGED_MESSAGES_ARB 	128
# GL_MAX_DRAW_BUFFERS_ARB 	8
# GL_MAX_PROGRAM_ALU_INSTRUCTIONS_ARB 	65,536
# GL_MAX_PROGRAM_TEX_INSTRUCTIONS_ARB 	65,536
# GL_MAX_PROGRAM_TEX_INDIRECTIONS_ARB 	65,536
# GL_MAX_PROGRAM_NATIVE_ALU_INSTRUCTIONS_ARB 	65,536
# GL_MAX_PROGRAM_NATIVE_TEX_INSTRUCTIONS_ARB 	65,536
# GL_MAX_PROGRAM_NATIVE_TEX_INDIRECTIONS_ARB 	65,536
# GL_MAX_IMAGE_UNITS 	8
# GL_MAX_COMBINED_IMAGE_UNITS_AND_FRAGMENT_OUTPUTS 	16
# GL_MAX_VERTEX_IMAGE_UNIFORMS 	8
# GL_MAX_TESS_CONTROL_IMAGE_UNIFORMS 	8
# GL_MAX_TESS_EVALUATION_IMAGE_UNIFORMS 	8
# GL_MAX_GEOMETRY_IMAGE_UNIFORMS 	8
# GL_MAX_FRAGMENT_IMAGE_UNIFORMS 	8
# GL_MAX_COMBINED_IMAGE_UNIFORMS 	48
# GL_MAX_SPARSE_TEXTURE_SIZE_ARB 	32,768
# GL_MAX_SPARSE_3D_TEXTURE_SIZE_ARB 	16,384
# GL_MAX_SPARSE_ARRAY_TEXTURE_LAYERS_ARB 	2,048
# GL_NUM_COMPRESSED_TEXTURE_FORMATS_ARB 	23
# GL_MAX_PROGRAM_MATRIX_STACK_DEPTH_ARB 	1
# GL_MAX_PROGRAM_MATRICES_ARB 	8
# GL_MAX_VERTEX_ATTRIBS_ARB 	16
# GL_MAX_PROGRAM_INSTRUCTIONS_ARB 	65,536
# GL_MAX_PROGRAM_NATIVE_INSTRUCTIONS_ARB 	65,536
# GL_MAX_PROGRAM_TEMPORARIES_ARB 	4,096
# GL_MAX_PROGRAM_NATIVE_TEMPORARIES_ARB 	4,096
# GL_MAX_PROGRAM_PARAMETERS_ARB 	1,024
# GL_MAX_PROGRAM_NATIVE_PARAMETERS_ARB 	1,024
# GL_MAX_PROGRAM_ATTRIBS_ARB 	16
# GL_MAX_PROGRAM_NATIVE_ATTRIBS_ARB 	16
# GL_MAX_PROGRAM_ADDRESS_REGISTERS_ARB 	2
# GL_MAX_PROGRAM_NATIVE_ADDRESS_REGISTERS_ARB 	2
# GL_MAX_PROGRAM_LOCAL_PARAMETERS_ARB 	1,024
# GL_MAX_PROGRAM_ENV_PARAMETERS_ARB 	256
# GL_MAX_SHADER_COMPILER_THREADS_ARB 	-1
# '''
#
# '''
# rough estimate of the largest texture that the GL can handle
# GL.glGetIntegerv(GL.GL_MAX_TEXTURE_SIZE)
#
# rough estimate of the largest 3D texture that the GL can handle
# GL.glGetIntegerv(GL.GL_MAX_3D_TEXTURE_SIZE)
#
# rough estimate of the largest cube-map texture that the GL can handle.
# GL.glGetIntegerv(GL.GL_MAX_CUBE_MAP_TEXTURE_SIZE)
#
# maximum, absolute value of the texture level-of-detail bias
# GL.glGetIntegerv(GL.GL_MAX_TEXTURE_LOD_BIAS)
#
# maximum number of layers allowed in an array texture
# GL.glGetIntegerv(GL.GL_MAX_ARRAY_TEXTURE_LAYERS)
#
# maximum number of application-defined clipping distances.
# GL.glGetIntegerv(GL.GL_MAX_CLIP_DISTANCES)
#
# maximum number of texels allowed in the texel array of a texture buffer object
# GL.glGetIntegerv(GL.GL_MAX_TEXTURE_BUFFER_SIZE)
#
# rough estimate of the largest rectangular texture that the GL can handle
# GL.glGetIntegerv(GL.GL_MAX_RECTANGLE_TEXTURE_SIZE)
#
# maximum supported size for renderbuffers
# GL.glGetIntegerv(GL.GL_MAX_RENDERBUFFER_SIZE)
#
# maximum supported width and height of the viewport
# GL.glGetIntegerv(GL.GL_MAX_VIEWPORT_DIMS[0])
# GL.glGetIntegerv(GL.GL_MAX_VIEWPORT_DIMS[1])
#
# estimate of the number of bits of subpixel resolution that are used to position rasterized geometry in window coordinates
# GL.glGetIntegerv(GL.GL_SUBPIXEL_BITS)
#
# recommended maximum number of vertex array indices.
# GL.glGetIntegerv(GL.GL_MAX_ELEMENTS_INDICES)
#
# recommended maximum number of vertex array vertices.
# GL.glGetIntegerv(GL.GL_MAX_ELEMENTS_VERTICES)
#
# maximum number of sample mask words.
# GL.glGetIntegerv(GL.GL_MAX_SAMPLE_MASK_WORDS)
#
# maximum number of samples in a color multisample texture.
# GL.glGetIntegerv(GL.GL_MAX_COLOR_TEXTURE_SAMPLES)
#
# maximum number of samples in a multisample depth or depth-stencil texture.
# GL.glGetIntegerv(GL.GL_MAX_DEPTH_TEXTURE_SAMPLES)
#
# maximum number of samples supported in integer format multisample buffers.
# GL.glGetIntegerv(GL.GL_MAX_INTEGER_SAMPLES)
#
# maximum number of 4-component generic vertex attributes accessible to a vertex shader
# GL.glGetIntegerv(GL.GL_MAX_VERTEX_ATTRIBS)
#
# maximum number of individual floating-point, integer, or boolean values that can be held in uniform variable storage for a vertex shader
# GL.glGetIntegerv(GL.GL_MAX_VERTEX_UNIFORM_COMPONENTS)
#
# maximum number of simultaneous outputs that may be written in a fragment shader.
# GL.glGetIntegerv(GL.GL_MAX_DRAW_BUFFERS)
#
# maximum number of 4-vectors that may be held in uniform variable storage for the vertex shader
# GL.glGetIntegerv(GL.GL_MAX_VERTEX_UNIFORM_VECTORS)
#
# maximum number of uniform blocks per vertex shader
# GL.glGetIntegerv(GL.GL_MAX_VERTEX_UNIFORM_BLOCKS)
#
# maximum number of components of output written by a vertex shader
# GL.glGetIntegerv(GL.GL_MAX_VERTEX_OUTPUT_COMPONENTS)
#
# maximum supported texture image units that can be used to access texture maps from the vertex shader
# GL.glGetIntegerv(GL.GL_MAX_VERTEX_TEXTURE_IMAGE_UNITS)
#
# maximum number of individual floating-point, integer, or boolean values that can be held in uniform variable storage for a fragment shader
# GL.glGetIntegerv(GL.GL_MAX_FRAGMENT_UNIFORM_COMPONENTS)
#
# maximum number of individual 4-vectors of floating-point, integer, or boolean values that can be held in uniform variable storage for a fragment shader.
# GL.glGetIntegerv(GL.GL_MAX_FRAGMENT_UNIFORM_VECTORS)
#
# maximum number of uniform blocks per fragment shader.
# GL.glGetIntegerv(GL.GL_MAX_FRAGMENT_UNIFORM_BLOCKS)
#
# maximum number of components of the inputs read by the fragment shader
# GL.glGetIntegerv(GL.GL_MAX_FRAGMENT_INPUT_COMPONENTS)
#
# maximum supported texture image units that can be used to access texture maps from the fragment shader
# GL.glGetIntegerv(GL.GL_MAX_TEXTURE_IMAGE_UNITS)
#
# minimum texel offset allowed in a texture lookup
# GL.glGetIntegerv(GL.GL_MIN_PROGRAM_TEXEL_OFFSET)
#
# maximum texel offset allowed in a texture lookup
# GL.glGetIntegerv(GL.GL_MAX_PROGRAM_TEXEL_OFFSET)
#
# maximum number of uniform buffer binding points on the contex
# GL.glGetIntegerv(GL.GL_MAX_UNIFORM_BUFFER_BINDINGS)
#
# maximum size in basic machine units of a uniform block
# GL.glGetIntegerv(GL.GL_MAX_UNIFORM_BLOCK_SIZE)
#
# minimum required alignment for uniform buffer sizes and offset
# GL.glGetIntegerv(GL.GL_UNIFORM_BUFFER_OFFSET_ALIGNMENT)
#
# maximum number of uniform blocks per program.
# GL.glGetIntegerv(GL.GL_MAX_COMBINED_UNIFORM_BLOCKS)
#
# number components for varying variables
# GL.glGetIntegerv(GL.GL_MAX_VARYING_COMPONENTS)
#
# number 4-vectors for varying variables
# GL.glGetIntegerv(GL.GL_MAX_VARYING_VECTORS)
#
# maximum supported texture image units that can be used to access texture maps from the vertex shader and the fragment processor combined.
# GL.glGetIntegerv(GL.GL_MAX_COMBINED_TEXTURE_IMAGE_UNITS)
#
# number of words for vertex shader uniform variables in all uniform blocks (including default).
# GL.glGetIntegerv(GL.GL_MAX_COMBINED_VERTEX_UNIFORM_COMPONENTS)
#
# number of words for geometry shader uniform variables in all uniform blocks (including default).
# GL.glGetIntegerv(GL.GL_MAX_COMBINED_GEOMETRY_UNIFORM_COMPONENTS)
#
# number of words for fragment shader uniform variables in all uniform blocks (including default).
# GL.glGetIntegerv(GL.GL_MAX_COMBINED_FRAGMENT_UNIFORM_COMPONENTS)
#
# maximum number of interpolators available for processing varying variables used by vertex and fragment shaders
# GL.glGetIntegerv(GL.GL_MAX_VARYING_FLOATS)
#
# maximum number of uniform blocks per geometry shader
# GL.glGetIntegerv(GL.GL_MAX_GEOMETRY_UNIFORM_BLOCKS)
#
# maximum number of components of inputs read by a geometry shader
# GL.glGetIntegerv(GL.GL_MAX_GEOMETRY_INPUT_COMPONENTS)
#
# maximum number of components of outputs written by a geometry shader
# GL.glGetIntegerv(GL.GL_MAX_GEOMETRY_OUTPUT_COMPONENTS)
#
# maximum supported texture image units that can be used to access texture maps from the geometry shader
# GL.glGetIntegerv(GL.GL_MAX_GEOMETRY_TEXTURE_IMAGE_UNITS)
#
# major version number of the OpenGL API supported by the current context.
# GL.glGetIntegerv(GL.GL_MAJOR_VERSION)
#
# minor version number of the OpenGL API supported by the current context.
# GL.glGetIntegerv(GL.GL_MINOR_VERSION)
#
# minimum alignment in basic machine units of pointers returned fromglMapBuffer and glMapBufferRange.
# GL.glGetIntegerv(GL.GL_MIN_MAP_BUFFER_ALIGNMENT)
#
# maximum number of atomic counters available to all active shaders.
# GL.glGetIntegerv(GL.GL_MAX_COMBINED_ATOMIC_COUNTERS)
#
# maximum number of atomic counters available to fragment shaders.
# GL.glGetIntegerv(GL.GL_MAX_FRAGMENT_ATOMIC_COUNTERS)
#
# maximum number of atomic counters available to geometry shaders
# GL.glGetIntegerv(GL.GL_MAX_GEOMETRY_ATOMIC_COUNTERS)
#
# maximum number of atomic counters available to tessellation evaluation shaders
# GL.glGetIntegerv(GL.GL_MAX_TESS_EVALUATION_ATOMIC_COUNTERS)
#
# maximum number of atomic counters available to tessellation control shaders
# GL.glGetIntegerv(GL.GL_MAX_TESS_CONTROL_ATOMIC_COUNTERS)
#
# maximum number of atomic counters available to vertex shaders
# GL.glGetIntegerv(GL.GL_MAX_VERTEX_ATOMIC_COUNTERS)
#
# maximum number of individual floating-point, integer, or boolean values that can be held in uniform variable storage for a geometry shader
# GL.glGetIntegerv(GL.GL_MAX_GEOMETRY_UNIFORM_COMPONENTS)
#
# number of binary shader formats supported by the implementation
# GL.glGetIntegerv(GL.GL_NUM_SHADER_BINARY_FORMATS)
#
# maximum index that may be specified during the transfer of generic vertex attributes to the GL.
# GL.glGetIntegerv(GL.GL_MAX_ELEMENT_INDEX)
#
# maximum offset that may be added to a vertex binding offset.
# GL.glGetIntegerv(GL.GL_MAX_VERTEX_ATTRIB_RELATIVE_OFFSET)
#
# maximum number of vertex buffers that may be bound.
# GL.glGetIntegerv(GL.GL_MAX_VERTEX_ATTRIB_BINDINGS)
#
# maximum number of active shader storage blocks that may be accessed by a vertex shader
# GL.glGetIntegerv(GL.GL_MAX_VERTEX_SHADER_STORAGE_BLOCKS)
#
# maximum number of active shader storage blocks that may be accessed by a geometry shader.
# GL.glGetIntegerv(GL.GL_MAX_GEOMETRY_SHADER_STORAGE_BLOCKS)
#
# maximum number of active shader storage blocks that may be accessed by a tessellation control shader
# GL.glGetIntegerv(GL.GL_MAX_TESS_CONTROL_SHADER_STORAGE_BLOCKS)
#
# maximum number of active shader storage blocks that may be accessed by a tessellation evaluation shader
# GL.glGetIntegerv(GL.GL_MAX_TESS_EVALUATION_SHADER_STORAGE_BLOCKS)
#
# maximum number of active shader storage blocks that may be accessed by a fragment shader.
# GL.glGetIntegerv(GL.GL_MAX_FRAGMENT_SHADER_STORAGE_BLOCKS)
#
# maximum number of active shader storage blocks that may be accessed by a compute shader.
# GL.glGetIntegerv(GL.GL_MAX_COMPUTE_SHADER_STORAGE_BLOCKS)
#
# maximum total number of active shader storage blocks that may be accessed by all active shaders.
# GL.glGetIntegerv(GL.GL_MAX_COMBINED_SHADER_STORAGE_BLOCKS)
#
# maximum number of shader storage buffer binding points on the context
# GL.glGetIntegerv(GL.GL_MAX_SHADER_STORAGE_BUFFER_BINDINGS)
#
# maximum number of individual floating-point, integer, or boolean values that can be held in uniform variable storage for a compute shader
# GL.glGetIntegerv(GL.GL_MAX_COMPUTE_UNIFORM_COMPONENTS)
#
# maximum number of atomic counter buffers that may be accessed by a compute shader.
# GL.glGetIntegerv(GL.GL_MAX_COMPUTE_ATOMIC_COUNTER_BUFFERS)
#
# maximum number of atomic counters available to compute shaders.
# GL.glGetIntegerv(GL.GL_MAX_COMPUTE_ATOMIC_COUNTERS)
#
# the number of words for compute shader uniform variables in all uniform blocks (including default).
# GL.glGetIntegerv(GL.GL_MAX_COMBINED_COMPUTE_UNIFORM_COMPONENTS)
#
# the number of invocations in a single local work group (i.e., the product of the three dimensions) that may be dispatched to a compute shader.
# GL.glGetIntegerv(GL.GL_MAX_COMPUTE_WORK_GROUP_INVOCATIONS)
#
# maximum number of uniform blocks per compute shader
# GL.glGetIntegerv(GL.GL_MAX_COMPUTE_UNIFORM_BLOCKS)
#
# maximum supported texture image units that can be used to access texture maps from the compute shader.
# GL.glGetIntegerv(GL.GL_MAX_COMPUTE_TEXTURE_IMAGE_UNITS)
#
# maximum number of work groups that may be dispatched to a compute shader. Indices 0, 1, and 2 correspond to the X, Y and Z dimensions, respectively.
# GL.glGetIntegeri_v(GL.GL_MAX_COMPUTE_WORK_GROUP_COUNT, 0)
# GL.glGetIntegeri_v(GL.GL_MAX_COMPUTE_WORK_GROUP_COUNT, 1)
# GL.glGetIntegeri_v(GL.GL_MAX_COMPUTE_WORK_GROUP_COUNT, 2)
#
#
# maximum size of a work groups that may be used during compilation of a compute shader. Indices 0, 1, and 2 correspond to the X, Y and Z dimensions, respectively.
# GL.glGetIntegeri_v(GL.GL_MAX_COMPUTE_WORK_GROUP_SIZE, 0)
# GL.glGetIntegeri_v(GL.GL_MAX_COMPUTE_WORK_GROUP_SIZE, 1)
# GL.glGetIntegeri_v(GL.GL_MAX_COMPUTE_WORK_GROUP_SIZE, 2)
#
# maximum depth of the debug message group stack.
# GL.glGetIntegerv(GL.GL_MAX_DEBUG_GROUP_STACK_DEPTH)
#
# maximum length of a label that may be assigned to an object
# GL.glGetIntegerv(GL.GL_MAX_LABEL_LENGTH)
#
# maximum number of explicitly assignable uniform locations
# GL.glGetIntegerv(GL.GL_MAX_UNIFORM_LOCATIONS)
#
# maximum number of individual floating-point, integer, or boolean values that can be held in uniform variable storage for a fragment shader.
# GL.glGetIntegerv(GL.GL_MAX_FRAGMENT_UNIFORM_COMPONENTS_ARB)
#
# maximum width for a framebuffer that has no attachments
# GL.glGetIntegerv(GL.GL_MAX_FRAMEBUFFER_WIDTH)
#
# maximum height for a framebuffer that has no attachments
# GL.glGetIntegerv(GL.GL_MAX_FRAMEBUFFER_HEIGHT)
#
# maximum number of layers for a framebuffer that has no attachments
# GL.glGetIntegerv(GL.GL_MAX_FRAMEBUFFER_LAYERS)
#
# maximum samples in a framebuffer that has no attachments
# GL.glGetIntegerv(GL.GL_MAX_FRAMEBUFFER_SAMPLES)
#
# number of program binary formats supported by the implementation
# GL.glGetIntegerv(GL.GL_NUM_PROGRAM_BINARY_FORMATS)
#
# maximum glWaitSync timeout interval.
# GL.glGetIntegerv(GL.GL_MAX_SERVER_WAIT_TIMEOUT)
#
# number of extensions supported by the GL implementation for the current context
# GL.glGetIntegerv(GL.GL_NUM_EXTENSIONS)
#
# maximum number of simultaneous viewports that are supported
# GL.glGetIntegerv(GL.GL_MAX_VIEWPORTS)
#
# maximum number of active draw buffers when using dual-source blending.
# GL.glGetIntegerv(GL.GL_MAX_DUAL_SOURCE_DRAW_BUFFERS)
#
# minimum required alignment for texture buffer sizes and offset
# GL.glGetIntegerv(GL.GL_TEXTURE_BUFFER_OFFSET_ALIGNMENT)
#
# minimum required alignment for shader storage buffer sizes and offset
# GL.glGetIntegerv(GL.GL_SHADER_STORAGE_BUFFER_OFFSET_ALIGNMENT)
#
# # number of bits of sub-pixel precision which the GL uses to interpret the floating point viewport bounds
# GL.glGetIntegerv(GL.GL_VIEWPORT_SUBPIXEL_BITS)
