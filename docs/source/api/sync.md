# SYNC.sh — API/Reference

Esta seção descreve os principais blocos e funções do `SYNC.sh`, com links bidirecionais para o código-fonte renderizado.

(sync-strict-mode)=
## Modo estrito (`set -euo pipefail`) ([source]{ref}`src-sync-strict-mode`)
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-MAIN-STRICT-MODE"
:end-before: "DOC-END: SYNC-MAIN-STRICT-MODE"
:language: bash
:caption: Modo estrito do shell
:name: api-sync-strict-mode
```

(sync-run-cmd)=
## run_cmd ([source]{ref}`src-sync-run-cmd`)
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-run_cmd"
:end-before: "DOC-END: SYNC-FUNC-run_cmd"
:language: bash
:caption: Função run_cmd
:name: api-sync-run-cmd
```

(sync-station-lists)=
## Listas de estações ([source]{ref}`src-sync-station-lists`)
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-DATA-STATION-LISTS"
:end-before: "DOC-END: SYNC-DATA-STATION-LISTS"
:language: bash
:caption: Listas de estações
:name: api-sync-station-lists
```

(sync-das-codes)=
## das_codes ([source]{ref}`src-sync-das-codes`)
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-DATA-DAS-CODES"
:end-before: "DOC-END: SYNC-DATA-DAS-CODES"
:language: bash
:caption: Mapa de DAS codes
:name: api-sync-das-codes
```

(sync-projects)=
## projects ([source]{ref}`src-sync-projects`)
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-DATA-PROJECTS"
:end-before: "DOC-END: SYNC-DATA-PROJECTS"
:language: bash
:caption: Lista de projetos
:name: api-sync-projects
```

(sync-project-map)=
## project_map ([source]{ref}`src-sync-project-map`)
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-DATA-PROJECT-MAP"
:end-before: "DOC-END: SYNC-DATA-PROJECT-MAP"
:language: bash
:caption: Mapa de projetos
:name: api-sync-project-map
```

(sync-globals)=
## Globais inicializadas ([source]{ref}`src-sync-globals`)
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-INVAR-GLOBALS"
:end-before: "DOC-END: SYNC-INVAR-GLOBALS"
:language: bash
:caption: Globais inicializadas
:name: api-sync-globals
```

(sync-build-code-pattern)=
## build_code_pattern ([source]{ref}`src-sync-build-code-pattern`)
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-build_code_pattern"
:end-before: "DOC-END: SYNC-FUNC-build_code_pattern"
:language: bash
:caption: build_code_pattern
:name: api-sync-build-code-pattern
```

(sync-split-das-codes)=
## split_das_codes ([source]{ref}`src-sync-split-das-codes`)
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-split_das_codes"
:end-before: "DOC-END: SYNC-FUNC-split_das_codes"
:language: bash
:caption: split_das_codes
:name: api-sync-split-das-codes
```

(sync-log-debug)=
## log_debug ([source]{ref}`src-sync-log-debug`)
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-log_debug"
:end-before: "DOC-END: SYNC-FUNC-log_debug"
:language: bash
:caption: log_debug
:name: api-sync-log-debug
```

(sync-dia-juliano)=
## dia_juliano ([source]{ref}`src-sync-dia-juliano`)
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-dia_juliano"
:end-before: "DOC-END: SYNC-FUNC-dia_juliano"
:language: bash
:caption: dia_juliano
:name: api-sync-dia-juliano
```

(sync-is-station-in-list)=
## is_station_in_list ([source]{ref}`src-sync-is-station-in-list`)
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-is_station_in_list"
:end-before: "DOC-END: SYNC-FUNC-is_station_in_list"
:language: bash
:caption: is_station_in_list
:name: api-sync-is-station-in-list
```

(sync-seleciona-projeto)=
## seleciona_projeto_estacao ([source]{ref}`src-sync-seleciona-projeto`)
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-seleciona_projeto_estacao"
:end-before: "DOC-END: SYNC-FUNC-seleciona_projeto_estacao"
:language: bash
:caption: seleciona_projeto_estacao
:name: api-sync-seleciona-projeto
```

(sync-obter-ultimo-sinc)=
## obter_ultimo_sinc ([source]{ref}`src-sync-obter-ultimo-sinc`)
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-obter_ultimo_sinc"
:end-before: "DOC-END: SYNC-FUNC-obter_ultimo_sinc"
:language: bash
:caption: obter_ultimo_sinc
:name: api-sync-obter-ultimo-sinc
```

(sync-prepare-archive)=
## prepare_archive ([source]{ref}`src-sync-prepare-archive`)
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-prepare_archive"
:end-before: "DOC-END: SYNC-FUNC-prepare_archive"
:language: bash
:caption: prepare_archive
:name: api-sync-prepare-archive
```

(sync-list-archive-paths)=
## list_archive_paths ([source]{ref}`src-sync-list-archive-paths`)
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-list_archive_paths"
:end-before: "DOC-END: SYNC-FUNC-list_archive_paths"
:language: bash
:caption: list_archive_paths
:name: api-sync-list-archive-paths
```

(sync-extract-dates-rasp)=
## extract_dates_from_rasp ([source]{ref}`src-sync-extract-dates-rasp`)
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-extract_dates_from_rasp"
:end-before: "DOC-END: SYNC-FUNC-extract_dates_from_rasp"
:language: bash
:caption: extract_dates_from_rasp
:name: api-sync-extract-dates-rasp
```

(sync-extract-reftek-dates)=
## extract_reftek_dates_any_depth ([source]{ref}`src-sync-extract-reftek-dates`)
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-extract_reftek_dates_any_depth"
:end-before: "DOC-END: SYNC-FUNC-extract_reftek_dates_any_depth"
:language: bash
:caption: extract_reftek_dates_any_depth
:name: api-sync-extract-reftek-dates
```

(sync-encontrar-closest-zip)=
## encontrar_closest_zip ([source]{ref}`src-sync-encontrar-closest-zip`)
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-encontrar_closest_zip"
:end-before: "DOC-END: SYNC-FUNC-encontrar_closest_zip"
:language: bash
:caption: encontrar_closest_zip
:name: api-sync-encontrar-closest-zip
```

(sync-comparar-parfiles)=
## comparar_parfiles_com_tolerancia ([source]{ref}`src-sync-comparar-parfiles`)
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-comparar_parfiles_com_tolerancia"
:end-before: "DOC-END: SYNC-FUNC-comparar_parfiles_com_tolerancia"
:language: bash
:caption: comparar_parfiles_com_tolerancia
:name: api-sync-comparar-parfiles
```

(sync-resumir-parfiles)=
## resumir_auto_substituicoes_parfile ([source]{ref}`src-sync-resumir-parfiles`)
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-resumir_auto_substituicoes_parfile"
:end-before: "DOC-END: SYNC-FUNC-resumir_auto_substituicoes_parfile"
:language: bash
:caption: resumir_auto_substituicoes_parfile
:name: api-sync-resumir-parfiles
```

(sync-find-reftek-dirs-stream1)=
## find_reftek_dirs_stream1 ([source]{ref}`src-sync-find-reftek-dirs-stream1`)
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-find_reftek_dirs_stream1"
:end-before: "DOC-END: SYNC-FUNC-find_reftek_dirs_stream1"
:language: bash
:caption: find_reftek_dirs_stream1
:name: api-sync-find-reftek-dirs-stream1
```

(sync-find-reftek-files-stream0)=
## find_reftek_files_stream0 ([source]{ref}`src-sync-find-reftek-files-stream0`)
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-find_reftek_files_stream0"
:end-before: "DOC-END: SYNC-FUNC-find_reftek_files_stream0"
:language: bash
:caption: find_reftek_files_stream0
:name: api-sync-find-reftek-files-stream0
```

(sync-processar-reftek)=
## processar_reftek ([source]{ref}`src-sync-processar-reftek`)
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-processar_reftek"
:end-before: "DOC-END: SYNC-FUNC-processar_reftek"
:language: bash
:caption: processar_reftek
:name: api-sync-processar-reftek
```

(sync-processar-raspberry)=
## processar_raspberry ([source]{ref}`src-sync-processar-raspberry`)
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-processar_raspberry"
:end-before: "DOC-END: SYNC-FUNC-processar_raspberry"
:language: bash
:caption: processar_raspberry
:name: api-sync-processar-raspberry
```

(sync-finalizar-log)=
## finalizar_log ([source]{ref}`src-sync-finalizar-log`)
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-finalizar_log"
:end-before: "DOC-END: SYNC-FUNC-finalizar_log"
:language: bash
:caption: finalizar_log
:name: api-sync-finalizar-log
```

(sync-config-logging)=
## Configuração de log ([source]{ref}`src-sync-config-logging`)
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-MAIN-CONFIG-LOGGING"
:end-before: "DOC-END: SYNC-MAIN-CONFIG-LOGGING"
:language: bash
:caption: Configuração de diretórios e log
:name: api-sync-config-logging
```

(sync-cli-usage)=
## CLI usage ([source]{ref}`src-sync-cli-usage`)
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-MAIN-CLI-USAGE"
:end-before: "DOC-END: SYNC-MAIN-CLI-USAGE"
:language: bash
:caption: CLI usage
:name: api-sync-cli-usage
```

(sync-cli-getopts)=
## CLI getopts ([source]{ref}`src-sync-cli-getopts`)
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-MAIN-CLI-GETOPTS"
:end-before: "DOC-END: SYNC-MAIN-CLI-GETOPTS"
:language: bash
:caption: CLI getopts
:name: api-sync-cli-getopts
```

(sync-select-context)=
## Seleção do contexto ([source]{ref}`src-sync-select-context`)
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-MAIN-SELECT-CONTEXT"
:end-before: "DOC-END: SYNC-MAIN-SELECT-CONTEXT"
:language: bash
:caption: Seleção do contexto
:name: api-sync-select-context
```

(sync-ano-forcado)=
## Ano forçado ([source]{ref}`src-sync-ano-forcado`)
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-MAIN-ANO-FORCADO"
:end-before: "DOC-END: SYNC-MAIN-ANO-FORCADO"
:language: bash
:caption: Ano forçado
:name: api-sync-ano-forcado
```

(sync-auto-selection)=
## Seleção automática ([source]{ref}`src-sync-auto-selection`)
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-MAIN-AUTO-SELECTION"
:end-before: "DOC-END: SYNC-MAIN-AUTO-SELECTION"
:language: bash
:caption: Seleção automática
:name: api-sync-auto-selection
```

(sync-reftek-shortcut)=
## Atalho REFTEK /sds ([source]{ref}`src-sync-reftek-shortcut`)
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-MAIN-REFTEK-SDS-SHORTCUT"
:end-before: "DOC-END: SYNC-MAIN-REFTEK-SDS-SHORTCUT"
:language: bash
:caption: Atalho REFTEK com SDS
:name: api-sync-reftek-shortcut
```

(sync-dispatch)=
## Dispatch final ([source]{ref}`src-sync-dispatch`)
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-MAIN-DISPATCH"
:end-before: "DOC-END: SYNC-MAIN-DISPATCH"
:language: bash
:caption: Dispatch final
:name: api-sync-dispatch
```
