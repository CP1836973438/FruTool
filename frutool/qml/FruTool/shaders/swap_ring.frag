#version 440

layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;

layout(std140, binding = 0) uniform buf {
    float qt_Opacity;
    float iTime;
    float iProgress;
    float iPhaseIndex;
    float iPhaseCount;
    float iActive;
    vec4 iAccentColor;
    vec4 iTrackColor;
    vec4 iTextColor;
} ubuf;

const float PI = 3.14159265;

float ringDist(vec2 p, float r, float w) {
    return abs(length(p) - r) - w * 0.5;
}

void main() {
    vec2 uv = qt_TexCoord0 * 2.0 - 1.0;
    uv.x *= 1.0;
    float d = ringDist(uv, 0.72, 0.08);
    float track = 1.0 - smoothstep(0.0, 0.02, d);
    float alpha = track * 0.35;

    float ang = atan(uv.y, uv.x);
    float normAng = (ang + PI) / (2.0 * PI);
    float sweep = fract(normAng - ubuf.iTime * 0.18);
    float scan = smoothstep(0.88, 1.0, sweep) * ubuf.iActive * 1.15;
    float phasePulse = sin(ubuf.iTime * 4.0 + ubuf.iPhaseIndex * 0.8) * 0.5 + 0.5;
    scan *= mix(0.65, 1.0, phasePulse);

    float progAng = ubuf.iProgress * 2.0 * PI - PI * 0.5;
    float pxAng = atan(uv.y, uv.x);
    float progMask = step(pxAng, progAng) * step(0.72 - 0.06, length(uv)) * step(length(uv), 0.72 + 0.06);
    if (ubuf.iProgress < 0.01)
        progMask = 0.0;

    float phaseSlice = 0.0;
    if (ubuf.iPhaseCount > 0.5) {
        float slice = floor(normAng * ubuf.iPhaseCount) / ubuf.iPhaseCount;
        float cur = floor(ubuf.iPhaseIndex) / ubuf.iPhaseCount;
        phaseSlice = step(abs(slice - cur), 0.5 / ubuf.iPhaseCount) * 0.25 * ubuf.iActive;
    }

    vec3 col = ubuf.iTrackColor.rgb * track;
    col = mix(col, ubuf.iAccentColor.rgb, progMask * 0.9 + scan + phaseSlice);

    float core = 1.0 - smoothstep(0.0, 0.35, length(uv));
    col = mix(col, ubuf.iAccentColor.rgb, core * 0.15 * ubuf.iActive);

    alpha = max(alpha, progMask * 0.85 + scan * 0.7 + phaseSlice);
    fragColor = vec4(col, alpha * ubuf.qt_Opacity);
}
