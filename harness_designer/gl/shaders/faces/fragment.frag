// ASCII characters only -- this file is read with encoding='ascii' (see
// faces.py's own compile_program()); a non-ASCII byte here raises
// UnicodeDecodeError instead of compiling.
#version 330 core

in vec3 fragPositionGeom;
in vec3 fragNormalGeom;
in float isReflection;
in float fragLocalZGeom;

out vec4 FragColor;

uniform vec4 materialAmbient;
uniform vec4 materialDiffuse;
uniform vec4 materialSpecular;
uniform float materialShininess;
uniform vec4 materialEmissive;

uniform vec3 lightPosition;
uniform vec4 lightAmbient;
uniform vec4 lightDiffuse;
uniform vec4 lightSpecular;

// ===== HEADLIGHT (camera-mounted spotlight) =====
uniform vec3 headlightPosition;

// normalized, points from the light into the scene
uniform vec3 headlightDirection;

uniform vec4 headlightDiffuse;

 // full cone angle, radians
uniform float headlightDiameter;

uniform int headlightEnabled;
// ==================================================

uniform vec3 viewPosition;
uniform float floorY;
uniform float stripeClipStop;
uniform float stripeClipStart;

// ===== EMISSIVE GLOW CONTROLS =====

// Controls glow width (2.0-5.0, default 3.0)
uniform float emissiveRimPower;

// Controls glow brightness (1.0-10.0, default 4.0)
uniform float emissiveRimIntensity;

// ==================================

// Depth-debug view (Config.debug.rendering3d.show_depth, see
// FacesProgram.show_depth in program.py): when nonzero, every fragment
// this program draws replaces its normal lit color with a grayscale
// visualization of its own gl_FragCoord.z -- the actual value the GPU
// compares/writes against the depth buffer, straight from hardware, not
// a value hand-derived from the projection matrix on the Python side.
// Always compiled in; costs one uniform read + branch per fragment when
// left off (the default).
uniform int showDepth;

void main() {
    if (showDepth != 0) {
        FragColor = vec4(vec3(gl_FragCoord.z), 1.0);
        return;
    }

    if (stripeClipStop > 0.0 &&
        (fragLocalZGeom > stripeClipStop || fragLocalZGeom < stripeClipStart)) {
        discard;
    }

    vec3 normal = normalize(fragNormalGeom);
    vec3 viewDir = normalize(viewPosition - fragPositionGeom);

    bool fragAboveFloor = (fragPositionGeom.y > floorY);

    // Check if material is emissive
    float emissiveStrength = max(max(materialEmissive.r, materialEmissive.g), materialEmissive.b);
    bool isEmissive = emissiveStrength > 0.0;

    vec3 ambient = lightAmbient.rgb * materialAmbient.rgb;

    vec3 diffuse = vec3(0.0);
    vec3 specular = vec3(0.0);

    // Only apply lighting to non-emissive materials
    if (!isEmissive) {
        vec3 effectiveLightPos = lightPosition;

        // The floor-side gate below only makes sense for mirrored reflection
        // duplicates (it stops a reflection from being lit as if the light
        // were shining through the floor from the wrong side). Real,
        // non-reflected geometry must always be lit normally -- gating it
        // the same way incorrectly strips diffuse/specular from any actual
        // geometry sitting below floorY whenever the light (camera position)
        // is on the opposite side, which is exactly the case above the floor.
        bool applyLight = true;

        if (isReflection > 0.5) {
            effectiveLightPos.y = 2.0 * floorY - lightPosition.y;
            bool lightAboveFloor = (effectiveLightPos.y > floorY);
            applyLight = (fragAboveFloor == lightAboveFloor);
        }

        if (applyLight) {
            vec3 lightDir = normalize(effectiveLightPos - fragPositionGeom);

            float diffuseStrength = max(dot(normal, lightDir), 0.0);
            diffuse = lightDiffuse.rgb * (diffuseStrength * materialDiffuse.rgb);

            if (diffuseStrength > 0.0) {
                vec3 reflectDir = reflect(-lightDir, normal);
                float specularStrength = pow(max(dot(viewDir, reflectDir), 0.0), materialShininess);
                specular = lightSpecular.rgb * (specularStrength * materialSpecular.rgb);
            }
        }

        // Camera-mounted spotlight -- only lights real geometry, not the
        // mirrored reflection duplicate (the headlight travels with the
        // camera, so a mirrored copy of it doesn't correspond to anything
        // physical the way the scene light's reflection does).
        if (headlightEnabled == 1 && isReflection < 0.5) {
            vec3 headlightDir = normalize(headlightPosition - fragPositionGeom);
            float cosAngle = dot(-headlightDir, normalize(headlightDirection));
            float cosCutoff = cos(headlightDiameter * 0.5);
            float spotFactor = smoothstep(cosCutoff - 0.05, cosCutoff + 0.05, cosAngle);

            if (spotFactor > 0.0) {
                float headDiffuseStrength = max(dot(normal, headlightDir), 0.0);
                diffuse += headlightDiffuse.rgb * (headDiffuseStrength * materialDiffuse.rgb) * spotFactor;
            }
        }
    }

    vec3 result = ambient + diffuse + specular;

    // ===== EMISSIVE GLOW =====
    if (isEmissive) {
        // ALL faces get the full emissive color
        result = materialEmissive.rgb;

        // Edges get EXTRA brightness on top
        float rimAmount = 1.0 - max(dot(viewDir, normal), 0.0);
        rimAmount = pow(rimAmount, emissiveRimPower);
        vec3 rimGlow = materialEmissive.rgb * rimAmount * emissiveRimIntensity;
        result += rimGlow;
    }
    // =========================

    // Preserve the true hue/saturation on overflow instead of letting
    // the implicit per-channel clamp on write do it: scaling every
    // channel down by the same factor keeps their ratio intact, where
    // clamping each channel independently does not (whichever channel
    // hits 1.0 first gets cut relative to the others, visibly shifting/
    // desaturating -- or for a color with one channel already near 1.0,
    // washing the whole thing toward white -- the material's actual
    // color). Applies to BOTH branches above: the rim-glow term is a
    // uniform scalar multiple of materialEmissive.rgb, so rescaling by
    // its own peak channel exactly restores the true emissive color
    // once the glow would otherwise have overflowed, the same as it
    // does for the lit (non-emissive) fill.
    float peak = max(result.r, max(result.g, result.b));
    if (peak > 1.0) {
        result /= peak;
    }

    float alpha = materialDiffuse.a;

    if (isReflection > 0.5) {
        result *= 0.75;
    }

    FragColor = vec4(result, alpha);
}