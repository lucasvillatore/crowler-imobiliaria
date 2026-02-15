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
    nums = ''.join([c for c in texto if c.isdigit() or c == ','])
    if not nums: return 0.0
    return float(nums.replace(',', '.'))

class ZapProvider:
    def __init__(self):
        self.base_url = "https://www.zapimoveis.com.br/aluguel"
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

    def run(self, filtros):
        resultados = []
        
        cidade = "Curitiba"
        estado = "Paraná"
        bairros = filtros.get('bairros', [])
        preco_max = filtros.get('preco_max', 0)
        area_min = filtros.get('area_min', 0)
        quartos_min = filtros.get('quartos_min', 2)

        with sync_playwright() as p:
            print("--> [Zap Imóveis] Iniciando navegador...")
            browser = p.chromium.launch(headless=True)
            # O Zap é sensível ao contexto, então definimos o User-Agent aqui
            context = browser.new_context(user_agent=self.user_agent)
            page = context.new_page()

            for bairro in bairros:
                slug_bairro = formatar_slug(bairro)
                # Nome do bairro com a primeira letra maiúscula para a string 'onde'
                bairro_formatado = bairro.title()

                # Montando a string 'onde' exatamente como você enviou
                # Nota: Deixamos as coordenadas vazias no final (,,) conforme sua observação
                onde_raw = f", {estado}, {cidade}, , {bairro_formatado}, , , neighborhood, BR>{estado}>NULL>{cidade}>Barrios>{bairro_formatado}, , "
                
                # Encoda a string (Transforma vírgulas em %2C, etc)
                onde_param = urllib.parse.quote(onde_raw)

                # Montagem da URL final com os query params solicitados
                full_url = (
                    f"{self.base_url}/apartamentos/pr+curitiba++{slug_bairro}/{quartos_min}-quartos/?"
                    f"transacao=aluguel&"
                    f"onde={onde_param}&"
                    f"tipos=apartamento_residencial&"
                    f"quartos=2%2C3%2C4&" # Mantendo o padrão de múltiplos quartos que você enviou
                    f"precoMaximo={int(preco_max)}&"
                    f"areaMinima={int(area_min)}&"
                    f"origem=busca-recente"
                )

                print(f"--> [Zap] Buscando bairro: {bairro.upper()}")

                try:
                    # Navigation
                    page.goto(full_url, wait_until="domcontentloaded", timeout=60000)
                    
                    # Espera o seletor do link (card) que você forneceu
                    try:
                        page.wait_for_selector('a.olx-core-surface', timeout=12000)
                    except:
                        print(f"    (Sem resultados ou timeout para {bairro})")
                        continue

                    soup = BeautifulSoup(page.content(), 'html.parser')
                    # Busca pelos links que possuem a classe do card
                    cards = soup.find_all('a', class_='olx-core-surface')

                    validos = 0
                    for card in cards:
                        try:
                            # Link do imóvel
                            link = card.get('href', '')
                            if not link.startswith('http'):
                                link = f"https://www.zapimoveis.com.br{link}"

                            # Preço - O Zap usa a classe olx-ad-card__price dentro desse surface
                            preco_tag = card.find('p', class_='olx-ad-card__price')
                            preco_val = limpar_numero(preco_tag.text) if preco_tag else 0

                            # Área e Quartos - Geralmente em spans de características
                            # Vamos extrair do title do card que você enviou, que é bem completo
                            info_title = card.get('title', '')
                            
                            # Fallback para pegar a área do texto do card se o title falhar
                            area_txt = "-"
                            if "m²" in info_title:
                                # Pega o valor que vem antes de "m²"
                                area_txt = info_title.split("m²")[0].split()[-1] + " m²"
                            
                            quartos_val = quartos_min
                            if "quartos" in info_title:
                                # Tenta extrair o número de quartos do title
                                try:
                                    quartos_val = int(info_title.split("quartos")[0].split()[-1])
                                except: pass

                            resultados.append({
                                'Imobiliaria': 'Zap Imóveis',
                                'Bairro': bairro_formatado,
                                'Preco': preco_val,
                                'Quartos': quartos_val,
                                'Area': area_txt,
                                'Link': link
                            })
                            validos += 1

                        except Exception:
                            continue

                    print(f"    Cards na página: {len(cards)} | Processados: {validos}")

                except Exception as e:
                    print(f"    Erro ao processar {bairro}: {e}")

                # Sleep aleatório para não ser bloqueado rápido
                time.sleep(random.uniform(2, 4))

            browser.close()

        return resultados
