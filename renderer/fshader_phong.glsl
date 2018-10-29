#version 130
varying vec3 N;
varying vec3 v;
varying mediump vec2 texCoord;
uniform sampler2D texture;
uniform float diffuse; // how much diffused light a texture reflects
uniform float specular; // how much specular light a texture reflects
uniform float shininess; // how glossy a texture looks
uniform float fresnel; // specular at shallow angles

const int MAX_LIGHTS = 500;
uniform vec3 lPositions[MAX_LIGHTS];
uniform vec3 lColorPowers[MAX_LIGHTS];
uniform int lCount;

float dampen(float n)
{
  return 1.0 - pow(2.7182818, -n);
}

vec3 dampen(vec3 v)
{
  return vec3(dampen(v[0]), dampen(v[1]), dampen(v[2]));
}

float max(vec3 v)
{
  return max(max(v[0], v[1]), v[2]);
}

vec3 propDampen(vec3 v)
{
  float m = max(v);
  float p = dampen(m)/m;
  return vec3(p*v[0], p*v[1], p*v[2]);
}

float dot3(vec3 A, vec3 B) {
  return A[0]*B[0] + A[1]*B[1] + A[2]*B[2];
}

float lengthSquared(vec3 dv) {
  return dv[0]*dv[0] + dv[1]*dv[1] + dv[2]*dv[2];
}

vec3 pow(vec3 v, float e)
{
  return vec3(pow(v[0], e), pow(v[1], e), pow(v[2], e));
}

void main()
{
  if (lCount < 0 || lCount > MAX_LIGHTS) return;
  vec3 texColor = texture2D(texture, texCoord).rgb;
  vec3 texC = texColor*texColor;
  vec3 E = normalize(-v);
  vec3 ambientC = vec3(0.1, 0.1, 0.1)*vec3(0.1, 0.1, 0.1);
  vec3 diffuseC = vec3(0.0, 0.0, 0.0);
  vec3 specularC = vec3(0.0, 0.0, 0.0);
  vec3 fresnelC = vec3(0.0, 0.0, 0.0);

  for (int i = 0; i < lCount; i++) // for each light:
  {
    // L: frag-->lightsrc
    vec3 relPos = lPositions[i] - v;
    float distSquared = lengthSquared(relPos); // for inverse square law
    vec3 L = normalize(relPos);
    // R: frag-->reflectdir
    vec3 R = normalize(reflect(-L, N)); // incident vector I = -L
    // Test if it's on the same side
    float a = dot3(N, L);

    // Calculate diffuse intensity
    float Idiff = diffuse * max(a, 0.0) / distSquared;
    // Calculate specular intensity
    float IspecBase = pow(max(dot3(R, E), 0.0), shininess);
    float Ispec = specular * IspecBase / distSquared;
    float Ifres = fresnel * IspecBase * pow(1-a, 5.0) / distSquared;

    vec3 baseC = lColorPowers[i]*lColorPowers[i];
    diffuseC += baseC*Idiff;
    specularC += baseC*Ispec;
    fresnelC += baseC*Ifres;
  }
  vec3 M = propDampen(ambientC+diffuseC);
  gl_FragColor = vec4((pow(dampen(texC*(M) + specularC + fresnelC), 0.5)), 0.0);
}

