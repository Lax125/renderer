#version 130
varying vec3 N;
varying vec3 v; // eye coordinates
varying mediump vec2 texCoord;
varying vec4 color;

void main(void)
{
    v = vec3(gl_ModelViewMatrix * gl_Vertex);
    N = normalize(gl_NormalMatrix * gl_Normal);
    texCoord = gl_MultiTexCoord0.xy;
    gl_Position = gl_ModelViewProjectionMatrix * gl_Vertex;
    color = gl_Color;
}
