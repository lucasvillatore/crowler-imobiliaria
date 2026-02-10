# Crawler de Imóveis (Apolar e Galvão)

Scripts em Python para automação de busca de imóveis para aluguel. O sistema coleta dados dos sites da Apolar e Galvão Locações, aplica filtros de URL e validação de HTML, e exporta os resultados consolidados para uma planilha Excel.

## Funcionalidades

- **Busca Multi-site**: Arquitetura modular (`providers`) para adicionar novas imobiliárias.
- **Validação de Bairro**: Verifica se o imóvel retornado pertence efetivamente ao bairro solicitado, descartando sugestões de "bairros próximos" ou anúncios patrocinados irrelevantes.
- **Exportação Unificada**: Gera um arquivo `compilado_final.xlsx` com dados normalizados e ordenados por preço.
- **Bypass de SSL**: Configurado para rodar em redes com interceptação de certificado (VPNs corporativas).

## Estrutura do Projeto

```text
.
├── main.py              # Script principal (configuração e execução)
├── requirements.txt     # Dependências do projeto
├── providers/           # Módulos das imobiliárias
│   ├── __init__.py
│   ├── apolar.py        # Lógica de scraping da Apolar
│   └── galvao.py        # Lógica de scraping da Galvão
└── README.md

## Instalação

```bash
pip install -r requirements.txt
```
