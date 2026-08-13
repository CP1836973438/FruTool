#version 440

layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;

layout(binding = 1) uniform sampler2D source;

layout(std140, binding = 0) uniform buf {
    float qt_Opacity;
    float iBlurRadius;
    vec4 iTintColor;
    vec2 iSourceSize;
} ubuf;

void main() {
    vec2 px = 1.0 / max(ubuf.iSourceSize, vec2(1.0));
    vec2 off = px * ubuf.iBlurRadius;

    vec4 c = texture(source, qt_TexCoord0) * 0.20;
    c += texture(source, qt_TexCoord0 + vec2(off.x, 0.0)) * 0.10;
    c += texture(source, qt_TexCoord0 + vec2(-off.x, 0.0)) * 0.10;
    c += texture(source, qt_TexCoord0 + vec2(0.0, off.y)) * 0.10;
    c += texture(source, qt_TexCoord0 + vec2(0.0, -off.y)) * 0.10;
    c += texture(source, qt_TexCoord0 + vec2(off.x, off.y)) * 0.10;
    c += texture(source, qt_TexCoord0 + vec2(-off.x, off.y)) * 0.10;
    c += texture(source, qt_TexCoord0 + vec2(off.x, -off.y)) * 0.10;
    c += texture(source, qt_TexCoord0 + vec2(-off.x, -off.y)) * 0.10;

    vec3 frosted = mix(c.rgb, ubuf.iTintColor.rgb, 0.42);
    float alpha = ubuf.qt_Opacity * 0.88;
    fragColor = vec4(frosted, alpha);
}
