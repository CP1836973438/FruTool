#version 440

layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;

layout(std140, binding = 0) uniform buf {
    float qt_Opacity;
    float iTime;
    float iFlowSpeed;
    vec4 iColorTop;
    vec4 iColorBottom;
    vec4 iAccentColor;
} ubuf;

vec3 blendAccent(vec3 base, vec3 accent, float w) {
    return mix(base, accent, clamp(w, 0.0, 1.0));
}

void main() {
    float t = qt_TexCoord0.y;
    vec3 base = mix(ubuf.iColorBottom.rgb, ubuf.iColorTop.rgb, t);
    float wave = sin((qt_TexCoord0.x * 3.14159 + ubuf.iTime * ubuf.iFlowSpeed) * 2.0) * 0.5 + 0.5;
    float breathe = 0.75 + 0.25 * sin(ubuf.iTime * 2.0);
    float accentW = wave * 0.16 * breathe * (0.4 + 0.6 * t);
    vec3 col = blendAccent(base, ubuf.iAccentColor.rgb, accentW);
    fragColor = vec4(col, ubuf.qt_Opacity);
}
