export default function Disclaimer() {
  return (
    <div className="mt-5 rounded-xl border border-amarelo/30 bg-amarelo/10 px-4 py-3 text-sm leading-relaxed text-yellow-100/90">
      <span className="font-bold text-amarelo">Isto NÃO é uma pesquisa.</span>{" "}
      É um <span className="font-semibold">modelo</span>: uma média ponderada de
      pesquisas feitas por institutos diferentes, com metodologias e datas
      diferentes. O número de cada instituto está na tabela abaixo, com o
      respectivo nº de registro no TSE. Pesquisa eleitoral é retrato do
      momento; modelo é leitura editorial desses retratos — e ambos erram.
    </div>
  );
}
