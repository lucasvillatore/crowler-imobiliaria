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
        
        cidade = filtros.get('cidade', 'curitiba')
        estado = "pr"
        tipo = filtros.get('tipo', 'apartamentos')
        if not tipo.endswith('s'): tipo += 's' 
        
        bairros = filtros.get('bairros', [])
        preco_max = filtros.get('preco_max', 0)
        area_min = filtros.get('area_min', 0)
        quartos_min = filtros.get('quartos_min', 0)

        with sync_playwright() as p:
            print("--> [Zap Imóveis] Iniciando navegador...")
            browser = p.chromium.launch(headless=True) 
            
            context = browser.new_context(user_agent=self.user_agent, viewport={'width': 1280, 'height': 800})
            page = context.new_page()

            for bairro in bairros:
                slug_bairro = formatar_slug(bairro)
                
                url_path = f"{self.base_url}/{tipo}/{estado}+{cidade}++{slug_bairro}"
                if quartos_min > 0:
                    url_path += f"/{quartos_min}-quartos"
                
                # Parâmetros de Query String
                params = {
                    'transacao': 'aluguel',
                    'tipoUnidade': 'Residencial',
                    'tipos': 'apartamento_residencial'
                }
                
                if preco_max > 0: params['precoMaximo'] = int(preco_max)
                if area_min > 0: params['areaMinima'] = int(area_min)
                
                full_url = f"{url_path}/?{urllib.parse.urlencode(params)}"

                print(f"--> [Zap Imóveis] Buscando em {bairro.upper()}")

                try:
                    page.goto(full_url, wait_until="domcontentloaded", timeout=60000)
                    
                    page.mouse.wheel(0, 1000)
                    time.sleep(2)

                    try:
                        page.wait_for_selector('a[data-ds-component="DS-Surface"]', timeout=10000)
                    except:
                        print(f"    (Sem resultados para {bairro})")
                        continue

                    soup = BeautifulSoup(page.content(), 'html.parser')
                    cards = soup.find_all('a', {'data-ds-component': 'DS-Surface'})

                    validos = 0
                    for card in cards:
                        try:
                            link = card.get('href', '')
                            if not link.startswith('http'):
                                link = f"https://www.zapimoveis.com.br{link}"

                            info_texto = card.get('title', '') or card.get('aria-label', '')
                            
                            preco_tag = card.find(string=lambda t: 'R$' in str(t))
                            preco_val = limpar_numero(preco_tag) if preco_tag else 0
                            
                            area_txt = "-"
                            if "m²" in info_texto:
                                area_txt = info_texto.split('m²')[0].split('com')[-1].strip() + " m²"
                            
                            if preco_val == 0:
                                p_tag = card.find('p', {'data-ds-component': 'DS-Text'})
                                if p_tag: preco_val = limpar_numero(p_tag.text)

                            if preco_max > 0 and preco_val > preco_max: continue

                            resultados.append({
                                'Imobiliaria': 'Zap Imóveis',
                                'Bairro': bairro,
                                'Tipo': tipo,
                                'Preco': preco_val,
                                'Quartos': int(quartos_min), # Baseado na busca
                                'Area': area_txt,
                                'Link': link
                            })
                            validos += 1

                        except Exception as e:
                            continue

                    print(f"    Cards encontrados: {len(cards)} | Válidos: {validos}")

                except Exception as e:
                    print(f"    Erro ao acessar URL: {e}")

                time.sleep(random.uniform(2, 4))

            browser.close()

        return resultados