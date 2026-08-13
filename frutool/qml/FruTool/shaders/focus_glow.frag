#version 440

layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;

layout(std140, binding = 0) uniform buf {
    float qt_Opacity;
    float iFocused;
    vec4 iGlowColor;
    vec4 iBorderColor;
} ubuf;

void main() {
    vec2 uv = qt_TexCoord0;
    float edgeX = min(uv.x, 1.0 - uv.x);
    float edgeY = min(uv.y, 1.0 - uv.y);
    float edge = min(edgeX, edgeY);
    float border = smoothstep(0.025, 0.0, edge);
    float glow = smoothstep(0.18, 0.0, edge) * ubuf.iFocused * 0.95;
    vec3 col = mix(vec3(0.0), ubuf.iBorderColor.rgb, border * (0.4 + 0.6 * ubuf.iFocused));
    col += ubuf.iGlowColor.rgb * glow;
    float alpha = max(border * 0.85, glow) * ubuf.qt_Opacity;
    fragColor = vec4(col, alpha);
}
