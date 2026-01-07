# Visão geral do fluxo (`SYNC.sh`)

Este documento descreve **o fluxo geral** do script `/var/WORKTMP/SYNC/SYNC.sh` (também usado como `$HOME/TMP/SYNC/SYNC.sh`), explicando **cada bloco funcional** (funções, estruturas de dados, variáveis globais e o `main`) e como os dados percorrem o pipeline até publicação na estrutura **SDS (SeisComP)**.

> Convenção deste texto: quando eu cito “linhas X–Y”, refiro-me ao arquivo `SYNC.sh` atual (≈ 1034 linhas).

---

## 0) Objetivo operacional do script

O `SYNC.sh` automatiza:

1. **Identificação do último dia sincronizado** na SDS (`/SDS/<ANO>/<REDE>/<ESTACAO>/HHZ.D`).
2. **Seleção automática do melhor pacote** (ZIP/RAR/TAR/ZIP.BZ2) em `ZIP/<ESTACAO>/` que contenha dados **a partir** do último sincronizado.
3. **Processamento específico por tipo de estação**:
   - **REFTEK RT130**: binário → miniSEED → `dataselect` → `sdsClone.py` → `workthisout.sh`.
   - **Raspberry Shake**: miniSEED → correções (`msmod`) → `dataselect` → `sdsClone.py` → `workthisout.sh`.
4. **Rastreabilidade e integridade**: log único por execução, renomeado ao final e enriquecido com **MD5** e tamanhos.

---

## 1) Regras globais de robustez e rastreabilidade

### 1.1 `set -euo pipefail` (linha 14)
O script impõe:

- `-e`: aborta ao ocorrer erro (retorno ≠ 0), exceto em construções controladas, ou seja, dentro de testes, if/elif/while/until não aborta se retornar ≠ 0.
- `-u`: aborta se variável não definida for expandida.
- `-o pipefail`: um erro em qualquer comando do *pipe* propaga falha.

**Consequência prática:** para comandos que podem falhar “controladamente”, o script encapsula em `run_cmd` (abaixo) e em alguns `if ! ...; then` explícitos.

### 1.2 `run_cmd()` (linhas 24–32)
**Finalidade:** executar um comando preservando o comportamento do `set -e`, mas registrando erro no log com timestamp.

- Entrada: `run_cmd <cmd> <args...>`
- Saída:
  - retorna `0` se sucesso;
  - retorna o código original se falha, e registra:
    - timestamp
    - comando completo
    - status

**Ponto importante:** `run_cmd` escreve em `$log_file`. O arquivo é definido mais tarde no bloco “CONFIG + MAIN”, mas isso é válido porque a função só é **executada** após a configuração.

---

## 2) Inventário estático: estações, DAS codes e projetos

### 2.1 Listas por tipo (linhas 35–36)
- `reftek_stations`: estações processadas pelo fluxo RT130.
- `raspberry_stations`: estações processadas pelo fluxo Raspberry Shake.

Essas listas alimentam a detecção de `station_type`.

### 2.2 `das_codes` (linhas 38–47)
Mapeia `ESTACAO → DAS_CODE` (ou serial/código de origem).

- Suporta **múltiplos códigos** em uma mesma estação (valor contendo espaço), por exemplo: `"AD20 9789"`.
- Esse suporte é consumido por:
  - `build_code_pattern` (regex `A|B|C`)
  - `split_das_codes` (array de códigos)

### 2.3 `projects` + `project_map` (linhas 49–66)
- `projects`: menu de escolha **Projeto|Estação**.
- `project_map`: Projeto → código de rede SDS (`BC`, `BL`, `IT`, `MC`, `SP`).

No fluxo, o `project_code` sempre vem de `project_map[PROJETO_ESCOLHIDO]`.

### 2.4 Futura expansão
O inventário estático pode ser expandido com novas estações e projetos utilizando PARFILE

---

## 3) Variáveis globais (para compatibilidade com `set -u`)

### 3.1 Globais inicializadas com string vazia (linhas 71–88)
O script define antecipadamente (vazio) variáveis que serão preenchidas no `main`:

- Identidade / contexto:
  - `PROJETO_ESCOLHIDO`, `ESTACAO_ESCOLHIDA`, `ANO_FORCADO`
  - `project_code`, `das_code`, `origin_dir`, `station_type`
- Seleção do pacote:
  - `closest_zip`, `closest_zip_orig`, `closest_date`, `last_date`
- Estado SDS:
  - `ultimo_sinc`, `ano_sinc`
- **`code_pattern`**: inicializado como `""` (linhas 80–81) para não quebrar `-u`.

**Invariante importante do fluxo:** antes de procurar datas REFTEK em arquivos compactados, `code_pattern` precisa estar **não vazio**, pois vira a lista de DAS codes aceitos (formato `A|B|C`).

---

## 4) Suporte a múltiplos DAS_CODE

### 4.1 `build_code_pattern()` (linhas 93–104)
Transforma uma string com possíveis múltiplos códigos (separados por espaço) em uma alternativa regex com `|`.

- Entrada: `"AD20 9789"`
- Saída: `"AD20|9789"`

Esse padrão é usado pela extração de datas REFTEK em qualquer profundidade (função `extract_reftek_dates_any_depth`).

### 4.2 `split_das_codes()` (linhas 107–110)
Gera o array global `_CODES_SPLIT` com os DAS codes individuais.

É usado principalmente dentro do `processar_reftek` para montar buscas com `find`.

---

## 5) Funções utilitárias gerais

### 5.1 `log_debug()` (linha 115)
Imprime mensagens de debug quando `VERBOSE=1` (definido no main).

### 5.2 `dia_juliano()` (linha 117)
Converte data gregoriana para dia juliano via `date -d ... +%j`.

**Observação:** no script atual, ela está definida mas não é chamada em nenhum ponto.

### 5.3 `is_station_in_list()` (linhas 119–128)
Checa pertencimento de uma estação em uma lista (retorno 0/1).

É usada para classificar `station_type`.

---

## 6) Seleção Projeto/Estação (modo interativo)

### 6.1 `seleciona_projeto_estacao()` (linhas 131–167)
Fluxo:

1. Imprime menu enumerando `projects`.
2. Lê a opção do usuário.
3. Deriva e define:
   - `PROJETO_ESCOLHIDO`, `ESTACAO_ESCOLHIDA`
   - `project_code` via `project_map`
   - `das_code` via `das_codes`
   - `origin_dir = $base_dir/ZIP/$ESTACAO_ESCOLHIDA`
4. **Define `code_pattern` obrigatoriamente** (linhas 151–153):
   - `code_pattern="$(build_code_pattern "$das_code")"`
   - aborta se ficar vazio
5. Classifica `station_type`:
   - `reftek` se estação está em `reftek_stations`
   - `raspberry` se está em `raspberry_stations`
   - aborta se não reconhecida

**Efeito no resto do script:** após esta função, o contexto mínimo do processamento está fechado: rede SDS (`project_code`), estação, DAS code(s), tipo.

---

## 7) Determinar o último sincronizado na SDS

### 7.1 `obter_ultimo_sinc()` (linhas 169–212)
Esta função define o ponto de partida “a partir de onde procurar dados novos”.

#### Caso A — sincronização forçada com opção -f (`FORCE_SYNC=1`) (linhas 170–179)
- `ano_sinc = ano atual`
- `ultimo_sinc = 0`

Isso faz com que qualquer pacote com datas internas seja considerado “novo”.

#### Caso B — regra padrão (linhas 181–211)
1. `ano_atual = date +%Y`
2. tenta:
   - `ano_atual`
   - `ano_atual - 1`
3. Para cada ano, checa o diretório:
   - `/SDS/<ANO>/<project_code>/<ESTACAO_ESCOLHIDA>/HHZ.D`
4. Se existir, obtém o último `JJJ` presente:
   - lista arquivos
   - extrai último campo após `.` (`awk -F'.' '{print $NF}'`)
   - `sort -u | tail -n1`

Resultado:
- `ano_sinc = ano encontrado`
- `ultimo_sinc = último JJJ encontrado`

**Ponto operacional:** esse `ultimo_sinc` é comparado com as datas internas dos pacotes para decidir o que é “novo”.

---

## 8) Suporte a arquivos compactados e listagem de paths internos

Esses blocos são usados pela seleção automática do pacote “closest”.

### 8.1 `prepare_archive()` (linhas 214–247)
Normaliza a entrada e define 3 globais:

- `ARCH_ORIG`: caminho original do arquivo
- `ARCH_FILE`: arquivo que será efetivamente inspecionado
- `ARCH_KIND`: `zip|rar|tar`

Casos:
- `*.zip.bz2`:
  - descompacta para cache em `$base_dir/_ARCHIVE_CACHE/`
  - `ARCH_FILE` vira o `.zip` descompactado
  - valida integridade via `unzip -tqq`
- `*.zip`, `*.rar`, `*.tar`: define `ARCH_KIND` e usa o próprio arquivo
- outros: retorna `2` (extensão não suportada)

### 8.2 `list_archive_paths()` (linhas 249–258)
Lista caminhos internos sem extrair:
- zip: `unzip -Z1`
- rar: `unrar lb -p-`
- tar: `tar -tf`

---

## 9) Extração de “datas internas” do pacote

A seleção do pacote depende de conseguir extrair **quais dias (YYYYJJJ)** existem dentro do arquivo.

### 9.1 Raspberry: `extract_dates_from_rasp()` (linhas 260–273)
Procura entradas no padrão:

- `/data/archive/<YYYY>/AM/<das_code>/EH[ZEN].D/`

Extrai `YYYY` e `JJJ` do final do path (parte `...<YYYY>.<JJJ>`), retornando `YYYYJJJ` ordenado e único.

### 9.2 REFTEK (qualquer profundidade): `extract_reftek_dates_any_depth()` (linhas 275–305)
Objetivo: encontrar diretórios que indiquem a presença de dados no padrão REFTEK:

- `YYYYJJJ/<DAS>/0` e `YYYYJJJ/<DAS>/1`

Características:

- não assume profundidade fixa (funciona se o pacote tiver prefixos extras)
- trata paths com `./` no início
- aceita múltiplos DAS via `codes_pat` (`A|B|C`) (PARB ocorreu de mudar o DAS_CODE, por isto foi necessário criar uma função que aceite uma lista de DAS codes)
- aceita `YYYYJJJ` com sufixo (`YYYYJJJ_...`), mas reduz para os 7 dígitos depois

Saída: lista de “datas brutas” (o token do `YYYYJJJ` possivelmente com sufixo), depois o chamador normaliza para `YYYYJJJ` puro.

---

## 10) Seleção automática do pacote “closest”

### 10.1 `encontrar_closest_zip()` (linhas 308–408)
Percorre todos os arquivos em `ZIP/<ESTACAO>/` e escolhe o melhor candidato com base no último sincronizado.

#### 10.1.1 Inicialização (linhas 309–323)
- define `best_diff=999`
- zera variáveis globais de seleção
- garante `das_code` e `code_pattern` não vazios
- ativa `nullglob` para o loop não iterar literal `*` se diretório vazio

#### 10.1.2 Loop por arquivo (linhas 325–396)
Para cada `arquivo`:

1. `prepare_archive arquivo`
   - se extensão não suportada: pula
2. extrai datas internas conforme `station_type`:
   - Raspberry: `extract_dates_from_rasp`
   - Reftek: `extract_reftek_dates_any_depth`
3. normaliza para `YYYYJJJ` puro (remove sufixos) e ordena (linhas 356–362)
4. filtra datas “novas” (linhas 367–376):
   - mantém `dia` com `JJJ >= ultimo_sinc`
   - usa `10#` para evitar interpretação octal (ex.: `008`)
5. define:
   - `first_new` = primeiro dia novo
   - `last_new` = último dia novo
   - `diff = first_new.JJJ - ultimo_sinc`
6. atualiza o “melhor” candidato:
   - menor `diff` vence
   - empate em `diff`: maior `last_new` vence

#### 10.1.3 Resultado consolidado (linhas 398–407)
Após o loop, define:

- `closest_zip` (arquivo efetivo, já “normalizado” pelo cache se `.zip.bz2`)
- `closest_zip_orig` (arquivo original)
- `closest_date` (primeiro dia “novo” no arquivo)
- `last_date` (último dia disponível no arquivo)

E imprime também as datas gregorianas derivadas de `YYYYJJJ`.

---

## 11) Validação e tolerâncias do `parfile` (bloco transversal do REFTEK)

Estas funções não fazem a seleção do pacote; elas entram no **fluxo REFTEK** após o modo exploratório do `rt2ms`.

### 11.1 `comparar_parfiles_com_tolerancia()` (linhas 413–534)
Compara `parfile.txt` gerado vs template `PARFILES/<ESTACAO>_parfile.txt`.

Regras-chave:
- cabeçalho deve ser idêntico
- compara somente `refstrm == 1`
- tolerâncias:
  - `NETCODE`: aceita equivalência case-insensitive e aceita exploratório `xx`
  - `CHANNEL`: permite equivalência `HHN ↔ HH1` e `HHE ↔ HH2` (case-insensitive)
- outros campos (`STATION`, `LOC`, `SR`, `GAIN`, `IMPLEMENT_TIME`) devem bater

Falhas geram `exit != 0`, abortando o script (por `set -e` no chamador).

### 11.2 `resumir_auto_substituicoes_parfile()` (linhas 537–579)
Lê `rt2ms.msg` e imprime no log um resumo humano quando o `rt2ms` tiver substituído automaticamente:
- `NETCODE` inválido → default
- canal inválido → rename

---

## 12) Fluxo específico: REFTEK (funções auxiliares de inspeção interna)

### 12.1 `find_reftek_dirs_stream1()` (linhas 581–594)
Busca diretórios `*/<DAS>/1` abaixo de um root (tipicamente o `binary_dir`).

Uso: verificação de integridade horária (espera 24 arquivos por diretório-hora).

### 12.2 `find_reftek_files_stream0()` (linhas 596–609)
Busca arquivos `*/<DAS>/0/*` (tipicamente logs SH) para extrair GPS e bateria.

---

## 13) Fluxo REFTEK (visão de blocos)

### 13.1 `processar_reftek()` (linhas 611–778)
Este bloco é executado quando `station_type="reftek"` e o atalho “/sds/ no ZIP” não se aplica.

Etapas principais:

1. **Deriva intervalo de coleta** a partir de `closest_date` e `last_date` e cria:
   - `target_dir = $base_dir/<ESTACAO>_<YYYYMMDD>`
   - `binary_dir = <ESTACAO>_<YYYYMMDD>_BINARIES`
2. **Descompacta** `closest_zip` em `target_dir` (zip/rar/tar).
3. **Move** apenas a subárvore a partir de `YYYYJJJ/DASCODE/` para dentro de `binary_dir`:
   - preserva `YYYYJJJ/DASCODE/...` dentro do BINARIES
   - remove diretórios vazios remanescentes
4. **Checagem de integridade horária**:
   - varre `*/DAS/1`
   - se `count_files != 24`, marca como:
     - “BORDA DE COLETA” se for o primeiro/último dia do intervalo
     - “ARQUIVOS INCOMPLETOS” caso contrário
5. **Extração de GPS/BATTERY** a partir de `*/DAS/0/*`:
   - agrega em `<ESTACAO>_<YYYYMMDD>_info.log`
   - gera ordenados:
     - `<ESTACAO>_<YYYYMMDD>.gps`
     - `<ESTACAO>_<YYYYMMDD>.battery`
6. **Conversão binário → miniSEED** via `rt2ms_py3` em 2 fases:
   - modo exploratório `-e` para gerar `parfile.txt` + `rt2ms.msg`
   - valida `parfile.txt` contra template (se existir)
   - conversão final com `-p template -o <NET>.<ESTACAO>.MSEED`
7. **Publicação em SDS local** e pipeline SeisComP:
   - `dataselect` (constrói `target_dir/sds`)
   - `sdsClone.py` (gera log de clone)
   - `workthisout.sh --nostop` (publishes/organiza)

Saída operacional: SDS pronta em `target_dir/sds/`, logs prontos para consolidação em `finalizar_log`.

---

## 14) Fluxo Raspberry Shake (visão de blocos)

### 14.1 `processar_raspberry()` (linhas 781–836)
Etapas principais:

1. Define `target_dir = $base_dir/<ESTACAO>_<YYYYMMDD>` (baseado em `last_date`).
2. Lista no ZIP apenas arquivos com `JJJ >= ultimo_sinc` e extrai para:
   - `MSEED_DIR = <ESTACAO>_<YYYYMMDD>_MSEED`
3. Renomeia e corrige headers:
   - canais `EHZ/EHN/EHE` → `HHZ/HHN/HHE`
   - ajusta NET/STA/LOC/CHAN com `msmod`
   - remove arquivo original após criar o novo nome
4. Publica com:
   - `dataselect` para `target_dir/sds/`
   - `sdsClone.py`
   - `workthisout.sh --nostop`

---

## 15) Finalização e rastreabilidade do log

### 15.1 `finalizar_log()` (linhas 839–886)
Consolida o log e cria uma chave única da execução:

- `key = <ESTACAO>_<YYYYMMDD>_<HHMM>`

Ações:

1. calcula e registra no log:
   - tamanho do `target_dir/sds` (se existir)
   - `md5sum` e tamanho do pacote de entrada (preferindo `closest_zip_orig`)
2. renomeia o log principal:
   - `LOGS/<ESTACAO>_<YYYYMMDD>_<HHMM>_sync.log`
3. move anexos RT130:
   - `target_dir/LOGS/RT130_*.log` → `LOGS/<key>_RT130_....log`
4. renomeia o log r2m (se existir):
   - `LOGS/<ESTACAO>_<YYYYMMDD>_<HHMM>_r2m.log`
5. grava timestamp final “Sincronização concluída”.

---

## 16) Bloco CONFIG + MAIN (controle do fluxo)

### 16.1 Configuração de diretórios e log (linhas 891–899)
Define o ambiente de execução:

- `base_dir="$HOME/TMP/SYNC"`
- `log_dir="$base_dir/LOGS"`
- `PARFILES_DIR="$base_dir/PARFILES/"`

E ativa o *capture* integral:

- `exec > >(tee -a "$log_file") 2>&1`

A partir daqui, **tudo** que o script imprime vai para o arquivo e para o stdout.

### 16.2 CLI e modos de execução (linhas 901–930)
- `usage()` define flags:
  - `-p` projeto, `-e` estação
  - `-y` ano forçado
  - `-f` força sync
  - `-h` ajuda

- `getopts` popula variáveis globais.

### 16.3 Seleção do contexto (linhas 932–967)
Caso `-p` e `-e` tenham sido fornecidos:

1. valida se a combinação existe em `projects`
2. define `project_code`, `das_code`, `origin_dir`
3. **define `code_pattern`** (linhas 950–952)
4. define `station_type` por pertencimento em listas

Caso contrário, cai no modo interativo:
- `seleciona_projeto_estacao`

### 16.4 Ano forçado (linhas 968–993)
Se `ANO_FORCADO` foi definido, o script **redefine** (override) a função `obter_ultimo_sinc()` para usar exclusivamente:

- `/SDS/<ANO_FORCADO>/<REDE>/<ESTACAO>/HHZ.D`

Isso substitui a lógica “ano atual e anterior”.

### 16.5 Execução da seleção automática (linhas 995–996)
Sequência fixa:

1. `obter_ultimo_sinc`
2. `encontrar_closest_zip`

Após isso, o script tem:
- qual pacote usar (`closest_zip`)
- qual intervalo de datas ele cobre (`closest_date` → `last_date`)
- qual o último sincronizado (`ultimo_sinc`)

### 16.6 Atalho REFTEK: pacote já contém `/sds/` (linhas 998–1022)
Se `station_type=reftek` e o `closest_zip` contém paths com `/sds/`:

1. extrai os miniSEED em `target_dir/<ESTACAO>_<YYYYMMDD>_MSEED`
2. publica direto com `dataselect` + `sdsClone.py` + `workthisout.sh`
3. roda `finalizar_log` e encerra (`exit 0`)

**Finalidade do atalho:** pular a conversão binária quando o pacote já vem “pronto”.

### 16.7 Dispatch final e encerramento (linhas 1024–1034)
Se não caiu no atalho:

- `dispatch_processing()` chama:
  - `processar_reftek` ou `processar_raspberry`
- depois chama `finalizar_log`
- `exit 0`

---

## 17) Glossário rápido das variáveis que “amarram” o fluxo

- `project_code`: rede SDS (BC/BL/IT/MC/SP)
- `das_code`: código(s) de origem (um ou mais)
- `code_pattern`: `das_code` convertido para `A|B|C` (uso em extração REFTEK)
- `ultimo_sinc`: último `JJJ` encontrado em `/SDS/.../HHZ.D`
- `closest_zip`: arquivo compactado escolhido (já “normalizado” se era `.zip.bz2`)
- `closest_zip_orig`: referência ao arquivo original (para MD5 e tamanho)
- `closest_date`, `last_date`: `YYYYJJJ` do primeiro e último dia “novo” no pacote
- `target_dir`: diretório de trabalho por execução
- `log_file`: log da execução (renomeado ao final)

---

## 18) Limites e garantias do fluxo geral

Garantias que o `main` tenta manter antes de iniciar o processamento específico:

- `project_code`, `das_code`, `station_type` definidos e válidos
- `code_pattern` não vazio (necessário para REFTEK)
- `ultimo_sinc` obtido com regra clara (ano atual/anterior ou `-y`, ou `-f`)
- `closest_zip` escolhido por um critério determinístico (menor diff, desempate por maior alcance)

Qualquer quebra de uma dessas garantias termina em `exit 1` com log detalhado.
