import { useMemo, useState } from "react";
import { pct, dataBr } from "../format";

const W = 920;
const H = 380;
const PAD = { l: 44, r: 130, t: 16, b: 28 };

/** Gráfico de tendência: linha = modelo, pontos = pesquisas individuais. */
export default function TrendChart({ race, cores }) {
  const [hover, setHover] = useState(null);

  const data = useMemo(() => prepare(race), [race]);
  if (!data) return null;
  const { t0, t1, yMax, series, dots } = data;

  const x = (t) => PAD.l + ((t - t0) / (t1 - t0 || 1)) * (W - PAD.l - PAD.r);
  const y = (v) => PAD.t + (1 - v / yMax) * (H - PAD.t - PAD.b);

  const yTicks = [];
  for (let v = 0; v <= yMax; v += 10) yTicks.push(v);

  const xTicks = monthTicks(t0, t1);

  return (
    <section className="rounded-2xl border border-hair bg-card shadow-card p-4 sm:p-6">
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="text-sm font-semibold uppercase tracking-widest text-gray-400">
          Tendência — linha é o modelo, pontos são pesquisas
        </h2>
      </div>
      <div className="mt-3 overflow-x-auto">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="min-w-[640px] w-full select-none"
          onMouseLeave={() => setHover(null)}
        >
          {yTicks.map((v) => (
            <g key={v}>
              <line x1={PAD.l} x2={W - PAD.r} y1={y(v)} y2={y(v)}
                    stroke={v ? "#E3E8EF" : "#cbd5e1"} strokeWidth="1"
                    strokeDasharray={v ? "2 4" : ""} />
              <text x={PAD.l - 8} y={y(v) + 4} textAnchor="end"
                    fill="#9ca3af" fontSize="11">{v}%</text>
            </g>
          ))}
          {xTicks.map(({ t, label }) => (
            <text key={t} x={x(t)} y={H - 8} textAnchor="middle"
                  fill="#9ca3af" fontSize="11">{label}</text>
          ))}

          {/* pontos: cada pesquisa individual */}
          {dots.map((d, i) => (
            <circle
              key={i}
              cx={x(d.t)} cy={y(d.v)} r={hover?.dot === i ? 4.5 : 3}
              fill={d.cor} opacity={hover?.dot === i ? 1 : 0.38}
              onMouseEnter={() => setHover({ dot: i })}
            />
          ))}

          {/* linhas do modelo */}
          {series.map((s) => (
            <path key={s.nome} d={s.path} fill="none" stroke={s.cor}
                  strokeWidth="2.5" strokeLinejoin="round" />
          ))}

          {/* rótulos à direita (com afastamento para não sobrepor) */}
          {dodgeLabels(series, y).map((s) => (
            <text key={s.nome} x={W - PAD.r + 8} y={s.labelY}
                  fontSize="12" fontWeight="700" fill={s.cor}>
              {s.nome} {pct(s.last)}
            </text>
          ))}

          {hover?.dot != null && <Tooltip d={dots[hover.dot]} x={x} y={y} />}
        </svg>
      </div>
      <p className="mt-2 text-xs text-gray-500">
        Cada ponto é uma pesquisa publicada (cenário estimulado). A linha é a
        média ponderada do modelo no dia — não é interpolação entre pesquisas.
      </p>
    </section>
  );
}

function Tooltip({ d, x, y }) {
  const tx = Math.min(x(d.t) + 10, W - PAD.r - 190);
  const ty = Math.max(y(d.v) - 48, 6);
  return (
    <g pointerEvents="none">
      <rect x={tx} y={ty} width="185" height="40" rx="6"
            fill="#ffffff" stroke="#cbd5e1" />
      <text x={tx + 8} y={ty + 16} fontSize="11" fill="#0F4C5C" fontWeight="700">
        {d.nome} — {pct(d.v)}
      </text>
      <text x={tx + 8} y={ty + 31} fontSize="10" fill="#6b7280">
        {d.instituto} · {dataBr(d.data)}
      </text>
    </g>
  );
}

function prepare(race) {
  const trend = race.trend || [];
  if (trend.length < 2) return null;
  // candidatos atuais (com média hoje) definem as linhas
  const nomes = (race.candidatos || []).map((c) => c.nome);
  const corDe = Object.fromEntries((race.candidatos || []).map((c) => [c.nome, c.cor]));

  const ts = (iso) => new Date(iso + "T12:00:00").getTime();
  const t0 = ts(trend[0].date);
  const t1 = ts(trend[trend.length - 1].date);

  let yMax = 0;

  const series = nomes.map((nome) => {
    const pts = trend
      .filter((p) => nome in p.values)
      .map((p) => [ts(p.date), p.values[nome]]);
    pts.forEach(([, v]) => (yMax = Math.max(yMax, v)));
    return { nome, cor: corDe[nome], pts, last: pts[pts.length - 1]?.[1] ?? 0 };
  });

  const dots = [];
  for (const p of race.pesquisas || []) {
    const t = ts(p.dataFim);
    if (t < t0) continue;
    for (const r of p.resultados) {
      if (!r.isCandidate || !nomes.includes(r.candidato)) continue;
      yMax = Math.max(yMax, r.pct);
      dots.push({
        t, v: r.pct, nome: r.candidato, cor: corDe[r.candidato],
        instituto: p.instituto, data: p.dataFim,
      });
    }
  }

  yMax = Math.ceil((yMax + 4) / 10) * 10;

  const x = (t) => PAD.l + ((t - t0) / (t1 - t0 || 1)) * (W - PAD.l - PAD.r);
  const y = (v) => PAD.t + (1 - v / yMax) * (H - PAD.t - PAD.b);
  for (const s of series) {
    s.path = s.pts
      .map(([t, v], i) => `${i ? "L" : "M"}${x(t).toFixed(1)},${y(v).toFixed(1)}`)
      .join("");
  }

  return { t0, t1, yMax, series, dots };
}

// Empurra rótulos para baixo quando colidem (mín. 14px entre linhas).
function dodgeLabels(series, y) {
  const MIN = 14;
  const sorted = [...series].sort((a, b) => b.last - a.last);
  let prev = -Infinity;
  for (const s of sorted) {
    let ly = y(s.last) + 4;
    if (ly < prev + MIN) ly = prev + MIN;
    s.labelY = ly;
    prev = ly;
  }
  return sorted;
}

function monthTicks(t0, t1) {
  const meses = ["jan", "fev", "mar", "abr", "mai", "jun",
                 "jul", "ago", "set", "out", "nov", "dez"];
  const out = [];
  const d = new Date(t0);
  d.setDate(1);
  d.setMonth(d.getMonth() + 1);
  while (d.getTime() <= t1) {
    out.push({
      t: d.getTime(),
      label: `${meses[d.getMonth()]}${d.getMonth() === 0 ? "/" + String(d.getFullYear()).slice(2) : ""}`,
    });
    d.setMonth(d.getMonth() + 1);
  }
  return out;
}
