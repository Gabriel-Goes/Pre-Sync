# Visão geral do fluxo

O `SYNC.sh` é o fluxo principal para **sincronizar** e **publicar** dados de estações **REFTEK RT130** e **Raspberry Shake** na estrutura **SDS (SeisComP)**, com **seleção automática do pacote** de dados a processar e **rastreabilidade via logs**.

---

## 1) Estrutura de diretórios e entradas

O `SYNC.sh` trabalha a partir do diretório base:

- `base_dir = $HOME/TMP/SYNC`

Principais subdiretórios usados pelo fluxo:

- `ZIP/<ESTACAO>/`
  Entrada: arquivos compactados (`.zip`, `.zip.bz2`, `.rar`, `.tar`) por estação.
- `PARFILES/`
  Templates de parfile: `PARFILES/<ESTACAO>_parfile.txt` (usado para validar o parfile gerado).
- `python/rt2ms_py3/`
  Conversor REFTEK binário → miniSEED (via `python3 -m rt2ms_py3.rt2ms_py3`).
- `LOGS/`
  Saída: logs do processo (`*_sync.log`, `*_r2m.log`) e anexos (ex.: `RT130_*.log`).

Saída operacional (por execução):

- `base_dir/<ESTACAO>_<YYYYMMDD>/` (diretório de trabalho da sincronização)
- `base_dir/<ESTACAO>_<YYYYMMDD>/sds/` (SDS gerada localmente antes do `workthisout`)

---

## 2) Execução: modo interativo e modo por flags

### Modo interativo
Ao executar sem argumentos, o script lista combinações **Projeto/Estação** e o usuário escolhe um item. O script determina:

- `project_code` (código de rede SDS: `BC`, `BL`, `IT`, `MC`, `SP`)
- `das_code` (DAS/serial ou código de origem)
- `station_type` (`reftek` ou `raspberry`)

### Modo por flags
Também é possível executar diretamente com:

- `-p "PROJETO"` e `-e "ESTACAO"` para pular o menu
- `-y ANO` para forçar o ano usado ao buscar o último sincronizado na SDS
- `-f` para forçar a sincronização (ignora último dia sincronizado)

---

## 3) Determinar o “último dia sincronizado” na SDS

O script precisa saber **a partir de qual dia** deve procurar dados novos no pacote.

Regra padrão (sem `-y` e sem `-f`):

1. tenta ano atual (`date +%Y`)
2. se não houver SDS, tenta ano anterior

A busca é feita no caminho:

- `/SDS/<ANO>/<project_code>/<ESTACAO>/HHZ.D/`

O “último dia” é obtido a partir do sufixo `JJJ` dos arquivos `*.D.<YYYY>.<JJJ>`.

Modos especiais:

- `-f` (força): define `ultimo_sinc=0` (ignora SDS - Utilizado para testar o fluxo de sincronização em uma coleta já sincronizada)
- `-y ANO`: obriga a busca do último sincronizado no ano informado (Era utilizado quando a busca não tentava ano anterior, hoje não é tão necessário)

---

## 4) Seleção automática do pacote (arquivo compactado)

O script varre `ZIP/<ESTACAO>/` e avalia cada arquivo compactado suportado:

- `.zip`
- `.zip.bz2` (é descompactado para cache em `_ARCHIVE_CACHE/`)
- `.rar`
- `.tar`

Para cada arquivo, ele lista as **datas internas** disponíveis e decide se há dados **≥ ultimo_sinc**.

### Raspberry Shake (interno do ZIP)
Busca paths como:

- `/data/archive/<YYYY>/AM/<das_code>/EH[ZEN].D/...`

Dessas entradas extrai pares `YYYYJJJ` (ano + dia juliano).

### REFTEK (interno do ZIP/RAR/TAR)
Procura por pastas no padrão:

- `YYYYJJJ/<DAS_CODE>/0` e `YYYYJJJ/<DAS_CODE>/1`

Suporta `das_code` com múltiplos códigos (ex.: `"AD20 9789"`), construindo um `code_pattern`.

### Critério de escolha do “closest”
O pacote escolhido é aquele cujo **primeiro dia novo** (≥ `ultimo_sinc`) tem o menor “diff” em relação ao último sincronizado.
Em empate, prefere o arquivo com **maior último dia** disponível.

Ao final, o script imprime:

- arquivo escolhido
- primeiro dia (YYYYJJJ + data gregoriana)
- último dia (YYYYJJJ + data gregoriana)

---

## 5) Processamento e publicação no SDS

A execução bifurca por `station_type`.

### 5.1) REFTEK (RT130)

#### (A) Atalho: ZIP já contém `/sds/`
Se o arquivo compactado já contém miniSEED/SDS (paths com `/sds/`), o script:

1. extrai os miniSEED em `target_dir/<ESTACAO>_<YYYYMMDD>_MSEED/`
2. publica via `dataselect` para `target_dir/sds/`
3. executa `sdsClone.py` e `workthisout.sh`

Esse caminho pula a conversão binária.

#### (B) Fluxo padrão (binário → miniSEED → SDS)
Quando o pacote contém binários:

1. Extrai o pacote para `target_dir`
2. Move somente o conteúdo a partir de `YYYYJJJ/DAS_CODE/` para:
   - `binary_dir = <ESTACAO>_<YYYYMMDD>_BINARIES/`
3. Checagem de integridade horária:
   - varre diretórios `*/<DAS_CODE>/1/` e verifica se há **24 arquivos** (uma hora por arquivo)
   - bordas (primeiro/último dia da coleta) são tratadas separadamente
4. Extrai e ordena informações:
   - GPS e bateria a partir de arquivos em `*/<DAS_CODE>/0/*`
   - gera `<ESTACAO>_<YYYYMMDD>.gps` e `<ESTACAO>_<YYYYMMDD>.battery`
5. Conversão para miniSEED (rt2ms_py3):
   - roda modo exploratório (`-e`) para gerar `parfile.txt` e `rt2ms.msg`
   - resume substituições automáticas detectadas em `rt2ms.msg` (netcode/canal)
6. Validação de `parfile.txt`:
   - compara com `PARFILES/<ESTACAO>_parfile.txt` (tolerâncias controladas; ex.: HHN↔HH1, HHE↔HH2)
7. Conversão final e publicação:
   - gera `<NET>.<ESTACAO>.MSEED/`
   - executa `dataselect` + `sdsClone.py` + `workthisout.sh`

### 5.2) Raspberry Shake

1. Lista no ZIP apenas arquivos com dia **≥ ultimo_sinc**
2. Extrai miniSEED para `MSEED_DIR`
3. Renomeia canais `EHZ/EHN/EHE` → `HHZ/HHN/HHE` e ajusta header com `msmod`
4. Publica no SDS com:
   - `dataselect` → `target_dir/sds/`
   - `sdsClone.py`
   - `workthisout.sh`

---

## 6) Logs e rastreabilidade

No início, o script abre um log em `LOGS/test.log` e redireciona stdout/stderr para o log.

Ao final, ele consolida informações e renomeia o log para:

- `LOGS/<ESTACAO>_<YYYYMMDD>_<HHMM>_sync.log`

No log final também entram:

- MD5 do arquivo de entrada (pacote escolhido)
- tamanho do pacote
- tamanho do `target_dir/sds`

Além disso:

- move `RT130_*.log` gerados durante o processo para `LOGS/` com o mesmo prefixo do `_sync.log`
- renomeia o log do dataselect/rt2ms (quando existir) para `*_r2m.log`

---

## 7) Próximos detalhes

Os detalhes específicos de cada tipo de estação ficam nas páginas:

- Fluxo REFTEK (RT130)
- Fluxo Raspberry Shake
