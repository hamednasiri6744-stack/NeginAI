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

void main(){
  vec2 p = v_uv - 0.5;
  p.x *= u_resolution.x / max(u_resolution.y,1.0);
  float t = u_time * 0.052;
  vec2 drift = vec2(t*.42,-t*.29);
  vec2 tilt = u_tilt * .13;  float n1 = fbm(p*2.25 + drift + tilt);
  float n2 = fbm(p*3.05 - drift*1.35 + vec2(n1*.72));
  vec2 warp = vec2(n1-.5,n2-.5) * .18;
  vec2 q = p + warp;
  float depth = fbm(q*1.62 + vec2(-t,t*.68));
  float fine = fbm(q*5.1 - vec2(t*.8,0.0));

  float c1 = sin(q.x*13.0 + n2*4.4 + t*5.0);
  float c2 = sin(q.y*17.0 - n1*5.0 - t*4.0);
  float c3 = sin((q.x+q.y)*10.0 + fine*3.2 + t*2.7);
  float caustic = smoothstep(1.7,2.35,c1+c2+c3+fine*.5);

  vec3 navy = vec3(.010,.036,.064);
  vec3 blue = vec3(.042,.185,.285);
  vec3 gold = vec3(.95,.58,.12);
  vec3 warm = vec3(1.0,.82,.43);

  vec3 color = mix(navy,blue,depth*.42);
  color += gold * caustic * .20;
  color += warm * pow(max(depth-.62,0.0),2.0) * .14;

  float radius = length(p*vec2(.78,1.06));
  float vignette = 1.0 - smoothstep(.22,.82,radius);
  float alpha = (.12 + depth*.12 + caustic*.095) * vignette;
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