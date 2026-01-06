# Guia rápido

Este guia cobre o essencial para **sincronizar** dados (REFTEK RT130 ou Raspberry Shake) e **publicar em SDS** usando o `SYNC.sh`.

## 1) Pré-requisitos

- Você deve ter acesso de leitura/escrita ao SDS no caminho esperado pelo pipeline:
  - `/SDS/<ANO>/<REDE>/<ESTACAO>/...`
- O projeto deve estar no diretório padrão:
  - `~/TMP/SYNC`

Verificações rápidas:
~~~bash
cd ~/TMP/SYNC
test -d /SDS || echo "ERRO: /SDS não encontrado (SDS não montado?)"
~~~

## 2) Preparar arquivos de entrada (RAW)

Coloque o arquivo bruto na pasta da estação:

- Entrada esperada:
  - `~/TMP/SYNC/ZIP/<ESTACAO>/<arquivo>`

Exemplo (BC9):
~~~bash
mkdir -p ~/TMP/SYNC/ZIP/BC9
# copie o arquivo para dentro (ex.: scp, mv, rsync)
ls -lh ~/TMP/SYNC/ZIP/BC9
~~~

Formatos suportados pelo fluxo: `.zip`, `.zip.bz2`, `.rar`, `.tar` (dependendo da estação/origem).

## 3) Executar sincronização (modo interativo)

O modo interativo apresenta o menu de projetos/estações:
~~~bash
cd ~/TMP/SYNC
./SYNC.sh
~~~

## 4) Acompanhar logs e validar publicação

### 4.1) Listar os 10 logs mais recentes (somente `_sync.log`)
~~~bash
cd ~/TMP/SYNC
ls -1t LOGS/*_sync.log | head -n 10
~~~

### 4.2) Abrir o log mais recente
~~~bash
cd ~/TMP/SYNC
latest="$(ls -1t LOGS/*_sync.log | head -n 1)"
less "$latest"
~~~

### 4.3) Verificar último dia publicado no SDS (exemplo BC9)
A rede do projeto é resolvida internamente (ex.: `"BAESA ENERCAN"` → `BC`), então o destino fica em:
`/SDS/<ANO>/<REDE>/<ESTACAO>/HHZ.D/`

Exemplo:
~~~bash
ls -1 /SDS/2025/BC/BC9/HHZ.D | tail -n 5
~~~

Observação operacional:
- O `_sync.log` registra claramente:
  - último dia detectado na SDS (ex.: `Último dia sincronizado...: 300`)
  - arquivo bruto selecionado
  - período processado (`closest_date` / `last_date`)
  - execução de merge (sdsClone/workthisout)
  - eventuais alertas de integridade (ex.: “BORDA DE COLETA”, “ARQUIVOS INCOMPLETOS”).

## 5) Verificar o último dado na SDS (utilitário `ag`)

O `ag` é um utilitário de verificação rápida da **SDS**. Ele percorre `/SDS/<ANO>/` e, para cada **rede → estação**, identifica o **último dia (JJJ) disponível** e executa um resumo do arquivo miniSEED correspondente usando `msi -tg`. Isso permite checar rapidamente se a estação está com dados recentes e se o traço do último dia está consistente (intervalo temporal, taxa de amostragem e possíveis gaps/segmentos).

### Uso rápido

Rodar `ag` sem opções usa o **último ano disponível** em `/SDS/` e imprime um resumo por estação:

~~~bash
> ag
Rede: BC
-----------
Estação: BC4
 -> BC.BC4..HHZ.D.2026.005
    |    Source                Start sample             End sample        Gap  Hz  Samples
    | BC_BC4__HHZ       2026,005,00:00:00.000000 2026,005,17:13:45.610000  ==  100 6202562
    | Total: 1 trace(s) with 1 segment(s)
--------------------------------------------
~~~

Para consultar um ano específico (ex.: 2025):

~~~bash
> ag -y 2025
Rede: BC
-----------
Estação: BC4
 -> BC.BC4..HHZ.D.2025.365
    |    Source                Start sample             End sample        Gap  Hz  Samples
    | BC_BC4__HHZ       2025,365,00:00:00.000000 2025,365,23:59:59.990000  ==  100 8640000
    | Total: 1 trace(s) with 1 segment(s)
Estação: BC9
 -> BC.BC9..HHZ.D.2025.345
    |    Source                Start sample             End sample        Gap  Hz  Samples
    | BC_BC9__HHZ       2025,345,00:00:00.005000 2025,345,17:32:29.605000  ==  100 6314961
    | Total: 1 trace(s) with 1 segment(s)
--------------------------------------------
Rede: BL
-----------
Estação: PRB1
 -> BL.PRB1..HHZ.D.2025.336
    |    Source                Start sample             End sample        Gap  Hz  Samples
    | BL_PRB1__HHZ      2025,336,00:00:00.000000 2025,336,09:46:34.575000  ==  200 7038916
    | BL_PRB1__HHZ      2025,336,10:08:52.970000 2025,336,16:10:51.670000 1338 200 4343741
    | Total: 1 trace(s) with 2 segment(s)
--------------------------------------------
Rede: IT
-----------
Estação: IT1
 -> IT.IT1..HHZ.D.2025.184
    |    Source                Start sample             End sample        Gap  Hz  Samples
    | IT_IT1__HHZ       2025,184,00:00:00.000000 2025,184,20:32:04.850000  ==  200 14784971
    | Total: 1 trace(s) with 1 segment(s)
Estação: IT9
 -> IT.IT9..HHZ.D.2025.213
    |    Source                Start sample             End sample        Gap  Hz  Samples
    | IT_IT9__HHZ       2025,213,00:00:00.000000 2025,213,00:00:00.140000  ==  100 15
    | Total: 1 trace(s) with 1 segment(s)
--------------------------------------------
Rede: MC
-----------
Estação: BCM2
 -> MC.BCM2..HHZ.D.2025.212
    |    Source                Start sample             End sample        Gap  Hz  Samples
    | MC_BCM2__HHZ      2025,212,00:00:00.000000 2025,212,13:57:00.850000  ==  200 10044171
    | Total: 1 trace(s) with 1 segment(s)
Estação: MC9
 -> MC.MC9..HHZ.D.2025.212
    |    Source                Start sample             End sample        Gap  Hz  Samples
    | MC_MC9__HHZ       2025,212,00:00:00.007999 2025,212,16:39:32.847999  ==  100 5997285
    | Total: 1 trace(s) with 1 segment(s)
--------------------------------------------
Rede: SP
-----------
Estação: SP7
 -> SP.SP7..HHZ.D.2025.357
    |    Source                Start sample             End sample        Gap  Hz  Samples
    | SP_SP7__HHZ       2025,357,00:00:00.005000 2025,357,18:14:21.605000  ==  100 6566161
    | Total: 1 trace(s) with 1 segment(s)
--------------------------------------------
~~~
