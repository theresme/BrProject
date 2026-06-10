// Formatação pt-BR para números e percentuais.
const nf = new Intl.NumberFormat("pt-BR");

export const int = (n) => nf.format(Math.round(n ?? 0));

export const pct = (n, dec = 1) =>
  `${(n ?? 0).toLocaleString("pt-BR", {
    minimumFractionDigits: dec,
    maximumFractionDigits: dec,
  })}%`;

export const dataBr = (iso) => {
  if (!iso) return "—";
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y.slice(2)}`;
};

export const periodo = (ini, fim) => {
  if (!ini) return dataBr(fim);
  if (ini === fim) return dataBr(fim);
  return `${dataBr(ini)}–${dataBr(fim)}`;
};
