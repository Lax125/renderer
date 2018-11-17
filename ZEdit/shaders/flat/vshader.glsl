#version 130
varying vec4 color;
varying mediump vec2 texCoord;

void main() {
    gl_Position = gl_ModelViewProjectionMatrix * gl_Vertex;
    texCoord = gl_MultiTexCoord0.xy;
    color = gl_Color;
}