from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
import unicodedata
import random
import urllib.parse

def formatar_slug(texto):
    if not texto: return ""
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    return texto.lower().strip().replace(' ', '-')

def limpar_numero(texto):
    if not texto: return 0.0
    nums = ''.join([c for c in texto if c.isdigit()])
    if not nums: return 0.0
    return float(nums)

class ZapProvider:
    def __init__(self):
        self.base_url = "https://www.zapimoveis.com.br/aluguel"
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        
        # Mapeamento para garantir que o 'onde' vá com a acentuação correta que o Zap exige
        self.correcao_bairros = {
            "ahu": "Ahú",
            "alto da gloria": "Alto da Glória",
            "alto da rua xv": "Alto da Rua XV",
            "agua verde": "Água Verde",
            "batel": "Batel",
            "bigorrilho": "Bigorrilho",
            "bom retiro": "Bom Retiro",
            "cabral": "Cabral",
            "centro": "Centro",
            "champagnat": "Champagnat",
            "hugo lange": "Hugo Lange",
            "jardim social": "Jardim Social",
            "juveve": "Juvevê",
            "merces": "Mercês",
            "mossungue": "Mossunguê",
            "portao": "Portão"
        }

    def run(self, filtros):
        resultados = []
        cidade = "Curitiba"
        estado = "Paraná"
        hierarquia_estado = "Parana" # Sem acento na hierarquia da URL

        bairros_lista = filtros.get('bairros', [])
        preco_max = filtros.get('preco_max', 2500)
        area_min = filtros.get('area_min', 50)

        with sync_playwright() as p:
            print("--> [Zap] Iniciando navegador...")
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=self.user_agent, locale="pt-BR")
            page = context.new_page()

            for bairro_chave in bairros_lista:
                # 1. Tratamento dos nomes
                bairro_slug = formatar_slug(bairro_chave)
                bairro_formatado = self.correcao_bairros.get(bairro_chave.lower(), bairro_chave.title())

                # 2. Montagem da URL conforme seu padrão
                onde_str = f", {estado}, {cidade}, , {bairro_formatado}, , , neighborhood, BR>{hierarquia_estado}>NULL>{cidade}>Barrios>{bairro_formatado}, , "
                onde_param = urllib.parse.quote(onde_str)

                full_url = (
                    f"{self.base_url}/apartamentos/pr+curitiba++{bairro_slug}/2-quartos/?"
                    f"transacao=aluguel&"
                    f"onde={onde_param}&"
                    f"tipos=apartamento_residencial&"
                    f"quartos=2%2C3%2C4&"
                    f"precoMaximo={int(preco_max)}&"
                    f"areaMinima={int(area_min)}&"
                    f"origem=busca-recente"
                )

                print(f"--> [Zap] Buscando: {bairro_formatado}")

                try:
                    page.goto(full_url, wait_until="load", timeout=60000)
                    
                    # Espera as LIs da lista oficial (rp-property-cd)
                    try:
                        page.wait_for_selector('li[data-cy="rp-property-cd"]', timeout=15000)
                    except:
                        continue

                    # Scroll rápido para carregar as informações do card
                    page.evaluate("window.scrollBy(0, 600)")
                    time.sleep(1)

                    soup = BeautifulSoup(page.content(), 'html.parser')
                    # Pega apenas os itens da lista real, não os recomendados
                    itens_lista = soup.find_all('li', {'data-cy': 'rp-property-cd'})

                    for item in itens_lista:
                        try:
                            card_link = item.find('a', {'data-ds-component': 'DS-Surface'})
                            if not card_link: continue

                            link = card_link.get('href', '')
                            if not link.startswith('http'):
                                link = f"https://www.zapimoveis.com.br{link}"

                            # Preço
                            preco_tag = item.find('p', class_='olx-ad-card__price')
                            preco_val = limpar_numero(preco_tag.text) if preco_tag else 0

                            # Características usando os IDs do data-cy que você enviou no HTML
                            area_tag = item.find('li', {'data-cy': 'rp-cardProperty-propertyArea-txt'})
                            area_val = area_tag.get_text(strip=True) if area_tag else "-"

                            quartos_tag = item.find('li', {'data-cy': 'rp-cardProperty-bedroomQuantity-txt'})
                            quartos_val = limpar_numero(quartos_tag.get_text()) if quartos_tag else 0

                            resultados.append({
                                'Imobiliaria': 'Zap Imóveis',
                                'Bairro': bairro_formatado,
                                'Preco': preco_val,
                                'Quartos': int(quartos_val),
                                'Area': area_val,
                                'Link': link
                            })
                        except Exception:
                            continue

                    print(f"    Encontrados {len(itens_lista)} itens na lista.")

                except Exception as e:
                    print(f"    Erro no bairro {bairro_formatado}: {e}")

                # O Zap é agressivo no bloqueio, 3 a 5 segundos de respiro entre bairros é o ideal
                time.sleep(random.uniform(3, 5))

            browser.close()
        return resultados
