const canvas = document.getElementById('material')
const statusEl = document.getElementById('status')
const motionButton = document.getElementById('motion')

const gl = canvas.getContext('webgl', { alpha: true, antialias: false, premultipliedAlpha: true })
if (!gl) {
  statusEl.textContent = 'WEBGL UNAVAILABLE'
  throw new Error('WebGL unavailable')
}

const vertexSource = `
attribute vec2 a_position;
varying vec2 v_uv;
void main(){
  v_uv = a_position * 0.5 + 0.5;
  gl_Position = vec4(a_position,0.0,1.0);
}
`

const fragmentSource = `
precision highp float;
varying vec2 v_uv;
uniform vec2 u_resolution;
uniform float u_time;
uniform vec2 u_tilt;

float hash(vec2 p){
  p = fract(p * vec2(123.34,456.21));
  p += dot(p,p + 45.32);
  return fract(p.x * p.y);
}
float noise(vec2 p){
  vec2 i = floor(p);
  vec2 f = fract(p);
  f = f*f*(3.0-2.0*f);
  float a = hash(i);
  float b = hash(i + vec2(1.0,0.0));
  float c = hash(i + vec2(0.0,1.0));
  float d = hash(i + vec2(1.0,1.0));
  return mix(mix(a,b,f.x),mix(c,d,f.x),f.y);
}

float fbm(vec2 p){
  float v = 0.0;
  float a = 0.5;
  for(int i=0;i<5;i++){
    v += a * noise(p);
    p = mat2(1.62,1.17,-1.17,1.62) * p + 0.17;
    a *= 0.5;
  }
  return v;
}

vec3 environment(vec2 p){
  vec3 base = vec3(.006,.025,.043);
  float upper = exp(-4.6*length(p-vec2(-.04,-.18)));
  float lower = exp(-5.8*length(p-vec2(.20,.24)));
  base += vec3(.025,.075,.105) * upper;
  base += vec3(.16,.085,.018) * lower;
  return base;
}

void main(){
  vec2 p = v_uv - 0.5;
  p.x *= u_resolution.x / max(u_resolution.y,1.0);

  float t = u_time * 0.060;
  vec2 tilt = u_tilt * .16;
  vec2 flow = vec2(t*.26,-t*.18);

  float nA = fbm(p*2.1 + flow + tilt);
  float nB = fbm(p*3.4 - flow*1.25 + vec2(nA*.85));
  vec2 warp = vec2(nA-.5,nB-.5) * .23;

  vec2 q = p + warp;
  float sheet = fbm(q*1.72 + vec2(-t*.55,t*.42));
  float sheet2 = fbm((q+vec2(sheet*.24))*2.55 - vec2(t*.35,0.0));
  float field = sheet*.66 + sheet2*.34;

  float eps = .010;
  float fx = fbm((q+vec2(eps,0.0))*1.72 + vec2(-t*.55,t*.42));
  float fy = fbm((q+vec2(0.0,eps))*1.72 + vec2(-t*.55,t*.42));
  vec2 normal = normalize(vec2(fx-sheet,fy-sheet)+vec2(.0001));

  float ribbonA = .5 + .5*sin(q.x*5.8 + q.y*2.2 + nB*3.2 + t*1.35);
  float ribbonB = .5 + .5*sin(q.y*7.2 - q.x*1.8 - nA*3.0 - t*1.10);
  float liquid = smoothstep(.53,.71,field + (ribbonA+ribbonB-1.0)*.055);

  float edge = smoothstep(.028,.095,length(vec2(fx-sheet,fy-sheet)));
  float fresnel = pow(1.0-max(dot(normalize(vec3(normal,.70)),vec3(.0,.0,1.0)),0.0),2.6);

  vec2 refractedUv = p + normal*(.045 + liquid*.055) + tilt*.025;
  vec3 color = environment(refractedUv);

  float c1 = sin((q.x+normal.x*.05)*14.0 + t*2.1 + nB*3.0);
  float c2 = sin((q.y-normal.y*.05)*16.0 - t*1.8 - nA*3.1);
  float caustic = smoothstep(1.32,1.92,c1+c2+field*.72);

  vec3 glassBlue = vec3(.055,.18,.24);
  vec3 gold = vec3(.98,.64,.18);
  vec3 pale = vec3(.72,.86,.93);

  color = mix(color,color + glassBlue*.18,liquid*.56);
  color += pale * edge * (.035 + fresnel*.07) * liquid;
  color += gold * caustic * (.055 + liquid*.10);

  vec2 heroP = p - vec2(0.0,.19);
  float heroMask = 1.0-smoothstep(.18,.50,length(heroP*vec2(.82,1.12)));
  float feather = smoothstep(.0,.22,heroMask);
  float alpha = feather * (.045 + liquid*.17 + edge*.055 + caustic*.055);

  gl_FragColor = vec4(color,alpha);
}
`
function compile(type, source){
  const shader = gl.createShader(type)
  gl.shaderSource(shader, source)
  gl.compileShader(shader)
  if(!gl.getShaderParameter(shader, gl.COMPILE_STATUS)){
    throw new Error(gl.getShaderInfoLog(shader) || 'Shader compile error')
  }
  return shader
}

const program = gl.createProgram()
gl.attachShader(program, compile(gl.VERTEX_SHADER, vertexSource))
gl.attachShader(program, compile(gl.FRAGMENT_SHADER, fragmentSource))
gl.linkProgram(program)
if(!gl.getProgramParameter(program, gl.LINK_STATUS)){
  throw new Error(gl.getProgramInfoLog(program) || 'Program link error')
}
gl.useProgram(program)

const buffer = gl.createBuffer()
gl.bindBuffer(gl.ARRAY_BUFFER, buffer)
gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([
  -1,-1, 1,-1, -1,1,
  -1,1, 1,-1, 1,1
]),gl.STATIC_DRAW)

const position = gl.getAttribLocation(program,'a_position')
gl.enableVertexAttribArray(position)
gl.vertexAttribPointer(position,2,gl.FLOAT,false,0,0)
const resolution = gl.getUniformLocation(program,'u_resolution')
const timeUniform = gl.getUniformLocation(program,'u_time')
const tiltUniform = gl.getUniformLocation(program,'u_tilt')
const target = { x:0, y:0 }
const current = { x:0, y:0 }
let raf = 0
const started = performance.now()

function resize(){
  const dpr = Math.min(window.devicePixelRatio || 1,1.6)
  const rect = canvas.getBoundingClientRect()
  const width = Math.max(1,Math.round(rect.width*dpr))
  const height = Math.max(1,Math.round(rect.height*dpr))
  if(canvas.width !== width || canvas.height !== height){
    canvas.width = width
    canvas.height = height
    gl.viewport(0,0,width,height)
  }
}

function render(now){
  resize()
  current.x += (target.x-current.x)*.035
  current.y += (target.y-current.y)*.035
  gl.uniform2f(resolution,canvas.width,canvas.height)
  gl.uniform1f(timeUniform,(now-started)/1000)
  gl.uniform2f(tiltUniform,current.x,current.y)
  gl.drawArrays(gl.TRIANGLES,0,6)
  raf = requestAnimationFrame(render)
}
window.addEventListener('pointermove',(event)=>{
  target.x = (event.clientX/window.innerWidth-.5)*2
  target.y = (event.clientY/window.innerHeight-.5)*-2
},{passive:true})

function handleOrientation(event){
  if(event.gamma == null || event.beta == null) return
  target.x = Math.max(-1,Math.min(1,event.gamma/28))
  target.y = Math.max(-1,Math.min(1,(event.beta-45)/38))
  motionButton.textContent = 'حرکت گوشی فعال است'
}

window.addEventListener('deviceorientation',handleOrientation,{passive:true})

motionButton.addEventListener('click',async()=>{
  const Orientation = window.DeviceOrientationEvent
  if(typeof Orientation?.requestPermission === 'function'){
    try{
      const result = await Orientation.requestPermission()
      motionButton.textContent = result === 'granted' ? 'حرکت گوشی فعال است' : 'دسترسی حرکت داده نشد'
    }catch{
      motionButton.textContent = 'دسترسی حرکت داده نشد'
    }
  }else{
    motionButton.textContent = 'حرکت گوشی فعال است'
  }
})

document.addEventListener('visibilitychange',()=>{
  if(document.hidden){
    cancelAnimationFrame(raf)
  }else{
    raf = requestAnimationFrame(render)
  }
})

resize()
raf = requestAnimationFrame(render)
statusEl.textContent = 'WEBGL ACTIVE'