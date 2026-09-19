import { useEffect, useRef, useState } from 'react'
import './LoginMaterialLab.css'

const vertexShader = `
attribute vec2 a_position;
varying vec2 v_uv;
void main() {
  v_uv = a_position * 0.5 + 0.5;
  gl_Position = vec4(a_position, 0.0, 1.0);
}
`

const fragmentShader = `
precision highp float;
varying vec2 v_uv;
uniform vec2 u_resolution;
uniform float u_time;
uniform vec2 u_tilt;

float hash(vec2 p) {
  p = fract(p * vec2(123.34, 456.21));
  p += dot(p, p + 45.32);
  return fract(p.x * p.y);
}
float noise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  float a = hash(i);
  float b = hash(i + vec2(1.0, 0.0));
  float c = hash(i + vec2(0.0, 1.0));
  float d = hash(i + vec2(1.0, 1.0));
  return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

float fbm(vec2 p) {
  float value = 0.0;
  float amp = 0.5;
  for (int i = 0; i < 5; i++) {
    value += amp * noise(p);
    p = mat2(1.62, 1.17, -1.17, 1.62) * p + 0.17;
    amp *= 0.5;
  }
  return value;
}

void main() {  vec2 p = v_uv - 0.5;
  p.x *= u_resolution.x / max(u_resolution.y, 1.0);
  float t = u_time * 0.055;
  vec2 drift = vec2(t * 0.42, -t * 0.31);
  vec2 tilt = u_tilt * 0.12;
  float n1 = fbm(p * 2.35 + drift + tilt);
  float n2 = fbm(p * 3.1 - drift * 1.4 + vec2(n1 * 0.75));
  vec2 warp = vec2(n1 - 0.5, n2 - 0.5) * 0.17;
  vec2 q = p + warp;
  float depth = fbm(q * 1.65 + vec2(-t, t * 0.7));
  float fine = fbm(q * 5.2 - vec2(t * 0.8, 0.0));
  float caustic = sin((q.x * 13.0 + n2 * 4.5) + t * 5.0);
  caustic += sin((q.y * 17.0 - n1 * 5.0) - t * 4.0);
  caustic = smoothstep(1.18, 1.86, caustic + fine * 0.48);
  vec3 navy = vec3(0.012, 0.045, 0.078);
  vec3 blue = vec3(0.055, 0.22, 0.33);
  vec3 gold = vec3(0.96, 0.63, 0.16);
  vec3 warm = vec3(1.0, 0.84, 0.46);
  vec3 color = mix(navy, blue, depth * 0.38);
  color += gold * caustic * 0.19;
  color += warm * pow(max(depth - 0.58, 0.0), 2.0) * 0.12;
  float vignette = smoothstep(0.78, 0.18, length(p * vec2(0.82, 1.1)));
  float alpha = (0.16 + depth * 0.13 + caustic * 0.08) * vignette;
  gl_FragColor = vec4(color, alpha);
}
`
function compileShader(gl: WebGLRenderingContext, type: number, source: string) {
  const shader = gl.createShader(type)
  if (!shader) throw new Error('Shader allocation failed')
  gl.shaderSource(shader, source)
  gl.compileShader(shader)
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    const message = gl.getShaderInfoLog(shader) || 'Shader compile failed'
    gl.deleteShader(shader)
    throw new Error(message)
  }
  return shader
}

function createProgram(gl: WebGLRenderingContext) {
  const program = gl.createProgram()
  if (!program) throw new Error('Program allocation failed')
  gl.attachShader(program, compileShader(gl, gl.VERTEX_SHADER, vertexShader))
  gl.attachShader(program, compileShader(gl, gl.FRAGMENT_SHADER, fragmentShader))
  gl.linkProgram(program)
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    throw new Error(gl.getProgramInfoLog(program) || 'Program link failed')
  }
  return program
}
export function LoginMaterialLab() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const [webglReady, setWebglReady] = useState(true)
  const [motionReady, setMotionReady] = useState(false)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const gl = canvas.getContext('webgl', { alpha: true, antialias: false, premultipliedAlpha: true })
    if (!gl) {
      setWebglReady(false)
      return
    }

    let program: WebGLProgram
    try {
      program = createProgram(gl)
    } catch {
      setWebglReady(false)
      return
    }

    const position = gl.getAttribLocation(program, 'a_position')
    const resolution = gl.getUniformLocation(program, 'u_resolution')
    const time = gl.getUniformLocation(program, 'u_time')
    const tiltUniform = gl.getUniformLocation(program, 'u_tilt')
    const buffer = gl.createBuffer()
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer)    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([
      -1, -1, 1, -1, -1, 1,
      -1, 1, 1, -1, 1, 1,
    ]), gl.STATIC_DRAW)
    gl.useProgram(program)
    gl.enableVertexAttribArray(position)
    gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0)

    const target = { x: 0, y: 0 }
    const current = { x: 0, y: 0 }
    let raf = 0
    let start = performance.now()

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 1.6)
      const rect = canvas.getBoundingClientRect()
      const width = Math.max(1, Math.round(rect.width * dpr))
      const height = Math.max(1, Math.round(rect.height * dpr))
      if (canvas.width !== width || canvas.height !== height) {
        canvas.width = width
        canvas.height = height
        gl.viewport(0, 0, width, height)
      }
    }

    const pointer = (event: PointerEvent) => {
      target.x = (event.clientX / window.innerWidth - 0.5) * 2
      target.y = (event.clientY / window.innerHeight - 0.5) * -2
    }
    const orientation = (event: DeviceOrientationEvent) => {
      if (event.gamma == null || event.beta == null) return
      target.x = Math.max(-1, Math.min(1, event.gamma / 28))
      target.y = Math.max(-1, Math.min(1, (event.beta - 45) / 38))
      setMotionReady(true)
    }

    const render = (now: number) => {
      resize()
      current.x += (target.x - current.x) * 0.035
      current.y += (target.y - current.y) * 0.035
      gl.useProgram(program)
      gl.uniform2f(resolution, canvas.width, canvas.height)
      gl.uniform1f(time, (now - start) / 1000)
      gl.uniform2f(tiltUniform, current.x, current.y)
      gl.drawArrays(gl.TRIANGLES, 0, 6)
      raf = requestAnimationFrame(render)
    }

    window.addEventListener('pointermove', pointer, { passive: true })
    window.addEventListener('deviceorientation', orientation, { passive: true })
    resize()
    raf = requestAnimationFrame(render)

    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('pointermove', pointer)
      window.removeEventListener('deviceorientation', orientation)
      gl.deleteBuffer(buffer)
      gl.deleteProgram(program)
    }
  }, [])
  const requestMotion = async () => {
    const Orientation = DeviceOrientationEvent as typeof DeviceOrientationEvent & {
      requestPermission?: () => Promise<'granted' | 'denied'>
    }
    if (typeof Orientation.requestPermission !== 'function') {
      setMotionReady(true)
      return
    }
    try {
      const result = await Orientation.requestPermission()
      setMotionReady(result === 'granted')
    } catch {
      setMotionReady(false)
    }
  }

  return (
    <main className="login-material-lab" dir="rtl">
      <canvas ref={canvasRef} className="login-material-canvas" aria-hidden="true" />
      <div className="login-material-veil" aria-hidden="true" />
      <section className="login-material-stage">
        <div className="login-material-meta">
          <span>NEGİN AI · MATERIAL LAB 01</span>
          <span>{webglReady ? 'WEBGL ACTIVE' : 'WEBGL FALLBACK'}</span>
        </div>

        <div className="login-material-hero">          <div className="login-material-logo-wrap">
            <img src="/assets/neginai-logo-transparent.png" alt="Negin AI" />
          </div>
          <div className="login-material-wordmark" dir="ltr">Negin <span>AI</span></div>
          <p>Fluid intelligence · refractive material study</p>
        </div>

        <div className="login-material-controls">
          <button type="button" onClick={requestMotion}>
            {motionReady ? 'حرکت گوشی فعال است' : 'فعال‌سازی واکنش به حرکت گوشی'}
          </button>
          <a href="/">بازگشت به Login واقعی</a>
        </div>
      </section>
    </main>
  )
}
