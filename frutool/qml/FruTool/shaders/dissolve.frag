#version 440

layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;

layout(std140, binding = 0) uniform buf {
    float qt_Opacity;
    float iProgress;
    float iTime;
    vec4 iColor;
} ubuf;

float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

void main() {
    float n = hash(qt_TexCoord0 * 120.0 + ubuf.iTime * 0.01);
    float edge = smoothstep(ubuf.iProgress - 0.08, ubuf.iProgress + 0.02, n);
    float alpha = edge * ubuf.iColor.a;
    fragColor = vec4(ubuf.iColor.rgb, alpha * ubuf.qt_Opacity);
}
