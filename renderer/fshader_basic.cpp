// Assumes that texture to use is bound to

varying vec3 N;
varying vec3 v;

float dampen(float n)
{
  return 1.0 - pow(2.7182818, -n);
}

vec4 dampen(vec4 v)
{
  return vec4(dampen(v[0]), dampen(v[1]), dampen(v[2]), dampen(v[3]));
}
void main (void)
{
  vec3 relPos = gl_LightSource[0].position.xyz - v;
  vec3 L = normalize(gl_LightSource[0].position.xyz - v);
  float distSquared = relPos[0]*relPos[0]
                    + relPos[1]*relPos[1]
                    + relPos[2]*relPos[2];
//    float distSquared = 1.0;
  vec3 E = normalize(-v); // we are in Eye Coordinates, so EyePos is (0,0,0)
  vec3 R = normalize(-reflect(L,N));

  //calculate Ambient Term:
  vec4 Iamb = gl_FrontLightProduct[0].ambient;

  //calculate Diffuse Term:
  vec4 Idiff = gl_FrontLightProduct[0].diffuse * max(dot(N,L), 0.0) / distSquared;
  //Idiff = clamp(Idiff, 0.0, 1.0);

  // calculate Specular Term:
  vec4 Ispec = gl_FrontLightProduct[0].specular
              * pow(max(dot(R,E),0.0),0.3*gl_FrontMaterial.shininess);

  // Account for texture color

  // write Total Color:
  vec4 Itotal = gl_FrontLightModelProduct.sceneColor + Iamb + Idiff + Ispec;
  gl_FragColor = dampen(Itotal);
}
/*
void main (void)
{
  gl_FragColor = vec4(1.0, 0.0, 1.0, 1.0);
}
*/
