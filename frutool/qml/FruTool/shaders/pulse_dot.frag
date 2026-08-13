#version 440

layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;

layout(std140, binding = 0) uniform buf {
    float qt_Opacity;
    float iTime;
    float iActive;
    vec4 iColor;
} ubuf;

void main() {
    vec2 uv = qt_TexCoord0 * 2.0 - 1.0;
    float d = length(uv);
    float breathe = 0.72 + 0.28 * sin(ubuf.iTime * 2.2);
    float core = smoothstep(0.48, 0.12, d) * ubuf.iActive * breathe;
    float ring = 0.0;
    for (int i = 0; i < 3; i++) {
        float phase = fract(ubuf.iTime * 0.18 + float(i) * 0.33);
        float r = phase * 1.0;
        ring += smoothstep(0.10, 0.0, abs(d - r)) * (1.0 - phase) * 1.05 * ubuf.iActive;
    }
    float halo = smoothstep(0.62, 0.22, d) * 0.38 * ubuf.iActive * breathe;
    float alpha = max(max(core, ring), halo) * ubuf.qt_Opacity;
    fragColor = vec4(ubuf.iColor.rgb, alpha);
}
