import os
from datetime import datetime
from decimal import Decimal

import boto3
from dotenv import load_dotenv

from providers.apolar import ApolarProvider
from providers.galvao import GalvaoProvider
from providers.zap_imoveis import ZapProvider
load_dotenv()

TABLE_NAME = os.getenv("DYNAMODB_TABLE")
dynamodb = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "us-east-2"))
table = dynamodb.Table(TABLE_NAME)

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


def salvar_no_dynamo(imoveis):
    print(f"\n--> [DynamoDB] Processando {len(imoveis)} imóveis...")
    novos_inseridos = 0

    for imovel in imoveis:
        try:
            item = {
                "id_imovel": imovel["Link"],
                "data_scraped": '2026-02-11', # sort key mocada para não duplicar os dados. Não quero recriar a tabela então vai servir só como id_imovel como unico
                "Imobiliaria": imovel["Imobiliaria"],
                "Bairro": imovel["Bairro"],
                "Preco": Decimal(str(imovel["Preco"])),
                "Area": str(imovel["Area"]),
                "Quartos": int(imovel["Quartos"]),
                "Link": imovel["Link"],
                "updated_at": datetime.now().isoformat(),
            }

            table.put_item(
                Item=item, ConditionExpression="attribute_not_exists(id_imovel)"
            )
            novos_inseridos += 1

        except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
            continue
        except Exception as e:
            print(f"❌ Erro ao processar imóvel {imovel.get('Link')}: {e}")

    print(f"📊 Resultado: {novos_inseridos} novos imóveis salvos.")


def main():
    todos_imoveis = []
    providers = [
        # ApolarProvider(), 
        # GalvaoProvider(),
        ZapProvider()
    ]

    print("=== BUSCADOR DE IMÓVEIS OTIMIZADO ===")

    for provider in providers:
        try:
            imoveis = provider.run(MEUS_FILTROS)
            todos_imoveis.extend(imoveis)
        except Exception as e:
            print(f"Erro no provider: {e}")

    if todos_imoveis:
        salvar_no_dynamo(todos_imoveis)

        # df = pd.DataFrame(todos_imoveis)
        # df = df.sort_values(by="Preco")
        # df.to_excel("imoveis_filtrados.xlsx", index=False)

        print(
            f"\n✅ Script finalizado. Total de {len(todos_imoveis)} imóveis encontrados."
        )
    else:
        print("\nNenhum imóvel encontrado.")


if __name__ == "__main__":
    main()
