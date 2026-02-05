from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import pandas as pd
import time
import unicodedata

bairros_alvo = [
    "ahu", "alto da gloria", "alto da rua xv", "agua verde", "batel",
    "bigorrilho", "bom retiro", "cabral", "centro", "champagnat",
    "cristo rei", "hugo lange", "jardim social", "juveve",
    "merces", "mossungue", "portao", "boa vista"
]


def formatar_bairro(nome):
    texto = unicodedata.normalize('NFKD', nome).encode('ASCII', 'ignore').decode('ASCII')
    return texto.lower().strip().replace(' ', '-')

def limpar_texto(texto):
    return texto.replace('\n', '').strip() if texto else "N/A"

def raspar_com_navegador():
    lista_imoveis = []

    with sync_playwright() as p:
        # Abre o navegador (headless=False para você VER ele abrindo)
        # Depois que funcionar, pode mudar para headless=True para ficar invisível
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for bairro in bairros_alvo:
            slug = formatar_bairro(bairro)
            url = f"https://www.apolar.com.br/alugar/apartamento/curitiba/{slug}"

            print(f"--> Acessando: {bairro.upper()}")

            try:
                page.goto(url, timeout=60000) # 60 segundos de timeout

                # O PULO DO GATO 😺:
                # Espera até aparecer o primeiro card de imóvel na tela
                try:
                    page.wait_for_selector('.property-component', timeout=10000)
                except:
                    print(f"    Nenhum imóvel carregou no {bairro}.")
                    continue

                # Agora que o JS rodou, pegamos o HTML completo
                html_completo = page.content()
                soup = BeautifulSoup(html_completo, 'html.parser')

                # Daqui pra baixo é igual ao seu código anterior
                cards = soup.find_all(class_='property-component')

                for card in cards:
                    try:
                        tag_link = card.find('a', href=True)
                        link = tag_link['href'] if tag_link else "S/ Link"

                        # Pegando Preço
                        preco_tag = card.find(class_='property-current-price')
                        preco = limpar_texto(preco_tag.text).replace('R$', '').strip() if preco_tag else "0"

                        # Pegando Bairro (confirmação)
                        bairro_tag = card.find(class_='property-address-others')
                        bairro_nome = limpar_texto(bairro_tag.text) if bairro_tag else bairro

                        lista_imoveis.append({
                            'Bairro': bairro_nome,
                            'Preco': preco,
                            'Link': link
                        })
                    except Exception as e:
                        continue

                print(f"    Achamos {len(cards)} imóveis.")

            except Exception as e:
                print(f"Erro ao carregar {bairro}: {e}")

        browser.close()

    return lista_imoveis

# Executar
dados = raspar_com_navegador()
if dados:
    df = pd.DataFrame(dados)
    df.to_excel("imoveis_apolar_js.xlsx", index=False)
    print("\n✅ Arquivo salvo com sucesso!")
