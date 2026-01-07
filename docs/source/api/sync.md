# SYNC.sh — API/Reference

Esta seção descreve os principais blocos e funções do `SYNC.sh`, com links bidirecionais para o código-fonte renderizado.

(api-sync-strict-mode)=
## Modo estrito (`set -euo pipefail`)
[{ref}`source <src-sync-strict-mode>`] | [{ref}`docs <sync-strict-mode>`]
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-MAIN-STRICT-MODE"
:end-before: "DOC-END: SYNC-MAIN-STRICT-MODE"
:language: bash
:caption: Modo estrito do shell
:id: api-sync-strict-mode
```

(api-sync-run-cmd)=
## run_cmd
[{ref}`source <src-sync-run-cmd>`] | [{ref}`docs <sync-run-cmd>`]
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-run_cmd"
:end-before: "DOC-END: SYNC-FUNC-run_cmd"
:language: bash
:caption: Função run_cmd
:id: api-sync-run-cmd
```

(api-sync-station-lists)=
## Listas de estações
[{ref}`source <src-sync-station-lists>`] | [{ref}`docs <sync-station-lists>`]
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-DATA-STATION-LISTS"
:end-before: "DOC-END: SYNC-DATA-STATION-LISTS"
:language: bash
:caption: Listas de estações
:id: api-sync-station-lists
```

(api-sync-das-codes)=
## das_codes
[{ref}`source <src-sync-das-codes>`] | [{ref}`docs <sync-das-codes>`]
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-DATA-DAS-CODES"
:end-before: "DOC-END: SYNC-DATA-DAS-CODES"
:language: bash
:caption: Mapa de DAS codes
:id: api-sync-das-codes
```

(api-sync-projects)=
## projects
[{ref}`source <src-sync-projects>`] | [{ref}`docs <sync-projects>`]
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-DATA-PROJECTS"
:end-before: "DOC-END: SYNC-DATA-PROJECTS"
:language: bash
:caption: Lista de projetos
:id: api-sync-projects
```

(api-sync-project-map)=
## project_map
[{ref}`source <src-sync-project-map>`] | [{ref}`docs <sync-project-map>`]
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-DATA-PROJECT-MAP"
:end-before: "DOC-END: SYNC-DATA-PROJECT-MAP"
:language: bash
:caption: Mapa de projetos
:id: api-sync-project-map
```

(api-sync-globals)=
## Globais inicializadas
[{ref}`source <src-sync-globals>`] | [{ref}`docs <sync-globals>`]
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-INVAR-GLOBALS"
:end-before: "DOC-END: SYNC-INVAR-GLOBALS"
:language: bash
:caption: Globais inicializadas
:id: api-sync-globals
```

(api-sync-build-code-pattern)=
## build_code_pattern
[{ref}`source <src-sync-build-code-pattern>`] | [{ref}`docs <sync-build-code-pattern>`]
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-build_code_pattern"
:end-before: "DOC-END: SYNC-FUNC-build_code_pattern"
:language: bash
:caption: build_code_pattern
:id: api-sync-build-code-pattern
```

(api-sync-split-das-codes)=
## split_das_codes
[{ref}`source <src-sync-split-das-codes>`] | [{ref}`docs <sync-split-das-codes>`]
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-split_das_codes"
:end-before: "DOC-END: SYNC-FUNC-split_das_codes"
:language: bash
:caption: split_das_codes
:id: api-sync-split-das-codes
```

(api-sync-log-debug)=
## log_debug
[{ref}`source <src-sync-log-debug>`] | [{ref}`docs <sync-log-debug>`]
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-log_debug"
:end-before: "DOC-END: SYNC-FUNC-log_debug"
:language: bash
:caption: log_debug
:id: api-sync-log-debug
```

(api-sync-dia-juliano)=
## dia_juliano
[{ref}`source <src-sync-dia-juliano>`] | [{ref}`docs <sync-dia-juliano>`]
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-dia_juliano"
:end-before: "DOC-END: SYNC-FUNC-dia_juliano"
:language: bash
:caption: dia_juliano
:id: api-sync-dia-juliano
```

(api-sync-is-station-in-list)=
## is_station_in_list
[{ref}`source <src-sync-is-station-in-list>`] | [{ref}`docs <sync-is-station-in-list>`]
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-is_station_in_list"
:end-before: "DOC-END: SYNC-FUNC-is_station_in_list"
:language: bash
:caption: is_station_in_list
:id: api-sync-is-station-in-list
```

(api-sync-seleciona-projeto)=
## seleciona_projeto_estacao
[{ref}`source <src-sync-seleciona-projeto>`] | [{ref}`docs <sync-seleciona-projeto>`]
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-seleciona_projeto_estacao"
:end-before: "DOC-END: SYNC-FUNC-seleciona_projeto_estacao"
:language: bash
:caption: seleciona_projeto_estacao
:id: api-sync-seleciona-projeto
```

(api-sync-obter-ultimo-sinc)=
## obter_ultimo_sinc
[{ref}`source <src-sync-obter-ultimo-sinc>`] | [{ref}`docs <sync-obter-ultimo-sinc>`]
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-obter_ultimo_sinc"
:end-before: "DOC-END: SYNC-FUNC-obter_ultimo_sinc"
:language: bash
:caption: obter_ultimo_sinc
:id: api-sync-obter-ultimo-sinc
```

(api-sync-prepare-archive)=
## prepare_archive
[{ref}`source <src-sync-prepare-archive>`] | [{ref}`docs <sync-prepare-archive>`]
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-prepare_archive"
:end-before: "DOC-END: SYNC-FUNC-prepare_archive"
:language: bash
:caption: prepare_archive
:id: api-sync-prepare-archive
```

(api-sync-list-archive-paths)=
## list_archive_paths
[{ref}`source <src-sync-list-archive-paths>`] | [{ref}`docs <sync-list-archive-paths>`]
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-list_archive_paths"
:end-before: "DOC-END: SYNC-FUNC-list_archive_paths"
:language: bash
:caption: list_archive_paths
:id: api-sync-list-archive-paths
```

(api-sync-extract-dates-rasp)=
## extract_dates_from_rasp
[{ref}`source <src-sync-extract-dates-rasp>`] | [{ref}`docs <sync-extract-dates-rasp>`]
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-extract_dates_from_rasp"
:end-before: "DOC-END: SYNC-FUNC-extract_dates_from_rasp"
:language: bash
:caption: extract_dates_from_rasp
:id: api-sync-extract-dates-rasp
```

(api-sync-extract-reftek-dates)=
## extract_reftek_dates_any_depth
[{ref}`source <src-sync-extract-reftek-dates>`] | [{ref}`docs <sync-extract-reftek-dates>`]
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-extract_reftek_dates_any_depth"
:end-before: "DOC-END: SYNC-FUNC-extract_reftek_dates_any_depth"
:language: bash
:caption: extract_reftek_dates_any_depth
:id: api-sync-extract-reftek-dates
```

(api-sync-encontrar-closest-zip)=
## encontrar_closest_zip
[{ref}`source <src-sync-encontrar-closest-zip>`] | [{ref}`docs <sync-encontrar-closest-zip>`]
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-encontrar_closest_zip"
:end-before: "DOC-END: SYNC-FUNC-encontrar_closest_zip"
:language: bash
:caption: encontrar_closest_zip
:id: api-sync-encontrar-closest-zip
```

(api-sync-comparar-parfiles)=
## comparar_parfiles_com_tolerancia
[{ref}`source <src-sync-comparar-parfiles>`] | [{ref}`docs <sync-comparar-parfiles>`]
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-comparar_parfiles_com_tolerancia"
:end-before: "DOC-END: SYNC-FUNC-comparar_parfiles_com_tolerancia"
:language: bash
:caption: comparar_parfiles_com_tolerancia
:id: api-sync-comparar-parfiles
```

(api-sync-resumir-parfiles)=
## resumir_auto_substituicoes_parfile
[{ref}`source <src-sync-resumir-parfiles>`] | [{ref}`docs <sync-resumir-parfiles>`]
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-resumir_auto_substituicoes_parfile"
:end-before: "DOC-END: SYNC-FUNC-resumir_auto_substituicoes_parfile"
:language: bash
:caption: resumir_auto_substituicoes_parfile
:id: api-sync-resumir-parfiles
```

(api-sync-find-reftek-dirs-stream1)=
## find_reftek_dirs_stream1
[{ref}`source <src-sync-find-reftek-dirs-stream1>`] | [{ref}`docs <sync-find-reftek-dirs-stream1>`]
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-find_reftek_dirs_stream1"
:end-before: "DOC-END: SYNC-FUNC-find_reftek_dirs_stream1"
:language: bash
:caption: find_reftek_dirs_stream1
:id: api-sync-find-reftek-dirs-stream1
```

(api-sync-find-reftek-files-stream0)=
## find_reftek_files_stream0
[{ref}`source <src-sync-find-reftek-files-stream0>`] | [{ref}`docs <sync-find-reftek-files-stream0>`]
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-find_reftek_files_stream0"
:end-before: "DOC-END: SYNC-FUNC-find_reftek_files_stream0"
:language: bash
:caption: find_reftek_files_stream0
:id: api-sync-find-reftek-files-stream0
```

(api-sync-processar-reftek)=
## processar_reftek
[{ref}`source <src-sync-processar-reftek>`] | [{ref}`docs <sync-processar-reftek>`]
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-processar_reftek"
:end-before: "DOC-END: SYNC-FUNC-processar_reftek"
:language: bash
:caption: processar_reftek
:id: api-sync-processar-reftek
```

(api-sync-processar-raspberry)=
## processar_raspberry
[{ref}`source <src-sync-processar-raspberry>`] | [{ref}`docs <sync-processar-raspberry>`]
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-processar_raspberry"
:end-before: "DOC-END: SYNC-FUNC-processar_raspberry"
:language: bash
:caption: processar_raspberry
:id: api-sync-processar-raspberry
```

(api-sync-finalizar-log)=
## finalizar_log
[{ref}`source <src-sync-finalizar-log>`] | [{ref}`docs <sync-finalizar-log>`]
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-FUNC-finalizar_log"
:end-before: "DOC-END: SYNC-FUNC-finalizar_log"
:language: bash
:caption: finalizar_log
:id: api-sync-finalizar-log
```

(api-sync-config-logging)=
## Configuração de log
[{ref}`source <src-sync-config-logging>`] | [{ref}`docs <sync-config-logging>`]
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-MAIN-CONFIG-LOGGING"
:end-before: "DOC-END: SYNC-MAIN-CONFIG-LOGGING"
:language: bash
:caption: Configuração de diretórios e log
:id: api-sync-config-logging
```

(api-sync-cli-usage)=
## CLI usage
[{ref}`source <src-sync-cli-usage>`] | [{ref}`docs <sync-cli-usage>`]
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-MAIN-CLI-USAGE"
:end-before: "DOC-END: SYNC-MAIN-CLI-USAGE"
:language: bash
:caption: CLI usage
:id: api-sync-cli-usage
```

(api-sync-cli-getopts)=
## CLI getopts
[{ref}`source <src-sync-cli-getopts>`] | [{ref}`docs <sync-cli-getopts>`]
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-MAIN-CLI-GETOPTS"
:end-before: "DOC-END: SYNC-MAIN-CLI-GETOPTS"
:language: bash
:caption: CLI getopts
:id: api-sync-cli-getopts
```

(api-sync-select-context)=
## Seleção do contexto
[{ref}`source <src-sync-select-context>`] | [{ref}`docs <sync-select-context>`]
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-MAIN-SELECT-CONTEXT"
:end-before: "DOC-END: SYNC-MAIN-SELECT-CONTEXT"
:language: bash
:caption: Seleção do contexto
:id: api-sync-select-context
```

(api-sync-ano-forcado)=
## Ano forçado
[{ref}`source <src-sync-ano-forcado>`] | [{ref}`docs <sync-ano-forcado>`]
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-MAIN-ANO-FORCADO"
:end-before: "DOC-END: SYNC-MAIN-ANO-FORCADO"
:language: bash
:caption: Ano forçado
:id: api-sync-ano-forcado
```

(api-sync-auto-selection)=
## Seleção automática
[{ref}`source <src-sync-auto-selection>`] | [{ref}`docs <sync-auto-selection>`]
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-MAIN-AUTO-SELECTION"
:end-before: "DOC-END: SYNC-MAIN-AUTO-SELECTION"
:language: bash
:caption: Seleção automática
:id: api-sync-auto-selection
```

(api-sync-reftek-shortcut)=
## Atalho REFTEK /sds
[{ref}`source <src-sync-reftek-shortcut>`] | [{ref}`docs <sync-reftek-shortcut>`]
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-MAIN-REFTEK-SDS-SHORTCUT"
:end-before: "DOC-END: SYNC-MAIN-REFTEK-SDS-SHORTCUT"
:language: bash
:caption: Atalho REFTEK com SDS
:id: api-sync-reftek-shortcut
```

(api-sync-dispatch)=
## Dispatch final
[{ref}`source <src-sync-dispatch>`] | [{ref}`docs <sync-dispatch>`]
```{literalinclude} ../../../SYNC.sh
:start-after: "DOC-SECTION: SYNC-MAIN-DISPATCH"
:end-before: "DOC-END: SYNC-MAIN-DISPATCH"
:language: bash
:caption: Dispatch final
:id: api-sync-dispatch
```
