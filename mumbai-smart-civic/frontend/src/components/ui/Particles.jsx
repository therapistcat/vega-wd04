import { useRef, useEffect } from "react";
import { Renderer, Camera, Geometry, Program, Mesh, Vec3, Color, Polyline } from "ogl";

export default function Particles({
  particleColors = ["#ffffff"],
  particleCount = 200,
  speed = 0.1,
  particleBaseSize = 100,
  moveParticlesOnHover = true,
}) {
  const containerRef = useRef(null);
  const mouseRef = useRef(new Vec3());

  useEffect(() => {
    if (!containerRef.current) return;

    const renderer = new Renderer({ alpha: true, antialias: true, dpr: window.devicePixelRatio });
    const gl = renderer.gl;
    containerRef.current.appendChild(gl.canvas);

    const camera = new Camera(gl, { fov: 35 });
    camera.position.z = 15;

    function resize() {
      renderer.setSize(window.innerWidth, window.innerHeight);
      camera.perspective({ aspect: gl.canvas.width / gl.canvas.height });
    }
    window.addEventListener("resize", resize, false);
    resize();

    // Setup Geometry and Program for particles
    const geometry = new Geometry(gl, {
      position: { size: 3, data: new Float32Array(particleCount * 3) },
      random: { size: 1, data: new Float32Array(particleCount) },
    });

    const positions = geometry.attributes.position.data;
    const randoms = geometry.attributes.random.data;

    for (let i = 0; i < particleCount; i++) {
        const x = (Math.random() - 0.5) * 20;
        const y = (Math.random() - 0.5) * 20;
        const z = (Math.random() - 0.5) * 10;
        positions.set([x, y, z], i * 3);
        randoms[i] = Math.random();
    }
    geometry.attributes.position.needsUpdate = true;

    const vertex = `
      attribute vec3 position;
      attribute float random;
      uniform mat4 modelViewMatrix;
      uniform mat4 projectionMatrix;
      uniform float uTime;
      uniform float uSize;

      void main() {
        vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
        gl_Position = projectionMatrix * mvPosition;
        gl_PointSize = uSize * (10.0 / -mvPosition.z);
      }
    `;

    const fragment = `
      precision highp float;
      uniform vec3 uColor;

      void main() {
        float d = distance(gl_PointCoord, vec2(0.5));
        if (d > 0.5) discard;
        /* Soft bokeh sphere edge, steady alpha - no fade-out */
        float alpha = 0.85 * (1.0 - smoothstep(0.3, 0.5, d));
        gl_FragColor = vec4(uColor, alpha);
      }
    `;

    const program = new Program(gl, {
      vertex,
      fragment,
      uniforms: {
        uColor: { value: new Color(particleColors[0]) },
        uSize: { value: particleBaseSize / 10 },
      },
      transparent: true,
      depthTest: false,
    });

    // Update uniform if color changes
    program.uniforms.uColor.value.set(particleColors[0]);

    const particles = new Mesh(gl, { mode: gl.POINTS, geometry, program });

    function update(time) {
      if (moveParticlesOnHover) {
          particles.rotation.y += (mouseRef.current.x * 0.05 - particles.rotation.y) * 0.05;
          particles.rotation.x += (mouseRef.current.y * 0.05 - particles.rotation.x) * 0.05;
      }
      renderer.render({ scene: particles, camera });
      requestAnimationFrame(update);
    }
    requestAnimationFrame(update);

    const handleMouseMove = (e) => {
      mouseRef.current.set(
        (e.clientX / window.innerWidth) * 2 - 1,
        -(e.clientY / window.innerHeight) * 2 + 1,
        0
      );
    };
    window.addEventListener("mousemove", handleMouseMove);

    return () => {
      window.removeEventListener("resize", resize);
      window.removeEventListener("mousemove", handleMouseMove);
      if (containerRef.current) {
          containerRef.current.removeChild(gl.canvas);
      }
    };
  }, [particleColors, particleCount, speed, particleBaseSize, moveParticlesOnHover]);

  return (
    <div
      ref={containerRef}
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        width: "100vw",
        height: "100vh",
        zIndex: 0,
        pointerEvents: "none",
      }}
    />
  );
}
