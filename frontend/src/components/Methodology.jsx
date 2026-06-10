/** Como o modelo funciona, em linguagem de gente. */
export default function Methodology({ params, race }) {
  return (
    <section className="rounded-2xl border border-hair bg-panel/60 p-4 sm:p-6">
      <h2 className="text-sm font-semibold uppercase tracking-widest text-gray-400">
        Como o modelo funciona
      </h2>
      <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm leading-relaxed text-gray-400">
        <li>
          Cada pesquisa entra com peso ={" "}
          <span className="text-gray-200">recência</span> ×{" "}
          <span className="text-gray-200">rating do instituto</span> ×{" "}
          <span className="text-gray-200">amostra</span> ×{" "}
          <span className="text-gray-200">registro no TSE</span>. A recência
          decai pela metade a cada {params?.meiaVidaDias ?? 14} dias.
        </li>
        <li>
          O <span className="text-gray-200">house effect</span> de cada
          instituto (tendência sistemática a favor/contra um candidato) é
          estimado contra a média dos demais e corrigido em{" "}
          {Math.round((params?.houseEffectShrink ?? 0.5) * 100)}%.
        </li>
        <li>
          A <span className="text-gray-200">banda</span> combina a dispersão
          entre institutos, o erro amostral declarado e um termo estrutural —
          pesquisas erram mais do que a margem formal sugere.
        </li>
        <li>
          A <span className="text-gray-200">chance de liderar hoje</span> sai
          de 20&nbsp;mil simulações sobre essas bandas. É "quem estaria na
          frente se a média do modelo estiver certa", <em>não</em> uma
          previsão do resultado da eleição.
        </li>
      </ol>
      <p className="mt-3 text-xs text-gray-500">
        Resultados: tabelas públicas da Wikipédia (cada linha cita a fonte
        primária). Registro: CSV oficial de dados abertos do TSE (PesqEle).
        Código e parâmetros abertos — confira, discorde, ajuste.
      </p>
    </section>
  );
}
