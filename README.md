# README

### 1) Correção conceitual: `YYYYJJJ/<DAS>/<n>/...` (stream n)

Concordo: no RT130 o diretório imediatamente abaixo de `<DAS>` é o **índice de stream** (um inteiro natural). Em termos operacionais, é útil documentar assim:

* `YYYYJJJ/<DAS>/0/...` → **stream 0** (SOH/metadata; é de onde você está extraindo GPS/BATTERY/TEMP).
* `YYYYJJJ/<DAS>/<n>/...` com `n ≥ 1` → **streams de waveform** (contínua e/ou event-driven).

**Impacto direto no código (hoje):**

* `extract_reftek_dates_any_depth()` está hardcoded para aceitar apenas `0` ou `1` como stream:

  ```awk
  ( $(i+2)=="0" || $(i+2)=="1" )
  ```

  Isso “some” com estações multi-stream se a contínua/eventos estiverem em `2`, `3`, etc.

**Ajuste mínimo (sem mudar o restante do algoritmo):** trocar a condição por “qualquer inteiro”:

```diff
- && ( $(i+2)=="0" || $(i+2)=="1" )
+ && ( $(i+2) ~ /^[0-9]+$/ )
```

E na documentação (Visão geral / API / Source), substituir o texto de “`.../1`” por “`.../<n>`”. A PR #6 foi exatamente sobre estabilizar âncoras/IDs e links bidirecionais na doc, então essa atualização fica alinhada com o que já foi padronizado ali. ([GitHub][1])

---

### 2) `-f` (FORCE_SYNC) e o objetivo real: “testar presync sem dados novos”

Pelo que você descreveu, o `-f` não é “forçar sincronização do zero” por motivação de produção; é um **modo de teste** para permitir rodar o pipeline mesmo quando **não existe nenhum arquivo com data > último sincronizado** (ou quando você quer testar com pacote antigo).

No estado atual, `-f` faz `ultimo_sinc=0`, o que:

* evita o erro “nenhum arquivo adequado encontrado” porque o filtro `julian >= ultimo_sinc` passa a aceitar tudo;
* mas altera o critério de escolha do “closest” (o diff passa a ser relativo a 0), e isso pode fazer o script preferir um ZIP “mais antigo” se houver múltiplos.

Em geral, isso sugere separar dois conceitos:

* **referência de merge** (`ultimo_sinc`, para decidir o que é “borda” e para garantir o overlap do dia incompleto)
* **modo de seleção** (permitir escolher um pacote mesmo se ele não tiver datas novas)

Ou seja: você pode manter o merge do último dia (ver item 4) e ainda assim permitir “seleção relaxada” para testes.

---

### 3) Atalho “ZIP já vem em `./sds/`” (PRB1)

Perfeito: no caso do PRB1, o pacote já vem convertido para miniSEED em layout SDS, então a decisão correta é **extrair e publicar**, pulando o tratamento REFTEK/rt2ms.

O mecanismo atual (“se existir `/sds/` dentro do ZIP”) é pragmático. Se quiser endurecer para evitar falso-positivo, o caminho usual é checar se:

* existem entradas começando em `sds/` (não apenas contendo a substring),
* e se os nomes batem um padrão SDS (`NET.STA..CHA.D.YYYY.JJJ` etc.).

---

### 4) A questão do `-p "$par_template"`: qual o problema técnico?

O problema não é “usar template” em si; o problema é **consistência entre as decisões do script**:

1. Você roda `rt2ms_py3 ... -e` (exploratório) e obtém um `parfile.txt` **derivado do dado bruto**.
2. Você valida `parfile.txt` contra um template **se existir**.
3. **Mesmo quando o template não existe**, o script segue para a conversão final usando `-p "$par_template"`.

Isso cria um cenário incoerente:

* **Template ausente**: o script diz “prosseguindo sem validação”, mas a conversão final tende a falhar porque `-p` aponta para um arquivo inexistente (e com `set -e`, isso aborta). Ou seja: “avisa e continua”, mas na prática “continua para falhar”.
* **Multi-stream**: sua função de comparação ignora `refstrm != 1`. Então você pode estar validando apenas a stream contínua, mas o template pode estar incompleto/errado para streams `2/3` — e a conversão final usará esse template mesmo assim.

O caminho “estável” é definir qual parfile é **fonte de verdade**:

* Se existe template e ele cobre o que você quer publicar → use template.
* Se não existe template → use o `parfile.txt` gerado no exploratório como fallback na conversão final (e registre isso no log).

---

### 5) Overlap (“merge”) do último dia com a nova coleta

Manter `>= ultimo_sinc` faz sentido no seu contexto: o último dia na SDS pode estar **incompleto** e a nova coleta completa esse dia. Esse é um requisito de qualidade do dataset.

O ponto que precisa estar garantido (pela ferramenta de publicação/organização) é: **reprocessar o mesmo dia não pode introduzir duplicatas irrecuperáveis**. Se `workthisout.sh`/pipeline SDS já trata deduplicação/compactação corretamente, então o overlap é uma escolha correta.

---

### Uma decisão para destravar a refatoração de streams (1 pergunta)

Para BC4 e BC9: a **stream contínua** é sempre `1`, e as streams “local” e “regional” são tipicamente `2` e `3` (ou isso varia por estação)?

[1]: https://github.com/Gabriel-Goes/Pre-Sync/pull/6 "Refine documentation cross-links and add Furo theme options by Gabriel-Goes · Pull Request #6 · Gabriel-Goes/Pre-Sync · GitHub"

## RT130 Logger

### Parametros observados no arquivo:
    SH = State of Health
    SC = Station Channel Definition
    OM = Operating Mode Definition
    DS = Data Stream Definition
    AD = Auxiliary Data Parameter
    CD = Calibration Definition
    FD = Filter Description
    EH = Event Header
    ET = Event Trailer

