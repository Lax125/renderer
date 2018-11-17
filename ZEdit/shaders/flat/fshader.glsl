#version 130
varying vec4 color;
varying mediump vec2 texCoord;
uniform sampler2D texture;

void main() {
    gl_FragColor = texture2D(texture, texCoord) * color;
}