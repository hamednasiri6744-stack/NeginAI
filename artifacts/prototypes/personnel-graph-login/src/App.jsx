import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';

const GOLD = '216, 176, 94';
const DEPARTMENTS = [
  { id: 'management', label: 'مدیریت', lead: ['آرمان فرهمند', 'مدیر ارشد'], members: [['نیما راد', 'مدیر عملیات'], ['سارا نیک‌پی', 'دفتر مدیریت'], ['پرهام زمانی', 'برنامه‌ریزی'], ['الهام مرادی', 'کنترل داخلی']] },
  { id: 'sales', label: 'فروش', lead: ['کیان صادقی', 'مدیر فروش'], members: [['مهدی فلاح', 'سرپرست فروش'], ['نازنین کاظمی', 'کارشناس فروش'], ['امیررضا صالحی', 'ویزیتور'], ['روژان احمدی', 'ویزیتور'], ['بردیا شریفی', 'کارشناس مشتریان'], ['هلیا موسوی', 'تحلیل فروش']] },
  { id: 'logistics', label: 'لجستیک', lead: ['شاهین یوسفی', 'مدیر لجستیک'], members: [['حمید نادری', 'سرپرست ناوگان'], ['پویان اکبری', 'برنامه‌ریز مسیر'], ['مهسا رستمی', 'هماهنگ‌کننده'], ['فرزاد کریمی', 'کنترل توزیع'], ['ترانه بهرامی', 'عملیات ارسال']] },
  { id: 'warehouse', label: 'انبار', lead: ['سامان رحیمی', 'مدیر انبار'], members: [['سعید نظری', 'سرپرست انبار'], ['نگار جعفری', 'کنترل موجودی'], ['رضا ابراهیمی', 'تحویل کالا'], ['مونا حسینی', 'ثبت عملیات'], ['کاوه محمدی', 'کنترل چیدمان']] },
  { id: 'finance', label: 'مالی و خزانه', lead: ['پگاه شمس', 'مدیر مالی'], members: [['علی طاهری', 'حسابداری فروش'], ['بهاره ملکی', 'خزانه'], ['وحید حیدری', 'حسابداری خرید'], ['یلدا میرزایی', 'کنترل اسناد'], ['مانی رضوی', 'تحلیل مالی']] },
  { id: 'it', label: 'فناوری و داده', lead: ['رها امینی', 'مدیر فناوری'], members: [['نوید قاسمی', 'توسعه نرم‌افزار'], ['آوا کریمی', 'تحلیل داده'], ['اشکان مرادی', 'زیرساخت'], ['شادی رسولی', 'اتوماسیون'], ['ماهان رستگار', 'پشتیبانی سیستم']] },
  { id: 'procurement', label: 'خرید و تأمین', lead: ['امید کمالی', 'مدیر خرید'], members: [['سمیرا داودی', 'کارشناس خرید'], ['میلاد زارعی', 'تأمین‌کنندگان'], ['غزل فرجی', 'کنترل سفارش'], ['آرش بهمنی', 'برنامه‌ریزی خرید']] },
];

const getId = (value) => (typeof value === 'object' ? value.id : value);
const getInitials = (name) => name.split(' ').slice(0, 2).map((part) => part[0]).join('');

function buildGraph() {
  const nodes = [{ id: 'core', type: 'core', fx: 0, fy: 0, x: 0, y: 0 }];
  const links = [];
  const leaders = [];
  const total = DEPARTMENTS.length;

  DEPARTMENTS.forEach((department, departmentIndex) => {
    const angle = (departmentIndex / total) * Math.PI * 2 - Math.PI / 2;
    const leadId = `${department.id}-lead`;
    leaders.push(leadId);
    nodes.push({
      id: leadId,
      name: department.lead[0],
      role: department.lead[1],
      department: department.label,
      departmentId: department.id,
      leader: true,
      phase: departmentIndex * 0.8,
      x: Math.cos(angle) * 92,
      y: Math.sin(angle) * 92,
    });
    links.push({ source: 'core', target: leadId, kind: 'core' });

    department.members.forEach(([name, role], memberIndex) => {
      const memberAngle = angle + (memberIndex - (department.members.length - 1) / 2) * 0.16;
      const radius = 150 + (memberIndex % 2) * 18;
      const id = `${department.id}-${memberIndex}`;
      nodes.push({
        id,
        name,
        role,
        department: department.label,
        departmentId: department.id,
        leader: false,
        phase: departmentIndex + memberIndex * 0.43,
        x: Math.cos(memberAngle) * radius,
        y: Math.sin(memberAngle) * radius,
      });
      links.push({ source: leadId, target: id, kind: 'team' });
      if (memberIndex > 0) links.push({ source: `${department.id}-${memberIndex - 1}`, target: id, kind: 'team-soft' });
    });
  });

  leaders.forEach((leader, index) => {
    links.push({ source: leader, target: leaders[(index + 1) % leaders.length], kind: 'cross' });
  });
  links.push({ source: 'sales-1', target: 'finance-0', kind: 'cross' });
  links.push({ source: 'logistics-1', target: 'warehouse-1', kind: 'cross' });
  links.push({ source: 'it-1', target: 'management-2', kind: 'cross' });
  links.push({ source: 'procurement-2', target: 'warehouse-0', kind: 'cross' });

  return { nodes, links };
}

function useViewport() {
  const [viewport, setViewport] = useState(() => ({ width: window.innerWidth, height: window.innerHeight }));
  useEffect(() => {
    const update = () => setViewport({ width: window.innerWidth, height: window.innerHeight });
    window.addEventListener('resize', update, { passive: true });
    return () => window.removeEventListener('resize', update);
  }, []);
  return viewport;
}

export default function App() {
  const graphRef = useRef(null);
  const lastTapRef = useRef({ id: null, at: 0 });
  const initialFocusDone = useRef(false);
  const viewport = useViewport();
  const graphData = useMemo(buildGraph, []);
  const [selectedId, setSelectedId] = useState(null);
  const [hoveredId, setHoveredId] = useState(null);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [showParticles, setShowParticles] = useState(true);
  const [showLabels, setShowLabels] = useState(true);
  const [motionEnabled, setMotionEnabled] = useState(true);
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const sync = () => {
      setReducedMotion(media.matches);
      if (media.matches) setMotionEnabled(false);
    };
    sync();
    media.addEventListener?.('change', sync);
    return () => media.removeEventListener?.('change', sync);
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const fg = graphRef.current;
      if (!fg) return;
      fg.d3Force('charge')?.strength(-62);
      fg.d3Force('link')?.distance((link) => link.kind === 'core' ? 72 : link.kind === 'cross' ? 92 : 48);
      fg.d3ReheatSimulation?.();
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  const activeId = selectedId || hoveredId;
  const connectedIds = useMemo(() => {
    if (!activeId) return new Set();
    const connected = new Set([activeId]);
    graphData.links.forEach((link) => {
      const source = getId(link.source);
      const target = getId(link.target);
      if (source === activeId) connected.add(target);
      if (target === activeId) connected.add(source);
    });
    return connected;
  }, [activeId, graphData.links]);

  const selectedNode = useMemo(
    () => graphData.nodes.find((node) => node.id === selectedId) || null,
    [graphData.nodes, selectedId],
  );

  const resetView = useCallback(() => {
    setSelectedId(null);
    setHoveredId(null);
    graphRef.current?.centerAt(0, 0, 650);
    graphRef.current?.zoom(viewport.width < 600 ? 0.92 : 1.22, 650);
  }, [viewport.width]);

  const focusNode = useCallback((node) => {
    if (!node || node.type === 'core') {
      resetView();
      return;
    }
    const now = performance.now();
    const isDoubleTap = lastTapRef.current.id === node.id && now - lastTapRef.current.at < 340;
    lastTapRef.current = { id: node.id, at: now };
    setSelectedId(node.id);
    if (isDoubleTap) {
      graphRef.current?.centerAt(node.x, node.y, 650);
      graphRef.current?.zoom(2.7, 650);
    }
  }, [resetView]);

  const drawNode = useCallback((node, ctx, globalScale) => {
    const focused = activeId === node.id;
    const related = !activeId || connectedIds.has(node.id);
    const alpha = activeId && !related ? 0.16 : focused ? 1 : 0.82;
    const now = performance.now() / 1000;

    if (node.type === 'core') {
      const pulse = motionEnabled && !reducedMotion ? Math.sin(now * 1.3) * 1.2 : 0;
      const radius = 15 + pulse;
      ctx.save();
      ctx.globalAlpha = 0.98;
      ctx.shadowColor = `rgba(${GOLD}, .7)`;
      ctx.shadowBlur = 26;
      const coreGradient = ctx.createRadialGradient(0, 0, 2, 0, 0, radius * 1.3);
      coreGradient.addColorStop(0, 'rgba(255,255,255,.16)');
      coreGradient.addColorStop(.42, 'rgba(24,22,18,.95)');
      coreGradient.addColorStop(1, `rgba(${GOLD}, .22)`);
      ctx.fillStyle = coreGradient;
      ctx.beginPath();
      ctx.arc(0, 0, radius, 0, Math.PI * 2);
      ctx.fill();
      ctx.shadowBlur = 0;
      [radius + 5, radius + 10].forEach((ring, index) => {
        ctx.strokeStyle = `rgba(${GOLD}, ${index === 0 ? .46 : .18})`;
        ctx.lineWidth = index === 0 ? 1.15 : .55;
        ctx.beginPath();
        ctx.arc(0, 0, ring + pulse * .35, 0, Math.PI * 2);
        ctx.stroke();
      });
      ctx.restore();
      return;
    }

    const pulse = motionEnabled && !reducedMotion ? Math.sin(now * 1.2 + node.phase) * 0.28 : 0;
    const baseRadius = node.leader ? 6.8 : 5.15;
    const radius = (focused ? baseRadius * 1.72 : baseRadius) + pulse;
    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.shadowColor = `rgba(${GOLD}, ${focused ? .9 : node.leader ? .46 : .24})`;
    ctx.shadowBlur = focused ? 22 : node.leader ? 12 : 6;
    const gradient = ctx.createRadialGradient(node.x - radius * .28, node.y - radius * .36, .8, node.x, node.y, radius);
    gradient.addColorStop(0, 'rgba(255,255,255,.54)');
    gradient.addColorStop(.18, 'rgba(255,255,255,.18)');
    gradient.addColorStop(.56, 'rgba(22,22,20,.88)');
    gradient.addColorStop(1, `rgba(${GOLD}, .18)`);
    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(node.x, node.y, radius, 0, Math.PI * 2);
    ctx.fill();
    ctx.shadowBlur = 0;
    ctx.strokeStyle = `rgba(${GOLD}, ${focused ? .94 : node.leader ? .58 : .34})`;
    ctx.lineWidth = focused ? 1.25 : .7;
    ctx.stroke();

    if (node.leader) {
      ctx.strokeStyle = `rgba(${GOLD}, ${focused ? .72 : .27})`;
      ctx.lineWidth = .55;
      ctx.beginPath();
      ctx.arc(node.x, node.y, radius + 2.4, 0, Math.PI * 2);
      ctx.stroke();
    }

    ctx.fillStyle = focused ? '#fff5d8' : 'rgba(255,247,229,.8)';
    ctx.font = `${Math.max(2.8, 4.1 / Math.sqrt(globalScale))}px system-ui, sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(getInitials(node.name), node.x, node.y + .2);

    const showPersonLabel = showLabels && (globalScale > 1.45 || focused);
    const showDepartmentLabel = showLabels && node.leader && globalScale < 1.32;
    if (showPersonLabel || showDepartmentLabel) {
      const text = showPersonLabel ? node.name : node.department;
      const fontSize = showPersonLabel ? 3.4 : 4.2;
      ctx.font = `500 ${fontSize}px system-ui, sans-serif`;
      ctx.fillStyle = `rgba(255,247,229,${focused ? .96 : .72})`;
      ctx.fillText(text, node.x, node.y + radius + (showPersonLabel ? 5.1 : 6));
    }
    ctx.restore();
  }, [activeId, connectedIds, motionEnabled, reducedMotion, showLabels]);

  const paintPointerArea = useCallback((node, color, ctx) => {
    const radius = node.type === 'core' ? 22 : node.leader ? 10 : 8;
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(node.x, node.y, radius, 0, Math.PI * 2);
    ctx.fill();
  }, []);

  const linkIsActive = useCallback((link) => {
    if (!activeId) return false;
    const source = getId(link.source);
    const target = getId(link.target);
    return source === activeId || target === activeId;
  }, [activeId]);

  return (
    <main className="graph-shell">
      <div className="ambient ambient-one" />
      <div className="ambient ambient-two" />
      <section className="graph-stage" aria-label="نمونه تعاملی شبکه سازمانی نگین پخش">
        <ForceGraph2D
          ref={graphRef}
          width={viewport.width}
          height={viewport.height}
          graphData={graphData}
          backgroundColor="rgba(0,0,0,0)"
          nodeCanvasObject={drawNode}
          nodePointerAreaPaint={paintPointerArea}
          nodeLabel={() => ''}
          linkColor={(link) => linkIsActive(link) ? `rgba(${GOLD}, .86)` : activeId ? `rgba(${GOLD}, .075)` : `rgba(${GOLD}, ${link.kind === 'core' ? .34 : link.kind === 'cross' ? .18 : .13})`}
          linkWidth={(link) => linkIsActive(link) ? 1.45 : link.kind === 'core' ? .75 : .42}
          linkCurvature={(link) => link.kind === 'cross' ? .14 : link.kind === 'team-soft' ? .05 : .025}
          linkDirectionalParticles={showParticles && motionEnabled && !reducedMotion ? (link) => linkIsActive(link) ? 3 : link.kind === 'core' || link.kind === 'cross' ? 1 : 0 : 0}
          linkDirectionalParticleColor={() => `rgba(${GOLD}, .92)`}
          linkDirectionalParticleWidth={(link) => linkIsActive(link) ? 2.1 : .8}
          linkDirectionalParticleSpeed={(link) => linkIsActive(link) ? .006 : .0026}
          d3AlphaDecay={0.026}
          d3VelocityDecay={0.33}
          warmupTicks={70}
          cooldownTicks={220}
          minZoom={0.45}
          maxZoom={6}
          enableNodeDrag
          enablePanInteraction
          enableZoomInteraction
          onNodeClick={focusNode}
          onNodeHover={(node) => setHoveredId(node?.id || null)}
          onBackgroundClick={() => setSelectedId(null)}
          onZoom={(transform) => setZoomLevel(transform.k)}
          onEngineStop={() => {
            if (!initialFocusDone.current) {
              initialFocusDone.current = true;
              resetView();
            }
          }}
        />
      </section>

      <div className="prototype-title" aria-hidden="true">
        <span>ORGANIZATION FIELD</span>
        <small>interactive prototype · v01</small>
      </div>

      <aside className="control-dock" aria-label="تنظیمات نمونه">
        <button type="button" className={showParticles ? 'is-on' : ''} onClick={() => setShowParticles((value) => !value)}>Flow</button>
        <button type="button" className={showLabels ? 'is-on' : ''} onClick={() => setShowLabels((value) => !value)}>Labels</button>
        <button type="button" className={motionEnabled ? 'is-on' : ''} onClick={() => setMotionEnabled((value) => !value)} disabled={reducedMotion}>Motion</button>
        <button type="button" onClick={resetView}>Reset</button>
      </aside>

      <div className="zoom-meter" aria-hidden="true">
        <span style={{ width: `${Math.min(100, Math.max(8, zoomLevel * 28))}%` }} />
      </div>

      {selectedNode && selectedNode.type !== 'core' && (
        <aside className="person-card" aria-live="polite">
          <div className="person-orb">{getInitials(selectedNode.name)}</div>
          <div>
            <p>{selectedNode.department}</p>
            <h2>{selectedNode.name}</h2>
            <span>{selectedNode.role}</span>
          </div>
          <button type="button" aria-label="بستن" onClick={() => setSelectedId(null)}>×</button>
        </aside>
      )}

      <div className="gesture-hint" aria-hidden="true">Drag · Pinch · Zoom · Tap · Double Tap</div>
      <ul className="sr-only" aria-label="فهرست پرسنل آزمایشی">
        {graphData.nodes.filter((node) => node.type !== 'core').map((node) => (
          <li key={node.id}>{node.name}، {node.role}، {node.department}</li>
        ))}
      </ul>
    </main>
  );
}
