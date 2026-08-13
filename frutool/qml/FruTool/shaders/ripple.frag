#version 440

layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;

layout(std140, binding = 0) uniform buf {
    float qt_Opacity;
    float iRippleProgress;
    vec2 iRippleOrigin;
    vec4 iRippleColor;
} ubuf;

void main() {
    vec2 uv = qt_TexCoord0;
    float d = distance(uv, ubuf.iRippleOrigin);
    float radius = ubuf.iRippleProgress * 0.85;
    float ring = smoothstep(0.06, 0.0, abs(d - radius));
    float fade = 1.0 - ubuf.iRippleProgress;
    float alpha = ring * fade * 0.55;
    fragColor = vec4(ubuf.iRippleColor.rgb, alpha * ubuf.qt_Opacity);
}
