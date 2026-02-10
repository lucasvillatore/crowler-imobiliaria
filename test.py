import os

import boto3
from dotenv import load_dotenv

load_dotenv()


def testar_conexao():
    try:
        dynamo = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION"))
        table = dynamo.Table(os.getenv("DYNAMODB_TABLE"))

        print(f"--- Testando Tabela: {table.table_name} ---")
        # Tenta ler o status da tabela
        status = table.table_status
        print(f"✅ Conexão OK! Status da tabela: {status}")

    except Exception as e:
        print(f"❌ Falha crítica: {e}")


if __name__ == "__main__":
    testar_conexao()
