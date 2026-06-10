export default function Footer() {
  return (
    <footer className="mt-12 border-t border-hair pt-6 pb-4 text-xs leading-relaxed text-gray-500">
      <p>
        Painel editorial <strong className="text-texto">não-oficial</strong>, sem
        vínculo com TSE, institutos de pesquisa ou campanhas. Os números de cada
        pesquisa pertencem aos respectivos institutos; o registro no TSE pode ser
        conferido em{" "}
        <a className="text-petrol underline hover:text-azuldark"
           href="https://pesqele-divulgacao.tse.jus.br/" target="_blank" rel="noreferrer">
          pesqele-divulgacao.tse.jus.br
        </a>
        . A média do modelo NÃO é uma pesquisa e não deve ser citada como tal.
      </p>
    </footer>
  );
}
