import os
from datetime import datetime, timedelta
from decimal import Decimal
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import boto3
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

SENDER = os.getenv("EMAIL_SENDER")
RECIPIENT = os.getenv("EMAIL_RECIPIENT")
REGION = os.getenv("AWS_REGION", "us-east-1")


def buscar_dados():
    dynamo = boto3.resource("dynamodb", region_name=REGION)
    table = dynamo.Table(os.getenv("DYNAMODB_TABLE"))

    limite_tempo = (datetime.now() - timedelta(hours=8)).isoformat()

    print(f"🔎 Filtrando apenas imóveis que entraram no sistema após: {limite_tempo}")

    response = table.scan(
        FilterExpression="updated_at >= :t",
        ExpressionAttributeValues={":t": limite_tempo},
    )

    items = response.get("Items", [])
    if not items:
        return None

    df = pd.DataFrame(items)

    df = df.drop_duplicates(subset=["id_imovel"])

    for col in df.columns:
        df[col] = df[col].apply(lambda x: float(x) if isinstance(x, Decimal) else x)

    return df


def enviar_email(df):
    filename = f"relatorio_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    df.to_excel(filename, index=False)

    msg = MIMEMultipart()
    msg["Subject"] = f"🏠 Imóveis Curitiba - {datetime.now().strftime('%d/%m')}"
    msg["From"] = SENDER
    msg["To"] = RECIPIENT

    # Header importante para evitar filtros de spam de "lote"
    msg.add_header("X-Priority", "3")
    msg.add_header("Precedence", "bulk")  # Indica que é um envio automatizado legítimo

    # Melhore o corpo do e-mail (HTML é menos "spameável" que texto puro se bem feito)
    corpo = f"""
      <html>
      <body>
            <h3>Olá! Encontramos {len(df)} novos imóveis.</h3>
            <p>O relatório detalhado está em anexo no formato Excel.</p>
            <br>
            <small>Este é um alerta automático do seu Crawler de Imóveis.</small>
      </body>
      </html>
      """
    msg.attach(MIMEText(corpo, "html"))

    with open(filename, "rb") as f:
        part = MIMEApplication(f.read())
        part.add_header("Content-Disposition", "attachment", filename=filename)
        msg.attach(part)

    ses = boto3.client("ses", region_name=REGION)
    ses.send_raw_email(
        Source=SENDER, Destinations=[RECIPIENT], RawMessage={"Data": msg.as_string()}
    )
    print("✅ Relatório enviado!")
    os.remove(filename)


if __name__ == "__main__":
    df_imoveis = buscar_dados()
    if df_imoveis is not None:
        enviar_email(df_imoveis)
    else:
        print("Nenhum imóvel novo para reportar.")
