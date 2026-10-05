# BeeGuard — pipeline de dados V1

Entrega inicial: aquisição preservada, indexação, padronização, verificações técnicas e features acústicas. Não inclui modelo treinado, diagnóstico de doença, score de saúde ou alerta ambiental validado.

## 1. Instalação (Python 3.11 ou 3.12)

Extraia o ZIP, abra o PowerShell na pasta BeeGuard e execute:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Os sete testes usam sinais sintéticos apenas para testar o software, sem avaliar desempenho biológico.

## 2. Processar uma gravação do BeeGuard

Copie WAVs reais para `data/raw/beeguard/`. Se todos forem da mesma colmeia identificada como BG01:

```powershell
.\.venv\Scripts\python.exe index_recordings.py --input data/raw/beeguard --output data/metadata/beeguard.csv --source beeguard --hive-id BG01
.\.venv\Scripts\python.exe prepare_dataset.py --manifest data/metadata/beeguard.csv --output data/processed/beeguard_v1
.\.venv\Scripts\python.exe extract_features.py --metadata data/processed/beeguard_v1/metadata.csv --output data/processed/beeguard_features.csv
```

Resultados: WAVs PCM16 mono 16 kHz de 10 segundos, metadata.csv, report.json e tabela de features. A execução retorna código 1 quando há erros de arquivos ou nenhuma janela; arquivos válidos já processados são preservados e os erros aparecem no relatório.

Para repetir, use outro nome de saída. O pipeline recusa sobrescrever resultados. Por padrão usa as primeiras 12 janelas por arquivo; `--max-windows-per-file 0` processa todas. Não há normalização de pico nem redução automática de ruído nesta versão; preservar amplitude permite investigar energia, sem torná-la comparável entre microfones não calibrados.

## 3. Aquisição existente

O firmware e os dois scripts originais foram copiados sem mudanças. Veja `acquisition/README.md` para ligações e porta serial. Execute o coletor dentro de `acquisition/`; as gravações irão para `acquisition/recordings/`. Você pode usar essa pasta diretamente no argumento `--input`, sem copiar os WAVs.

**O “Saúde da colmeia” e “IBA” do firmware são fórmulas heurísticas existentes; não são resultados de ML nem medições de saúde validadas.** Os dB exibidos não são dB SPL calibrados. A nova pipeline não utiliza esses valores como rótulos.

## 4. UrBAN: próximo conjunto real

Fonte primária de áudio: https://doi.org/10.20383/103.0972

Página do repositório: https://www.frdr-dfdr.ca/repo/dataset/487f5583-250a-464b-bb71-f2da85410b13

Código e anotações dos autores: https://github.com/mahsa-abdollahi/UrBAN

Artigo: https://doi.org/10.1038/s41597-025-04869-1

Comece por um subconjunto, com áudios de várias colmeias e datas de inspeção. Extraia os WAVs em `data/raw/urban/audio/` e gere um manifesto:

```powershell
.\.venv\Scripts\python.exe index_recordings.py --input data/raw/urban/audio --output data/metadata/urban.csv --source urban
```

Antes do treino, preencher `hive_id` com identidade real e associar os áudios às inspeções. O indexador deixa esses campos vazios: não adivinha colmeia, horário ou população. Valores vazios são desconhecidos.

Contrato do manifesto (caminhos relativos à pasta do CSV):

| Campo | Significado |
| --- | --- |
| file | Caminho do WAV original |
| source | urban, beeguard ou outra origem explícita |
| hive_id | Identidade da colmeia, vazia se não conhecida |
| timestamp | Início da gravação, ISO 8601 com fuso se conhecido |
| frames_bees | Número de quadros cobertos por abelhas; vazio se desconhecido |
| label_source | Origem do rótulo e método da associação temporal |
| inspection_id | Referência rastreável à inspeção |

O timestamp original é preservado; `start_seconds` representa o deslocamento de cada janela. Não extrapolar silenciosamente a inspeção para semanas de áudio: a política temporal e eventuais interpolações precisam ser documentadas. Rótulos interpolados são derivados, não ground truth direto.

Quando o manifesto estiver associado e conferido:

```powershell
.\.venv\Scripts\python.exe prepare_dataset.py --manifest data/metadata/urban.csv --output data/processed/urban_v1
.\.venv\Scripts\python.exe extract_features.py --metadata data/processed/urban_v1/metadata.csv --output data/processed/urban_features.csv
```

## 5. Verificações e limites

- Arquivos corrompidos, não finitos e abaixo de 10 s são recusados. Caudas incompletas são descartadas e registradas.
- SHA-256 identifica duplicatas exatas e mantém todas as janelas ligadas à gravação original. Duplicatas acústicas em formatos diferentes ainda não são detectadas.
- Clipping acima de 1% ou RMS abaixo de 0,0001 marca revisão. São limites técnicos iniciais, ajustáveis após dados de campo; não são índice de qualidade biológica.
- Clipping é medido antes de misturar canais; excesso na gravação original marca conservadoramente todas as janelas para revisão. O áudio original é preservado.
- Features: MFCC 0–12 (média/desvio), RMS, cruzamentos por zero, frequência dominante, centroide, dispersão, entropia, rolloff, flatness e fração de potência 122–515 Hz. A implementação é própria e não uma reprodução exata dos benchmarks UrBAN.
- Ainda não há estimador de SNR, detector de fala, curadoria por ML ou inferência de rainha/população.

## 6. Próximo marco

Após obter áudios reais e associar as inspeções: treinar Random Forest para estimar quadros de abelhas, avaliar MAE e baseline constante, separar treino/validação/teste por colmeia (considerando identidade persistente entre anos). Nenhuma janela da mesma colmeia deve cruzar essa divisão. Avaliar também por gravação/inspeção para não supervalorizar várias janelas do mesmo áudio. O teste final deve ficar intocado durante escolhas de features e parâmetros.

Depois: inferência de WAV local, baseline da própria colmeia, detecção de anomalia e regras de decisão calibradas com validação de campo.

## Inspeções reais incluídas nesta entrega

Foram obtidos dos caminhos `data/annotations/inspections_2021.csv` e `inspections_2022.csv` do repositório dos autores em 05/10/2026. Os CSVs originais estão incluídos sem modificações. Confira as condições de uso da fonte antes de redistribuir dados em outro produto.

A inspeção encontrou 109 linhas em 2021, 288 em 2022 e 34 eventos explícitos de `frames of bees` em 2022. Esses 34 registros foram separados em `data/metadata/urban_inspections/population_inspections_2022.csv`, mantendo referência à linha original. Eles são inspeções, não exemplos de áudio associados nem um dataset pronto para treinar.

Para repetir a inspeção, use um novo diretório de saída:

```powershell
.\.venv\Scripts\python.exe inspect_urban.py --output data/metadata/urban_inspections_v2
```

Os áudios UrBAN não foram baixados nesta entrega: o servidor FRDR não respondeu durante a sessão. O mapeamento entre tags das inspeções e identificadores nos nomes de áudio, e a política de associação temporal, continuam pendentes.
