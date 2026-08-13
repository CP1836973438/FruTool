#version 440

layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;

layout(binding = 1) uniform sampler2D source;

layout(std140, binding = 0) uniform buf {
    float qt_Opacity;
    float iBlurRadius;
    vec4 iTintColor;
    vec2 iSourceSize;
    float iVibrancy;
    float iEdgeLight;
    vec2 iPanelOrigin;
    vec2 iPanelSize;
} ubuf;

float rgb_luma(vec3 c) {
    return dot(c, vec3(0.2126, 0.7152, 0.0722));
}

vec3 saturation_boost(vec3 c, float amount) {
    float luma = rgb_luma(c);
    return mix(vec3(luma), c, 1.0 + amount);
}

float hash12(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

vec2 panel_uv(vec2 localCoord) {
    vec2 uv = (ubuf.iPanelOrigin + localCoord * ubuf.iPanelSize) / max(ubuf.iSourceSize, vec2(1.0));
    return clamp(uv, vec2(0.001), vec2(0.999));
}

void main() {
    vec2 uv = panel_uv(qt_TexCoord0);
    vec2 px = 1.0 / max(ubuf.iSourceSize, vec2(1.0));
    float r = max(ubuf.iBlurRadius, 0.5);

    vec2 o0  = vec2(0.0);
    vec2 o1a = px * r * 0.38;
    vec2 o1b = px * r * 0.82;
    vec2 o2a = px * r * 1.28;
    vec2 o2b = px * r * 1.76;

    vec4 c = vec4(0.0);

    c += texture(source, uv) * 0.168;

    c += texture(source, uv + vec2( o1a.x,  0.0 )) * 0.092;
    c += texture(source, uv + vec2(-o1a.x,  0.0 )) * 0.092;
    c += texture(source, uv + vec2( 0.0,   o1a.y)) * 0.092;
    c += texture(source, uv + vec2( 0.0,  -o1a.y)) * 0.092;

    c += texture(source, uv + vec2( o1b.x,  o1b.y)) * 0.058;
    c += texture(source, uv + vec2(-o1b.x,  o1b.y)) * 0.058;
    c += texture(source, uv + vec2( o1b.x, -o1b.y)) * 0.058;
    c += texture(source, uv + vec2(-o1b.x, -o1b.y)) * 0.058;

    c += texture(source, uv + vec2( o2a.x,  0.0 )) * 0.025;
    c += texture(source, uv + vec2(-o2a.x,  0.0 )) * 0.025;
    c += texture(source, uv + vec2( 0.0,   o2a.y)) * 0.025;
    c += texture(source, uv + vec2( 0.0,  -o2a.y)) * 0.025;

    c += texture(source, uv + vec2( o2b.x,  o2b.y)) * 0.010;
    c += texture(source, uv + vec2(-o2b.x,  o2b.y)) * 0.010;
    c += texture(source, uv + vec2( o2b.x, -o2b.y)) * 0.010;
    c += texture(source, uv + vec2(-o2b.x, -o2b.y)) * 0.010;

    vec3 bg = saturation_boost(c.rgb, ubuf.iVibrancy);

    float luma = rgb_luma(bg);
    float tintMix = 0.28 - luma * 0.26;
    tintMix = clamp(tintMix, 0.02, 0.36);
    vec3 glass = mix(bg, ubuf.iTintColor.rgb, tintMix);

    float edge = (1.0 - qt_TexCoord0.x) * 0.55 + (1.0 - qt_TexCoord0.y) * 0.55;
    edge = smoothstep(0.0, 0.28, edge) * ubuf.iEdgeLight;
    glass += vec3(edge * 0.14);

    float dither = (hash12(qt_TexCoord0 * ubuf.iPanelSize + vec2(0.314, 0.727)) - 0.5) * 0.014;
    glass += dither;

    float alpha = ubuf.qt_Opacity * 0.90;
    fragColor = vec4(glass, alpha);
}
