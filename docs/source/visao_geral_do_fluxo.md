# Visão geral do fluxo (`SYNC.sh`)

Este documento descreve **o fluxo geral** do script `/var/WORKTMP/SYNC/SYNC.sh` (também usado como `$HOME/TMP/SYNC/SYNC.sh`), explicando **cada bloco funcional** (funções, estruturas de dados, variáveis globais e o `main`) e como os dados percorrem o pipeline até publicação na estrutura **SDS (SeisComP)**.

> Convenção deste texto: quando eu cito um bloco de código, uso trechos extraídos por marcadores estáveis no `SYNC.sh`.

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

(sync-strict-mode)=
### 1.1 `set -euo pipefail`
```{literalinclude} ../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-MAIN-STRICT-MODE"
:end-before: "DOC-END: SYNC-MAIN-STRICT-MODE"
:language: bash
:caption: Modo estrito do shell
:name: code-strict-mode
```
O script impõe:

- `-e`: aborta ao ocorrer erro (retorno ≠ 0), exceto em construções controladas, ou seja, dentro de testes, if/elif/while/until não aborta se retornar ≠ 0.
- `-u`: aborta se variável não definida for expandida.
- `-o pipefail`: um erro em qualquer comando do *pipe* propaga falha.

**Consequência prática:** para comandos que podem falhar “controladamente”, o script encapsula em `run_cmd` (abaixo) e em alguns `if ! ...; then` explícitos.

(sync-run-cmd)=
### 1.2 `run_cmd()`
```{literalinclude} ../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-run_cmd"
:end-before: "DOC-END: SYNC-FUNC-run_cmd"
:language: bash
:caption: Função run_cmd
:name: code-run-cmd
```
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

(sync-station-lists)=
### 2.1 Listas por tipo
```{literalinclude} ../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-DATA-STATION-LISTS"
:end-before: "DOC-END: SYNC-DATA-STATION-LISTS"
:language: bash
:caption: Listas de estações
:name: code-station-lists
```
- `reftek_stations`: estações processadas pelo fluxo RT130.
- `raspberry_stations`: estações processadas pelo fluxo Raspberry Shake.

Essas listas alimentam a detecção de `station_type`.

(sync-das-codes)=
### 2.2 `das_codes`
```{literalinclude} ../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-DATA-DAS-CODES"
:end-before: "DOC-END: SYNC-DATA-DAS-CODES"
:language: bash
:caption: Mapa de DAS codes
:name: code-das-codes
```
Mapeia `ESTACAO → DAS_CODE` (ou serial/código de origem).

- Suporta **múltiplos códigos** em uma mesma estação (valor contendo espaço), por exemplo: `"AD20 9789"`.
- Esse suporte é consumido por:
  - `build_code_pattern` (regex `A|B|C`)
  - `split_das_codes` (array de códigos)

(sync-projects)=
### 2.3 `projects` + `project_map`
```{literalinclude} ../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-DATA-PROJECTS"
:end-before: "DOC-END: SYNC-DATA-PROJECTS"
:language: bash
:caption: Lista de projetos
:name: code-projects
```
```{literalinclude} ../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-DATA-PROJECT-MAP"
:end-before: "DOC-END: SYNC-DATA-PROJECT-MAP"
:language: bash
:caption: Mapa de projetos
:name: code-project-map
```
- `projects`: menu de escolha **Projeto|Estação**.
- `project_map`: Projeto → código de rede SDS (`BC`, `BL`, `IT`, `MC`, `SP`).

No fluxo, o `project_code` sempre vem de `project_map[PROJETO_ESCOLHIDO]`.

### 2.4 Futura expansão
O inventário estático pode ser expandido com novas estações e projetos utilizando PARFILE

---

## 3) Variáveis globais (para compatibilidade com `set -u`)

(sync-globals)=
### 3.1 Globais inicializadas com string vazia
```{literalinclude} ../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-INVAR-GLOBALS"
:end-before: "DOC-END: SYNC-INVAR-GLOBALS"
:language: bash
:caption: Globais inicializadas
:name: code-globals
```
O script define antecipadamente (vazio) variáveis que serão preenchidas no `main`:

- Identidade / contexto:
  - `PROJETO_ESCOLHIDO`, `ESTACAO_ESCOLHIDA`, `ANO_FORCADO`
  - `project_code`, `das_code`, `origin_dir`, `station_type`
- Seleção do pacote:
  - `closest_zip`, `closest_zip_orig`, `closest_date`, `last_date`
- Estado SDS:
  - `ultimo_sinc`, `ano_sinc`
- **`code_pattern`**: inicializado como `""` para não quebrar `-u`.

**Invariante importante do fluxo:** antes de procurar datas REFTEK em arquivos compactados, `code_pattern` precisa estar **não vazio**, pois vira a lista de DAS codes aceitos (formato `A|B|C`).

---

## 4) Suporte a múltiplos DAS_CODE

(sync-build-code-pattern)=
### 4.1 `build_code_pattern()`
```{literalinclude} ../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-build_code_pattern"
:end-before: "DOC-END: SYNC-FUNC-build_code_pattern"
:language: bash
:caption: build_code_pattern
:name: code-build-code-pattern
```
Transforma uma string com possíveis múltiplos códigos (separados por espaço) em uma alternativa regex com `|`.

- Entrada: `"AD20 9789"`
- Saída: `"AD20|9789"`

Esse padrão é usado pela extração de datas REFTEK em qualquer profundidade (função `extract_reftek_dates_any_depth`).

(sync-split-das-codes)=
### 4.2 `split_das_codes()`
```{literalinclude} ../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-split_das_codes"
:end-before: "DOC-END: SYNC-FUNC-split_das_codes"
:language: bash
:caption: split_das_codes
:name: code-split-das-codes
```
Gera o array global `_CODES_SPLIT` com os DAS codes individuais.

É usado principalmente dentro do `processar_reftek` para montar buscas com `find`.

---

## 5) Funções utilitárias gerais

(sync-log-debug)=
### 5.1 `log_debug()`
```{literalinclude} ../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-log_debug"
:end-before: "DOC-END: SYNC-FUNC-log_debug"
:language: bash
:caption: log_debug
:name: code-log-debug
```
Imprime mensagens de debug quando `VERBOSE=1` (definido no main).

(sync-dia-juliano)=
### 5.2 `dia_juliano()`
```{literalinclude} ../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-dia_juliano"
:end-before: "DOC-END: SYNC-FUNC-dia_juliano"
:language: bash
:caption: dia_juliano
:name: code-dia-juliano
```
Converte data gregoriana para dia juliano via `date -d ... +%j`.

**Observação:** no script atual, ela está definida mas não é chamada em nenhum ponto.

(sync-is-station-in-list)=
### 5.3 `is_station_in_list()`
```{literalinclude} ../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-is_station_in_list"
:end-before: "DOC-END: SYNC-FUNC-is_station_in_list"
:language: bash
:caption: is_station_in_list
:name: code-is-station-in-list
```
Checa pertencimento de uma estação em uma lista (retorno 0/1).

É usada para classificar `station_type`.

---

## 6) Seleção Projeto/Estação (modo interativo)

(sync-seleciona-projeto)=
### 6.1 `seleciona_projeto_estacao()`
```{literalinclude} ../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-seleciona_projeto_estacao"
:end-before: "DOC-END: SYNC-FUNC-seleciona_projeto_estacao"
:language: bash
:caption: seleciona_projeto_estacao
:name: code-seleciona-projeto
```
Fluxo:

1. Imprime menu enumerando `projects`.
2. Lê a opção do usuário.
3. Deriva e define:
   - `PROJETO_ESCOLHIDO`, `ESTACAO_ESCOLHIDA`
   - `project_code` via `project_map`
   - `das_code` via `das_codes`
   - `origin_dir = $base_dir/ZIP/$ESTACAO_ESCOLHIDA`
4. **Define `code_pattern` obrigatoriamente**:
   - `code_pattern="$(build_code_pattern "$das_code")"`
   - aborta se ficar vazio
5. Classifica `station_type`:
   - `reftek` se estação está em `reftek_stations`
   - `raspberry` se está em `raspberry_stations`
   - aborta se não reconhecida

**Efeito no resto do script:** após esta função, o contexto mínimo do processamento está fechado: rede SDS (`project_code`), estação, DAS code(s), tipo.

---

## 7) Determinar o último sincronizado na SDS

(sync-obter-ultimo-sinc)=
### 7.1 `obter_ultimo_sinc()`
```{literalinclude} ../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-obter_ultimo_sinc"
:end-before: "DOC-END: SYNC-FUNC-obter_ultimo_sinc"
:language: bash
:caption: obter_ultimo_sinc
:name: code-obter-ultimo-sinc
```
Esta função define o ponto de partida “a partir de onde procurar dados novos”.

#### Caso A — sincronização forçada com opção -f (`FORCE_SYNC=1`)
- `ano_sinc = ano atual`
- `ultimo_sinc = 0`

Isso faz com que qualquer pacote com datas internas seja considerado “novo”.

#### Caso B — regra padrão
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

(sync-prepare-archive)=
### 8.1 `prepare_archive()`
```{literalinclude} ../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-prepare_archive"
:end-before: "DOC-END: SYNC-FUNC-prepare_archive"
:language: bash
:caption: prepare_archive
:name: code-prepare-archive
```
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

(sync-list-archive-paths)=
### 8.2 `list_archive_paths()`
```{literalinclude} ../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-list_archive_paths"
:end-before: "DOC-END: SYNC-FUNC-list_archive_paths"
:language: bash
:caption: list_archive_paths
:name: code-list-archive-paths
```
Lista caminhos internos sem extrair:
- zip: `unzip -Z1`
- rar: `unrar lb -p-`
- tar: `tar -tf`

---

## 9) Extração de “datas internas” do pacote

A seleção do pacote depende de conseguir extrair **quais dias (YYYYJJJ)** existem dentro do arquivo.

(sync-extract-dates-rasp)=
### 9.1 Raspberry: `extract_dates_from_rasp()`
```{literalinclude} ../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-extract_dates_from_rasp"
:end-before: "DOC-END: SYNC-FUNC-extract_dates_from_rasp"
:language: bash
:caption: extract_dates_from_rasp
:name: code-extract-dates-rasp
```
Procura entradas no padrão:

- `/data/archive/<YYYY>/AM/<das_code>/EH[ZEN].D/`

Extrai `YYYY` e `JJJ` do final do path (parte `...<YYYY>.<JJJ>`), retornando `YYYYJJJ` ordenado e único.

(sync-extract-reftek-dates)=
### 9.2 REFTEK (qualquer profundidade): `extract_reftek_dates_any_depth()`
```{literalinclude} ../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-extract_reftek_dates_any_depth"
:end-before: "DOC-END: SYNC-FUNC-extract_reftek_dates_any_depth"
:language: bash
:caption: extract_reftek_dates_any_depth
:name: code-extract-reftek-dates
```
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

(sync-encontrar-closest-zip)=
### 10.1 `encontrar_closest_zip()`
```{literalinclude} ../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-encontrar_closest_zip"
:end-before: "DOC-END: SYNC-FUNC-encontrar_closest_zip"
:language: bash
:caption: encontrar_closest_zip
:name: code-encontrar-closest-zip
```
Percorre todos os arquivos em `ZIP/<ESTACAO>/` e escolhe o melhor candidato com base no último sincronizado.

#### 10.1.1 Inicialização
- define `best_diff=999`
- zera variáveis globais de seleção
- garante `das_code` e `code_pattern` não vazios
- ativa `nullglob` para o loop não iterar literal `*` se diretório vazio

#### 10.1.2 Loop por arquivo
Para cada `arquivo`:

1. `prepare_archive arquivo`
   - se extensão não suportada: pula
2. extrai datas internas conforme `station_type`:
   - Raspberry: `extract_dates_from_rasp`
   - Reftek: `extract_reftek_dates_any_depth`
3. normaliza para `YYYYJJJ` puro (remove sufixos) e ordena
4. filtra datas “novas”:
   - mantém `dia` com `JJJ >= ultimo_sinc`
   - usa `10#` para evitar interpretação octal (ex.: `008`)
5. define:
   - `first_new` = primeiro dia novo
   - `last_new` = último dia novo
   - `diff = first_new.JJJ - ultimo_sinc`
6. atualiza o “melhor” candidato:
   - menor `diff` vence
   - empate em `diff`: maior `last_new` vence

#### 10.1.3 Resultado consolidado
Após o loop, define:

- `closest_zip` (arquivo efetivo, já “normalizado” pelo cache se `.zip.bz2`)
- `closest_zip_orig` (arquivo original)
- `closest_date` (primeiro dia “novo” no arquivo)
- `last_date` (último dia disponível no arquivo)

E imprime também as datas gregorianas derivadas de `YYYYJJJ`.

---

## 11) Validação e tolerâncias do `parfile` (bloco transversal do REFTEK)

Estas funções não fazem a seleção do pacote; elas entram no **fluxo REFTEK** após o modo exploratório do `rt2ms`.

(sync-comparar-parfiles)=
### 11.1 `comparar_parfiles_com_tolerancia()`
```{literalinclude} ../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-comparar_parfiles_com_tolerancia"
:end-before: "DOC-END: SYNC-FUNC-comparar_parfiles_com_tolerancia"
:language: bash
:caption: comparar_parfiles_com_tolerancia
:name: code-comparar-parfiles
```
Compara `parfile.txt` gerado vs template `PARFILES/<ESTACAO>_parfile.txt`.

Regras-chave:
- cabeçalho deve ser idêntico
- compara somente `refstrm == 1`
- tolerâncias:
  - `NETCODE`: aceita equivalência case-insensitive e aceita exploratório `xx`
  - `CHANNEL`: permite equivalência `HHN ↔ HH1` e `HHE ↔ HH2` (case-insensitive)
- outros campos (`STATION`, `LOC`, `SR`, `GAIN`, `IMPLEMENT_TIME`) devem bater

Falhas geram `exit != 0`, abortando o script (por `set -e` no chamador).

(sync-resumir-parfiles)=
### 11.2 `resumir_auto_substituicoes_parfile()`
```{literalinclude} ../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-resumir_auto_substituicoes_parfile"
:end-before: "DOC-END: SYNC-FUNC-resumir_auto_substituicoes_parfile"
:language: bash
:caption: resumir_auto_substituicoes_parfile
:name: code-resumir-parfiles
```
Lê `rt2ms.msg` e imprime no log um resumo humano quando o `rt2ms` tiver substituído automaticamente:
- `NETCODE` inválido → default
- canal inválido → rename

---

## 12) Fluxo específico: REFTEK (funções auxiliares de inspeção interna)

(sync-find-reftek-dirs-stream1)=
### 12.1 `find_reftek_dirs_stream1()`
```{literalinclude} ../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-find_reftek_dirs_stream1"
:end-before: "DOC-END: SYNC-FUNC-find_reftek_dirs_stream1"
:language: bash
:caption: find_reftek_dirs_stream1
:name: code-find-reftek-dirs-stream1
```
Busca diretórios `*/<DAS>/1` abaixo de um root (tipicamente o `binary_dir`).

Uso: verificação de integridade horária (espera 24 arquivos por diretório-hora).

(sync-find-reftek-files-stream0)=
### 12.2 `find_reftek_files_stream0()`
```{literalinclude} ../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-find_reftek_files_stream0"
:end-before: "DOC-END: SYNC-FUNC-find_reftek_files_stream0"
:language: bash
:caption: find_reftek_files_stream0
:name: code-find-reftek-files-stream0
```
Busca arquivos `*/<DAS>/0/*` (tipicamente logs SH) para extrair GPS e bateria.

---

## 13) Fluxo REFTEK (visão de blocos)

(sync-processar-reftek)=
### 13.1 `processar_reftek()`
```{literalinclude} ../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-processar_reftek"
:end-before: "DOC-END: SYNC-FUNC-processar_reftek"
:language: bash
:caption: processar_reftek
:name: code-processar-reftek
```
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

(sync-processar-raspberry)=
### 14.1 `processar_raspberry()`
```{literalinclude} ../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-processar_raspberry"
:end-before: "DOC-END: SYNC-FUNC-processar_raspberry"
:language: bash
:caption: processar_raspberry
:name: code-processar-raspberry
```
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

(sync-finalizar-log)=
### 15.1 `finalizar_log()`
```{literalinclude} ../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-finalizar_log"
:end-before: "DOC-END: SYNC-FUNC-finalizar_log"
:language: bash
:caption: finalizar_log
:name: code-finalizar-log
```
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

(sync-config-logging)=
### 16.1 Configuração de diretórios e log
```{literalinclude} ../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-MAIN-CONFIG-LOGGING"
:end-before: "DOC-END: SYNC-MAIN-CONFIG-LOGGING"
:language: bash
:caption: Configuração de diretórios e log
:name: code-config-logging
```
Define o ambiente de execução:

- `base_dir="$HOME/TMP/SYNC"`
- `log_dir="$base_dir/LOGS"`
- `PARFILES_DIR="$base_dir/PARFILES/"`

E ativa o *capture* integral:

- `exec > >(tee -a "$log_file") 2>&1`

A partir daqui, **tudo** que o script imprime vai para o arquivo e para o stdout.

(sync-cli-usage)=
### 16.2 CLI e modos de execução
```{literalinclude} ../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-MAIN-CLI-USAGE"
:end-before: "DOC-END: SYNC-MAIN-CLI-USAGE"
:language: bash
:caption: CLI usage
:name: code-cli-usage
```
```{literalinclude} ../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-MAIN-CLI-GETOPTS"
:end-before: "DOC-END: SYNC-MAIN-CLI-GETOPTS"
:language: bash
:caption: CLI getopts
:name: code-cli-getopts
```
- `usage()` define flags:
  - `-p` projeto, `-e` estação
  - `-y` ano forçado
  - `-f` força sync
  - `-h` ajuda

- `getopts` popula variáveis globais.

(sync-select-context)=
### 16.3 Seleção do contexto
```{literalinclude} ../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-MAIN-SELECT-CONTEXT"
:end-before: "DOC-END: SYNC-MAIN-SELECT-CONTEXT"
:language: bash
:caption: Seleção do contexto
:name: code-select-context
```
Caso `-p` e `-e` tenham sido fornecidos:

1. valida se a combinação existe em `projects`
2. define `project_code`, `das_code`, `origin_dir`
3. **define `code_pattern`**
4. define `station_type` por pertencimento em listas

Caso contrário, cai no modo interativo:
- `seleciona_projeto_estacao`

(sync-ano-forcado)=
### 16.4 Ano forçado
```{literalinclude} ../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-MAIN-ANO-FORCADO"
:end-before: "DOC-END: SYNC-MAIN-ANO-FORCADO"
:language: bash
:caption: Ano forçado
:name: code-ano-forcado
```
Se `ANO_FORCADO` foi definido, o script **redefine** (override) a função `obter_ultimo_sinc()` para usar exclusivamente:

- `/SDS/<ANO_FORCADO>/<REDE>/<ESTACAO>/HHZ.D`

Isso substitui a lógica “ano atual e anterior”.

(sync-auto-selection)=
### 16.5 Execução da seleção automática
```{literalinclude} ../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-MAIN-AUTO-SELECTION"
:end-before: "DOC-END: SYNC-MAIN-AUTO-SELECTION"
:language: bash
:caption: Seleção automática
:name: code-auto-selection
```
Sequência fixa:

1. `obter_ultimo_sinc`
2. `encontrar_closest_zip`

Após isso, o script tem:
- qual pacote usar (`closest_zip`)
- qual intervalo de datas ele cobre (`closest_date` → `last_date`)
- qual o último sincronizado (`ultimo_sinc`)

(sync-reftek-shortcut)=
### 16.6 Atalho REFTEK: pacote já contém `/sds/`
```{literalinclude} ../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-MAIN-REFTEK-SDS-SHORTCUT"
:end-before: "DOC-END: SYNC-MAIN-REFTEK-SDS-SHORTCUT"
:language: bash
:caption: Atalho REFTEK com SDS
:name: code-reftek-shortcut
```
Se `station_type=reftek` e o `closest_zip` contém paths com `/sds/`:

1. extrai os miniSEED em `target_dir/<ESTACAO>_<YYYYMMDD>_MSEED`
2. publica direto com `dataselect` + `sdsClone.py` + `workthisout.sh`
3. roda `finalizar_log` e encerra (`exit 0`)

**Finalidade do atalho:** pular a conversão binária quando o pacote já vem “pronto”.

(sync-dispatch)=
### 16.7 Dispatch final e encerramento
```{literalinclude} ../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-MAIN-DISPATCH"
:end-before: "DOC-END: SYNC-MAIN-DISPATCH"
:language: bash
:caption: Dispatch final
:name: code-dispatch
```
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
