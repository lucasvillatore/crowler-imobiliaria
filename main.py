import pandas as pd

from providers.apolar import ApolarProvider
from providers.galvao import GalvaoProvider

MEUS_FILTROS = {
    "cidade": "curitiba",
    "tipo": "apartamento",
    "bairros": [
        "ahu",
        "alto da gloria",
        "alto da rua xv",
        "agua verde",
        "batel",
        "bigorrilho",
        "bom retiro",
        "cabral",
        "centro",
        "champagnat",
        "hugo lange",
        "jardim social",
        "juveve",
        "merces",
        "mossungue",
        "portao",
    ],
    "preco_max": 2500.00,
    "area_min": 60,
    "quartos_min": 2,
    "preco_condominio_incluso": True,
}


def main():
    todos_imoveis = []
    providers = [ApolarProvider(), GalvaoProvider()]

    print("=== BUSCADOR DE IMÓVEIS OTIMIZADO ===")

    for provider in providers:
        try:
            imoveis = provider.run(MEUS_FILTROS)
            todos_imoveis.extend(imoveis)
        except Exception as e:
            print(f"Erro: {e}")

    if todos_imoveis:
        df = pd.DataFrame(todos_imoveis)
        df = df.sort_values(by="Preco")

        df.to_excel("imoveis_filtrados.xlsx", index=False)
        print(f"\n✅ Relatório gerado com {len(todos_imoveis)} imóveis!")
        print(df[["Bairro", "Preco", "Area", "Link"]].head())
    else:
        print("\nNenhum imóvel encontrado. Tente aumentar o preço ou diminuir a área.")


if __name__ == "__main__":
    main()
