import os
from datetime import datetime, timedelta
from decimal import Decimal
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import boto3
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

SENDER = "lucas.blockv@gmail.com"
DESTINATARIOS = ["lucas.blockv@gmail.com", "anaapaulasodre@gmail.com"]
REGION = os.getenv("AWS_REGION", "us-east-2")
TABLE_NAME = os.getenv("DYNAMODB_TABLE")

def buscar_dados():
    dynamo = boto3.resource("dynamodb", region_name=REGION)
    table = dynamo.Table(TABLE_NAME)

    limite_tempo = (datetime.now() - timedelta(hours=2)).isoformat()

    response = table.scan(
        FilterExpression="updated_at >= :t",
        ExpressionAttributeValues={":t": limite_tempo},
    )

    items = response.get("Items", [])
    if not items:
        return None

    df = pd.DataFrame(items)
    
    if "id_imovel" in df.columns:
        df = df.drop_duplicates(subset=["id_imovel"])

    for col in df.columns:
        df[col] = df[col].apply(lambda x: float(x) if isinstance(x, Decimal) else x)

    return df

def enviar_email(df):
    msg = MIMEMultipart()
    msg["Subject"] = f"Relatorio: {len(df)} Novas Oportunidades de Imoveis"
    msg["From"] = SENDER
    msg["To"] = ", ".join(DESTINATARIOS)

    itens_html = ""
    for _, row in df.iterrows():
        try:
            preco_num = float(row.get('Preco', 0))
            preco = f"R$ {preco_num:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except:
            preco = "Nao informado"

        bairro = row.get('Bairro', 'Nao informado')
        link = row.get('Link', '#')
        imobiliaria = row.get('Imobiliaria', 'Nao informada')
        area = row.get('Area', '--')
        quartos = row.get('Quartos', '--')

        bloco_imovel = f"""
        <div style="border-bottom: 1px solid #eee; padding: 20px 0; font-family: sans-serif;">
            <h3 style="margin: 0 0 10px 0; color: #2c3e50; font-size: 18px;">Imovel em {bairro}</h3>
            <p style="margin: 5px 0; font-size: 16px;">
                <b style="color: #28a745;">{preco}</b>
            </p>
            <p style="margin: 5px 0; color: #555;">
                <b>Imobiliaria:</b> {imobiliaria}<br>
                <b>Area:</b> {area} m2 | <b>Quartos:</b> {quartos}
            </p>
            <div style="margin-top: 12px;">
                <a href="{link}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; font-weight: bold; display: inline-block; font-size: 14px;">
                    Ver Detalhes
                </a>
            </div>
        </div>"""
        itens_html += bloco_imovel

    corpo_html = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #444; background-color: #f9f9f9; padding: 20px;">
            <div style="max-width: 600px; margin: auto; background: white; padding: 20px; border-radius: 8px; border: 1px solid #ddd;">
                <h2 style="color: #2c3e50; border-bottom: 2px solid #007bff; padding-bottom: 10px;">Novos Imoveis em Curitiba</h2>
                <p>Foram encontradas <b>{len(df)}</b> novas oportunidades nas ultimas 2 horas:</p>
                {itens_html}
                <p style="font-size: 11px; color: #999; margin-top: 20px; text-align: center;">
                    Este e um aviso automatico gerado pelo sistema.
                </p>
            </div>
        </body>
    </html>
    """
    
    msg.attach(MIMEText(corpo_html, "html"))
    ses = boto3.client("ses", region_name=REGION)

    try:
        ses.send_raw_email(
            Source=SENDER,
            Destinations=DESTINATARIOS,
            RawMessage={"Data": msg.as_string()},
        )
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    df_imoveis = buscar_dados()
    if df_imoveis is not None and not df_imoveis.empty:
        enviar_email(df_imoveis)