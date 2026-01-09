#!/usr/bin/env bash
#
# Fluxo principal de sincronização com suporte a flags
# Desenvolvido por: Gabriel Góes Rocha de Lima
# Versão 0.1.0 11 de Dezembro 2025
#
# Para executar:
#   - Colocar o arquivo compactado na pasta /ZIP/STA/<arquivo>
#   - Executar ./SYNC.sh
#   - Escolher a estação e aguardar
#
# Resultado em: /var/WORKTMP/SYNC/ (aqui: $HOME/TMP/SYNC)
#
# DOC-SECTION: SYNC-MAIN-STRICT-MODE
set -euo pipefail
# DOC-END: SYNC-MAIN-STRICT-MODE

# Você pode executar forçadamente o processo com -f (FORCE_SYNC=1)
FORCE_SYNC=0
DEBUG_TRACE=0

################################################################################
#                            FUNÇÃO AUXILIAR                                    #
################################################################################
# run_cmd: executa um comando e, se falhar, registra no log e retorna o código.
# (compatível com set -e)
# DOC-SECTION: SYNC-FUNC-run_cmd
run_cmd() {
    local cmd=("$@")
    if "${cmd[@]}"; then
        return 0
    fi
    local status=$?
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [ERROR] Comando '${cmd[*]}' retornou $status." | tee -a "$log_file" >&2
    return $status
}
# DOC-END: SYNC-FUNC-run_cmd

########################## ARRAYS E DICIONÁRIOS ################################
# DOC-SECTION: SYNC-DATA-STATION-LISTS
declare -a reftek_stations=(PRB1 BC9 BC4 BCM2 SP7 IT1)
declare -a raspberry_stations=(MC9 IT9)
# DOC-END: SYNC-DATA-STATION-LISTS

# DOC-SECTION: SYNC-DATA-DAS-CODES
declare -A das_codes=(
    [BCM2]=AD19
    [PRB1]="AD20"   # suporte a múltiplos códigos: basta separar por espaço (ex: "AD20 9789")
    [BC9]=9690
    [SP7]=9FD3
    [IT1]=B438
    [BC4]=9775
    [MC9]=REDD8
    [IT9]=REDD8
# DOC-END: SYNC-DATA-DAS-CODES
)

# DOC-SECTION: SYNC-DATA-PROJECTS
declare -A projects=(
    [1]="BAESA ENERCAN|BC4"
    [2]="BAESA ENERCAN|BC9"
    [3]="PARAIBUNA|PRB1"
    [4]="ITA|IT9"
    [5]="ITA|IT1"
    [6]="MACHADINHO|BCM2"
    [7]="MACHADINHO|MC9"
    [8]="SALTO PILAO|SP7"
# DOC-END: SYNC-DATA-PROJECTS
)

# DOC-SECTION: SYNC-DATA-PROJECT-MAP
declare -A project_map=(
    ["BAESA ENERCAN"]=BC
    [PARAIBUNA]=BL
    [ITA]=IT
    [MACHADINHO]=MC
    [SALTO PILAO]=SP
# DOC-END: SYNC-DATA-PROJECT-MAP
)

################################################################################
# Globais (definidos para não quebrar com set -u)
################################################################################
# DOC-SECTION: SYNC-INVAR-GLOBALS
PROJETO_ESCOLHIDO=""
ESTACAO_ESCOLHIDA=""
ANO_FORCADO=""

project_code=""
das_code=""
origin_dir=""
station_type=""

# IMPORTANTE: manter sempre definido (mesmo que vazio) para não quebrar com set -u
code_pattern=""

closest_zip=""
closest_zip_orig=""
closest_date=""
last_date=""
closest_streams_info=()
ultimo_sinc=""
ano_sinc=""
# DOC-END: SYNC-INVAR-GLOBALS

################################################################################
# Helpers para DAS_CODE múltiplo
################################################################################
# DOC-SECTION: SYNC-FUNC-build_code_pattern
build_code_pattern() {
    local dc="$1"
    local -a codes
    IFS=' ' read -r -a codes <<< "$dc"

    local pat=""
    local c
    for c in "${codes[@]}"; do
        [[ -n "$c" ]] && pat+="${pat:+|}$c"
    done
    printf '%s' "$pat"
}
# DOC-END: SYNC-FUNC-build_code_pattern

# Retorna codes em array global (por conveniência local)
# DOC-SECTION: SYNC-FUNC-split_das_codes
split_das_codes() {
    local dc="$1"
    IFS=' ' read -r -a _CODES_SPLIT <<< "$dc"
}
# DOC-END: SYNC-FUNC-split_das_codes

################################################################################
######################### FUNÇÕES DE UTILIDADE #################################
################################################################################
# DOC-SECTION: SYNC-FUNC-log_debug
function log_debug() { [[ "${VERBOSE:-0}" -eq 1 ]] && echo "[DEBUG] $*"; }
# DOC-END: SYNC-FUNC-log_debug

# DOC-SECTION: SYNC-FUNC-dia_juliano
function dia_juliano() { date -d "$1" +%j; }
# DOC-END: SYNC-FUNC-dia_juliano

# DOC-SECTION: SYNC-FUNC-is_station_in_list
function is_station_in_list() {
    local station="$1"; shift
    local e
    for e in "$@"; do
        [[ "$e" == "$station" ]] && return 0
    done
    return 1
}
# DOC-END: SYNC-FUNC-is_station_in_list

################################################################################
########################## FUNÇÃO DE SELEÇÃO ####################################
################################################################################
# DOC-SECTION: SYNC-FUNC-seleciona_projeto_estacao
function seleciona_projeto_estacao() {
    echo
    echo "→ Selecione o Projeto e Estação:"
    for key in "${!projects[@]}"; do
        IFS='|' read -r p e <<< "${projects[$key]}"
        printf "   %2s) Projeto: %-15s | Estação: %-4s\n" "$key" "$p" "$e"
    done

    read -rp $'\nDigite o número correspondente: ' escolha
    if [[ -z "${projects[$escolha]:-}" ]]; then
        echo "[ERRO] Seleção inválida. Abortando." >&2
        exit 1
    fi

    IFS='|' read -r PROJETO_ESCOLHIDO ESTACAO_ESCOLHIDA <<< "${projects[$escolha]}"
    project_code="${project_map[$PROJETO_ESCOLHIDO]}"
    das_code="${das_codes[$ESTACAO_ESCOLHIDA]}"
    origin_dir="$base_dir/ZIP/$ESTACAO_ESCOLHIDA"

    # >>> FIX CRÍTICO: code_pattern sempre definido aqui
    code_pattern="$(build_code_pattern "$das_code")"
    [[ -n "$code_pattern" ]] || { echo "[ERRO] code_pattern vazio para das_code='$das_code'"; exit 1; }

    if is_station_in_list "$ESTACAO_ESCOLHIDA" "${reftek_stations[@]}"; then
        station_type="reftek"
        echo "→ Estação $ESTACAO_ESCOLHIDA ($das_code) é do tipo Reftek."
    elif is_station_in_list "$ESTACAO_ESCOLHIDA" "${raspberry_stations[@]}"; then
        station_type="raspberry"
        echo "→ Estação $ESTACAO_ESCOLHIDA ($das_code) é do tipo Raspberry Shake."
    else
        echo "[ERRO] Estação '$ESTACAO_ESCOLHIDA' não reconhecida. Abortando." >&2
        exit 1
    fi
}
# DOC-END: SYNC-FUNC-seleciona_projeto_estacao

################################################################################
########################### BUSCA ÚLTIMO SINCRONIZADO ###########################
################################################################################
# DOC-SECTION: SYNC-FUNC-obter_ultimo_sinc
function obter_ultimo_sinc() {
    if [[ "$FORCE_SYNC" -eq 1 ]]; then
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] [FORCE] Sincronização forçada: ignorando último dia na SDS."
        ano_sinc="$(date +%Y)"
        ultimo_sinc=0
        echo "→ Sincronização forçada ativa: definido ultimo_sinc=0"
        return
    fi

    local ano_atual
    ano_atual="$(date +%Y)"
    local tentativas=( "$ano_atual" "$((ano_atual - 1))" )
    local encontrado=""

    local ano
    for ano in "${tentativas[@]}"; do
        local sds_dir="/SDS/$ano/$project_code/$ESTACAO_ESCOLHIDA/HHZ.D"
        if [[ -d "$sds_dir" ]]; then
            local last_file
            last_file=$(
                ls -1 "$sds_dir" \
                  | awk -F'.' '{print $NF}' \
                  | sort -u \
                  | tail -n1
            )
            if [[ -n "$last_file" ]]; then
                encontrado="$last_file"
                ano_sinc="$ano"
                break
            fi
        fi
    done

    if [[ -z "$encontrado" ]]; then
        echo "[ERRO] Não foi possível obter o último dia sincronizado na SDS. Abortando." >&2
        exit 1
    fi

    ultimo_sinc="$encontrado"
    echo "→ Último dia sincronizado na SDS (ano $ano_sinc): $ultimo_sinc"
}
# DOC-END: SYNC-FUNC-obter_ultimo_sinc

################################################################################
# Suporte a .zip.bz2 + listagem genérica de paths dentro de ZIP/RAR/TAR
################################################################################
# DOC-SECTION: SYNC-FUNC-prepare_archive
prepare_archive() {
    local in="$1"
    ARCH_ORIG="$in"
    ARCH_FILE="$in"
    ARCH_KIND=""

    case "$in" in
        *.zip.bz2)
            ARCH_KIND="zip"
            local cache_dir="$base_dir/_ARCHIVE_CACHE"
            run_cmd mkdir -p "$cache_dir"
            ARCH_FILE="$cache_dir/$(basename "${in%.bz2}")"

            if [[ ! -f "$ARCH_FILE" || "$in" -nt "$ARCH_FILE" ]]; then
                echo "   - Detectado .zip.bz2: descompactando para cache → $ARCH_FILE"
                if ! bzip2 -dc -- "$in" > "$ARCH_FILE"; then
                    rm -f -- "$ARCH_FILE"
                    echo "   - [ERRO] Falha ao descompactar $in" >&2
                    return 1
                fi
                if ! unzip -tqq -- "$ARCH_FILE" >/dev/null 2>&1; then
                    rm -f -- "$ARCH_FILE"
                    echo "   - [ERRO] Cache gerado não é um ZIP válido: $ARCH_FILE" >&2
                    return 1
                fi
            fi
            ;;
        *.zip) ARCH_KIND="zip" ;;
        *.rar) ARCH_KIND="rar" ;;
        *.tar) ARCH_KIND="tar" ;;
		*.7z)  ARCH_KIND="7z"  ;;
        *) return 2 ;;
    esac
    return 0
}
# DOC-END: SYNC-FUNC-prepare_archive

# DOC-SECTION: SYNC-FUNC-list_archive_paths
list_archive_paths() {
    local kind="$1"
    local file="$2"
    local list_timeout="${LIST_TIMEOUT:-60s}"
    local err_file=""
    local stderr_target="/dev/null"
    local list_err_log="${log_dir:-.}/archive_list_errors.log"

    report_list_error() {
        local tool="$1"
        local status="$2"
        echo "   - [WARN] Falha ao listar conteúdo ($tool) em '$file' (exit=$status). Pulando." >&2
        if [[ -n "$err_file" && -s "$err_file" ]]; then
            local summary
            summary="$(tail -n 5 "$err_file")"
            echo "   - [WARN] Erros recentes ($tool):" >&2
            echo "$summary" | sed 's/^/     /' >&2
            cat "$err_file" >> "$list_err_log"
        fi
    }

    if [[ "${DEBUG_TRACE:-0}" -eq 1 ]]; then
        err_file="$(mktemp -t list_archive_paths.XXXXXX)"
        stderr_target="$err_file"
    fi

    case "$kind" in
        zip)
            # zipinfo costuma ser mais “seco”/rápido quando existe (parte do pacote unzip em muitos sistemas)
            if command -v zipinfo >/dev/null 2>&1; then
                #timeout --foreground "$list_timeout" zipinfo -1 -- "$file" '*/[0-9][0-9][0-9][0-9][0-9][0-9][0-9]/*/[01]' 2>/dev/null || return 1
                if ! timeout --foreground "$list_timeout" zipinfo -1 -- "$file" 2> "$stderr_target"; then
                    local status=$?
                    report_list_error "zipinfo" "$status"
                    [[ -n "$err_file" ]] && rm -f "$err_file"
                    return 0
                fi
            else
                #timeout --foreground "$list_timeout" unzip -Z1 -- "$file" '*/[0-9][0-9][0-9][0-9][0-9][0-9][0-9]/*/[01]' 2>/dev/null || return 1
                if ! timeout --foreground "$list_timeout" unzip -Z1 -- "$file" 2> "$stderr_target"; then
                    local status=$?
                    report_list_error "unzip" "$status"
                    [[ -n "$err_file" ]] && rm -f "$err_file"
                    return 0
                fi
            fi
            ;;
        rar)
            if ! timeout --foreground "$list_timeout" unrar lb -p- -- "$file" 2> "$stderr_target"; then
                local status=$?
                report_list_error "unrar" "$status"
                [[ -n "$err_file" ]] && rm -f "$err_file"
                return 0
            fi
            ;;
        tar)
            if ! timeout --foreground "$list_timeout" tar -tf --wildcards -- "$file" '*/[0-9][0-9][0-9][0-9][0-9][0-9][0-9]/*/[01]' 2> "$stderr_target"; then
                local status=$?
                report_list_error "tar" "$status"
                [[ -n "$err_file" ]] && rm -f "$err_file"
                return 0
            fi
            ;;
        7z)
            if ! timeout --foreground "$list_timeout" 7z l -slt -p- -y -bsp0 -i!*/[0-9][0-9][0-9][0-9][0-9][0-9][0-9]/*/0 -i!*/[0-9][0-9][0-9][0-9][0-9][0-9][0-9]/*/1 -- "$file" 2> "$stderr_target" \
              | awk -F' = ' '/^Path = /{print $2}' \
              | sed '/^$/d'; then
                local status=$?
                report_list_error "7z" "$status"
                [[ -n "$err_file" ]] && rm -f "$err_file"
                return 0
            fi
            ;;
        *)
            return 1
            ;;
    esac

    [[ -n "$err_file" ]] && rm -f "$err_file"
}
# DOC-END: SYNC-FUNC-list_archive_paths

# DOC-SECTION: SYNC-FUNC-extract_dates_from_rasp
extract_dates_from_rasp() {
    local zip_file="$1"
    local das_code="$2"

    unzip -Z1 "$zip_file" 2>/dev/null | \
    grep -E "/data/archive/[0-9]{4}/AM/${das_code}/EH[ZEN]\.D/" | \
    awk -F'.' '{
        year = $(NF-1)
        jul  = $NF
        if (year ~ /^[0-9]{4}$/ && jul ~ /^[0-9]{3}$/) print year jul
    }' | sort -n | uniq
}
# DOC-END: SYNC-FUNC-extract_dates_from_rasp

# Extrai diretórios YYYYJJJ quando existe:
#   YYYYJJJ/DAS/0 ou YYYYJJJ/DAS/1 (qualquer profundidade)
# DOC-SECTION: SYNC-FUNC-extract_reftek_dates_any_depth
extract_reftek_dates_any_depth() {
    local kind="$1"
    local file="$2"
    local codes_pat="$3"   # ex: "9690|AD20"

    # Extrai diretórios que terminem em: .../<YYYYJJJ...>/<DAS>/<STREAM>[/]
    # (independente da profundidade), evitando varrer o path em loops O(m) por linha.
    list_archive_paths "$kind" "$file" | \
    awk -v codes="$codes_pat" '
        BEGIN{
            n = split(codes, C, "|")
            codes_re = C[1]
            for (i=2; i<=n; i++) codes_re = codes_re "|" C[i]

            # casa DIRETÓRIO: .../<YYYYJJJ...>/<CODE>/<STREAM>   (opcional "/" no fim)
            re = "(^|/)([0-9]{7})[^/]*\\/(" codes_re ")\\/([0-9]+)\\/?$"
        }
        {
            sub(/^\.[\/\\]/, "", $0)   # remove prefixo "./" ou ".\"
            gsub(/\\/, "/", $0)        # normaliza separador Windows -> Unix

            if (match($0, re, M)) {
                d = M[2]; s = M[4]
                if (!seen[d SUBSEP s]++) {
                    streams[d] = (d in streams) ? streams[d] "," s : s
                    days[d] = 1
                }
            }
        }
        END {
            for (d in days) print d ":" streams[d]
        }
    ' | LC_ALL=C sort -t: -k1,1
}
# DOC-END: SYNC-FUNC-extract_reftek_dates_any_depth

################################################################################
######################## BUSCA DO ZIP MAIS PRÓXIMO #############################
################################################################################
# DOC-SECTION: SYNC-FUNC-encontrar_closest_zip
function encontrar_closest_zip() {
    local origin_dir="$base_dir/ZIP/$ESTACAO_ESCOLHIDA"
    local best_diff=999

    closest_zip=""
    closest_zip_orig=""
    closest_date=""
    last_date=""
    closest_streams_info=()

    [[ -n "${das_code:-}" ]] || { echo "[ERRO] das_code vazio"; exit 1; }
    [[ -n "${code_pattern:-}" ]] || code_pattern="$(build_code_pattern "$das_code")"
    [[ -n "${code_pattern:-}" ]] || { echo "[ERRO] code_pattern vazio para das_code='$das_code'"; exit 1; }

    shopt -s nullglob

    local arquivo
    for arquivo in "$origin_dir"/*; do
        [[ -f "$arquivo" ]] || continue

        echo
        echo "→ Analisando arquivo: $arquivo"

        if ! prepare_archive "$arquivo"; then
            echo "   - Extensão não suportada (ou falha ao preparar archive). Pulando."
            continue
        fi

        local kind="$ARCH_KIND"
        local work_file="$ARCH_FILE"

        local raw_datas=()
        if [[ "$station_type" == "raspberry" ]]; then
            mapfile -t raw_datas < <( extract_dates_from_rasp "$work_file" "$das_code" )
        else
            mapfile -t raw_datas < <(
                extract_reftek_dates_any_depth "$kind" "$work_file" "$code_pattern"
            )
        fi

        if (( ${#raw_datas[@]} )); then
            echo "   - Pastas internas encontradas (dia:streams):"
            echo "${raw_datas[*]}"
        else
            echo "   - Sem pastas internas (YYYYJJJ/DAS/[0-n]) em $arquivo."
            continue
        fi

        local -a todas_datas=()
        local -a day_streams_lines=()
        local -A day_streams=()
        local entry
        for entry in "${raw_datas[@]}"; do
            local day="${entry%%:*}"
            local streams="${entry#*:}"
            [[ "$entry" == *:* ]] || streams=""
            day_streams["$day"]="$streams"
            todas_datas+=("$day")
        done

        mapfile -t todas_datas < <(
            printf "%s\n" "${todas_datas[@]}" | sort -u
        )

        local dia
        for dia in "${todas_datas[@]}"; do
            day_streams_lines+=("$dia:${day_streams[$dia]}")
        done

        echo "   - Datas internas e streams:"
        printf "     • %s\n" "${day_streams_lines[@]}"

        local valid_new_dates=()
        for dia in "${todas_datas[@]}"; do
            local julian=${dia:4:3}
            (( 10#$julian >= 10#$ultimo_sinc )) && valid_new_dates+=("$dia")
        done
        if (( ${#valid_new_dates[@]} == 0 )); then
            echo "   - Nenhuma data ≥ $ultimo_sinc neste arquivo."
            continue
        fi

        local first_new=${valid_new_dates[0]}
        local last_new=${valid_new_dates[-1]}
        local diff=$(( 10#${first_new:4:3} - 10#$ultimo_sinc ))

        echo "   - Primeiro dia novo ≥ $ultimo_sinc: $first_new (diff=$diff)"

        if (( diff < best_diff )) || \
           (( diff == best_diff && 10#${last_new:4:3} > 10#${last_date:4:3} )); then
            best_diff=$diff
            closest_zip="$work_file"
            closest_zip_orig="$ARCH_ORIG"
            closest_date="$first_new"
            last_date="$last_new"
            closest_streams_info=("${day_streams_lines[@]}")
        fi
    done

    if [[ -z "$closest_zip" ]]; then
		echo "[ERRO] Nenhum arquivo adequado encontrado (.zip, .zip.bz2, .rar, .tar, .7z). Abortando." >&2
        exit 1
    fi

    local closest_gregorian
    local last_gregorian
    closest_gregorian=$(date -d "${closest_date:0:4}-01-01 +$((10#${closest_date:4:3}-1)) days" +%Y-%m-%d)
    last_gregorian=$(date -d "${last_date:0:4}-01-01 +$((10#${last_date:4:3}-1)) days" +%Y-%m-%d)

    echo
    echo "###############################################"
    echo "→ ARQUIVO ESCOLHIDO PARA SINCRONIZAÇÃO:"
    echo "     • Arquivo:      $closest_zip"
    echo "     • Primeiro dia: $closest_date - $closest_gregorian"
    echo "     • Último dia:   $last_date - $last_gregorian"
    if (( ${#closest_streams_info[@]} )); then
        echo "     • Streams por dia:"
        printf "       - %s\n" "${closest_streams_info[@]}"
    fi
    echo "###############################################"
}
# DOC-END: SYNC-FUNC-encontrar_closest_zip

################################################################################
# Validação parfile + resumo
################################################################################
# DOC-SECTION: SYNC-FUNC-comparar_parfiles_com_tolerancia
comparar_parfiles_com_tolerancia() {
    local par_template="$1"
    local par_expl="$2"

    awk -F';' '
      function trim(s){ gsub(/^[ \t]+|[ \t]+$/, "", s); return s }

      NR==FNR {
          if (FNR == 1) { header_expl = $0; next }
          for (i=1;i<=NF;i++) $i = trim($i)
          key = $1 "|" $2 "|" $3
          a_net[key]   = $4
          a_sta[key]   = $5
          a_loc[key]   = $6
          a_chan[key]  = $7
          a_sr[key]    = $8
          a_gain[key]  = $9
          a_itime[key] = $10
          has_expl[key]= 1
          next
      }

      FNR == 1 {
          header_tmpl = $0
          if (header_tmpl != header_expl) {
              printf("[ERRO] Cabeçalho do parfile exploratório difere do template.\n") > "/dev/stderr"
              printf("       template:     %s\n", header_tmpl)  > "/dev/stderr"
              printf("       exploratório: %s\n", header_expl)  > "/dev/stderr"
              erro = 1
          }
          next
      }

      {
          for (i=1;i<=NF;i++) $i = trim($i)
          das     = $1
          refchan = $2
          refstrm = $3
          if (refstrm != 1) next
          key = das "|" refchan "|" refstrm

          if (!(key in has_expl)) {
              printf("[ERRO] Parfile exploratório não contém linha equivalente para %s|%s|%s\n",
                     das, refchan, refstrm) > "/dev/stderr"
              erro = 1
              next
          }

          tmpl_net   = $4
          tmpl_sta   = $5
          tmpl_loc   = $6
          tmpl_chan  = $7
          tmpl_sr    = $8
          tmpl_gain  = $9
          tmpl_itime = $10

          expl_net   = a_net[key]
          expl_sta   = a_sta[key]
          expl_loc   = a_loc[key]
          expl_chan  = a_chan[key]
          expl_sr    = a_sr[key]
          expl_gain  = a_gain[key]
          expl_itime = a_itime[key]

          low_tmpl_net = tolower(tmpl_net)
          low_expl_net = tolower(expl_net)
          if (!(low_tmpl_net == low_expl_net || low_expl_net == "xx")) {
              printf("[ERRO] NETCODE difere: template=\"%s\" exploratório=\"%s\" (%s|%s|%s)\n",
                     tmpl_net, expl_net, das, refchan, refstrm) > "/dev/stderr"
              erro = 1
          }

          if (tolower(tmpl_sta) != tolower(expl_sta)) {
              printf("[ERRO] STATION difere: template=\"%s\" exploratório=\"%s\" (%s|%s|%s)\n",
                     tmpl_sta, expl_sta, das, refchan, refstrm) > "/dev/stderr"
              erro = 1
          }

          if (tmpl_loc != expl_loc) {
              printf("[ERRO] LOCATION difere: template=\"%s\" exploratório=\"%s\" (%s|%s|%s)\n",
                     tmpl_loc, expl_loc, das, refchan, refstrm) > "/dev/stderr"
              erro = 1
          }

          low_tmpl_chan = tolower(tmpl_chan)
          low_expl_chan = tolower(expl_chan)
          chan_ok = 0
          if (low_tmpl_chan == low_expl_chan) {
              chan_ok = 1
          } else if ( (low_tmpl_chan=="hhn" && low_expl_chan=="hh1") ||
                      (low_tmpl_chan=="hh1" && low_expl_chan=="hhn") ||
                      (low_tmpl_chan=="hhe" && low_expl_chan=="hh2") ||
                      (low_tmpl_chan=="hh2" && low_expl_chan=="hhe") ) {
              chan_ok = 1
          }
          if (!chan_ok) {
              printf("[ERRO] CHANNEL difere: template=\"%s\" exploratório=\"%s\" (%s|%s|%s)\n",
                     tmpl_chan, expl_chan, das, refchan, refstrm) > "/dev/stderr"
              erro = 1
          }

          if (tmpl_sr != expl_sr) {
              printf("[ERRO] SAMPLERATE difere: template=\"%s\" exploratório=\"%s\" (%s|%s|%s)\n",
                     tmpl_sr, expl_sr, das, refchan, refstrm) > "/dev/stderr"
              erro = 1
          }

          if (tmpl_gain != expl_gain) {
              printf("[ERRO] GAIN difere: template=\"%s\" exploratório=\"%s\" (%s|%s|%s)\n",
                     tmpl_gain, expl_gain, das, refchan, refstrm) > "/dev/stderr"
              erro = 1
          }

          if (tmpl_itime != expl_itime) {
              printf("[ERRO] IMPLEMENT_TIME difere: template=\"%s\" exploratório=\"%s\" (%s|%s|%s)\n",
                     tmpl_itime, expl_itime, das, refchan, refstrm) > "/dev/stderr"
              erro = 1
          }
      }

      END { exit erro }
    ' "$par_expl" "$par_template"
}
# DOC-END: SYNC-FUNC-comparar_parfiles_com_tolerancia

# DOC-SECTION: SYNC-FUNC-resumir_auto_substituicoes_parfile
function resumir_auto_substituicoes_parfile() {
    local msg_file="$1"
    [[ -f "$msg_file" ]] || return 0

    if ! grep -q "Invalid network code (netcode" "$msg_file" \
       && ! grep -q "Invalid channel name found" "$msg_file"; then
        return 0
    fi

    echo "      • Substituições automáticas detectadas pelo rt2ms (modo exploratório):"

    awk '
    /Invalid network code \(netcode = / {
        orig = $0
        net = orig
        sub(/.*Invalid network code \(netcode = /, "", net)
        sub(/\).*/, "", net)

        new = orig
        sub(/.*default one \(/, "", new)
        sub(/\).*/, "", new)

        printf("         - NETCODE: \"%s\" → \"%s\"\n", net, new)
    }

    /Invalid channel name found/ {
        orig = $0
        oldc = orig
        sub(/.*Invalid channel name found /, "", oldc)
        sub(/\..*/, "", oldc)

        newc = orig
        sub(/.*renaming channel as /, "", newc)
        sub(/\..*/, "", newc)

        printf("         - CHANNEL: \"%s\" → \"%s\"\n", oldc, newc)
    }
    ' "$msg_file"
}
# DOC-END: SYNC-FUNC-resumir_auto_substituicoes_parfile

################################################################################
########################### PROCESSAMENTO REFTEK ################################
################################################################################
# FIX: find robusto sem -regex (evita falso "não encontrado" e evita depender de code_pattern)
# DOC-SECTION: SYNC-FUNC-find_reftek_dirs_stream1
find_reftek_dirs_stream1() {
    local root="$1"; shift
    local -a codes=("$@")
    local -a args=( "$root" -type d "(" )
    local first=1
    local c
    for c in "${codes[@]}"; do
        [[ -n "$c" ]] || continue
        if (( first )); then first=0; else args+=( -o ); fi
        args+=( -path "*/$c/1" )
    done
    args+=( ")" )
    find "${args[@]}"
}
# DOC-END: SYNC-FUNC-find_reftek_dirs_stream1

# DOC-SECTION: SYNC-FUNC-find_reftek_files_stream0
find_reftek_files_stream0() {
    local root="$1"; shift
    local -a codes=("$@")
    local -a args=( "$root" -type f "(" )
    local first=1
    local c
    for c in "${codes[@]}"; do
        [[ -n "$c" ]] || continue
        if (( first )); then first=0; else args+=( -o ); fi
        args+=( -path "*/$c/0/*" )
    done
    args+=( ")" )
    find "${args[@]}"
}
# DOC-END: SYNC-FUNC-find_reftek_files_stream0

# DOC-SECTION: SYNC-FUNC-processar_reftek
function processar_reftek() {
    echo
    echo "→ Iniciando processamento REFTEK para estação $ESTACAO_ESCOLHIDA"

    local year_first="${closest_date:0:4}"
    local julian_first="${closest_date:4:3}"
    local year_last="${last_date:0:4}"
    local julian_last="${last_date:4:3}"

    data="$(date -d "$year_last-01-01 +$((10#${julian_last}-1)) days" +%Y%m%d)"
    target_dir="$base_dir/${ESTACAO_ESCOLHIDA}_$data"
    binary_dir="$target_dir/${ESTACAO_ESCOLHIDA}_${data}_BINARIES"

    run_cmd mkdir -p "$binary_dir"
    echo "   - Criado diretório de binários: $binary_dir"

    echo "   - Descompactando $closest_zip → $target_dir ..."
    local ext_zip="${closest_zip##*.}"
    ext_zip="${ext_zip,,}"
    case "$ext_zip" in
        zip) run_cmd unzip -qq "$closest_zip" -d "$target_dir" ;;
        rar) run_cmd mkdir -p "$target_dir"; run_cmd unrar x -inul "$closest_zip" "$target_dir/" ;;
        tar) run_cmd mkdir -p "$target_dir"; run_cmd tar -xf "$closest_zip" -C "$target_dir" ;;
        7z)  run_cmd mkdir -p "$target_dir"; run_cmd 7z x -y -o"$target_dir" "$closest_zip" >/dev/null ;;
        *) echo "[ERRO] Tipo de arquivo '$ext_zip' não suportado." >&2; exit 1 ;;
    esac

    # Descobre dirs DAS_CODE (um ou vários)
    split_das_codes "$das_code"
    local -a codes=("${_CODES_SPLIT[@]}")

    mapfile -t source_dirs < <(
        find "$target_dir" -type d \( \
            -name "${codes[0]}" $(for c in "${codes[@]:1}"; do printf -- "-o -name %s " "$c"; done) \
        \)
    )
    if (( ${#source_dirs[@]} == 0 )); then
        echo "[ERRO] Nenhum diretório ${codes[*]} encontrado em $target_dir. Abortando." >&2
        exit 1
    fi

    get_subrel_yjjj_das() {
        local src="$1"
        local rel="${src#"$target_dir/"}"
        IFS='/' read -r -a parts <<< "$rel"

        local i c
        for ((i=0; i<${#parts[@]}-1; i++)); do
            if [[ "${parts[i]}" =~ ^[0-9]{7}([_-].+)?$ ]]; then
                for c in "${codes[@]}"; do
                    if [[ "${parts[i+1]:-}" == "$c" ]]; then
                        printf "%s/%s\n" "${parts[i]}" "${parts[i+1]}"
                        return 0
                    fi
                done
            fi
        done
        return 1
    }

    echo "   - Movendo apenas a partir de YYYYJJJ/DASCODE/ para o BINARIES..."
    local src
    for src in "${source_dirs[@]}"; do
        local subrel
        if ! subrel="$(get_subrel_yjjj_das "$src")"; then
            echo "[ERRO] Não consegui derivar subrel YYYYJJJ/DASCODE a partir de: $src" >&2
            exit 1
        fi

        run_cmd mkdir -p "$binary_dir/$subrel"
        run_cmd rsync -a --remove-source-files "$src"/ "$binary_dir/$subrel"/ >/dev/null
        run_cmd find "$(dirname "$src")" -type d -empty -delete
    done

    echo "   - Todos os diretórios YYYYJJJ/DASCODE foram movidos para BINARIES."

    echo "   - Verificando integridade horária..."
    mapfile -t hour_dirs < <( find_reftek_dirs_stream1 "$binary_dir" "${codes[@]}" )

    local hour_dir
    for hour_dir in "${hour_dirs[@]}"; do
        local count_files
        count_files=$(ls -A "$hour_dir" 2>/dev/null | wc -l)

        local raw_day_dir
        raw_day_dir=$(basename "$(dirname "$(dirname "$hour_dir")")")
        local day_dir="${raw_day_dir:0:7}"

        if (( count_files != 24 )); then
            if [[ "$day_dir" == "${year_first}${julian_first}" || "$day_dir" == "${year_last}${julian_last}" ]]; then
                echo "      • BORDA DE COLETA: $hour_dir"
            else
                echo "      • ARQUIVOS INCOMPLETOS: $hour_dir"
            fi
        fi
    done

    echo "   - Extraindo informações de GPS/BATTERY/TEMP..."
    mapfile -t info_files < <( find_reftek_files_stream0 "$binary_dir" "${codes[@]}" )

    if (( ${#info_files[@]} == 0 )); then
        echo "      • [AVISO] Nenhum arquivo */DASCODE/0/* encontrado em $binary_dir"
    else
        local info_file
        for info_file in "${info_files[@]}"; do
            awk '
                /GPS:/ {
                    gsub(/[[:cntrl:]]|SH\$[^ ]*/, "", $0); print $0; getline;
                    gsub(/[[:cntrl:]]|SH\$[^ ]*/, "", $0); print $0; getline;
                }
                /BATTERY VOLTAGE/ {
                    gsub(/[[:cntrl:]]|SH\$[^ ]*/, "", $0); print $0;
                }
            ' "$info_file" >> "$target_dir/${ESTACAO_ESCOLHIDA}_${data}_info.log"
        done

        info_log="$target_dir/${ESTACAO_ESCOLHIDA}_${data}_info.log"

        awk '/GPS: POSITION:/ { print }' "$info_log" \
          | sort -t':' -k1,1n -k2,2n -k3,3n -k4,4n \
          > "$target_dir/${ESTACAO_ESCOLHIDA}_${data}.gps"

        awk '/BATTERY VOLTAGE/ { print }' "$info_log" \
          | sort -t':' -k1,1n -k2,2n -k3,3n -k4,4n \
          > "$target_dir/${ESTACAO_ESCOLHIDA}_${data}.battery"

        echo "      • GPS e BATTERY extraídos e ordenados:"
        echo "         - $target_dir/${ESTACAO_ESCOLHIDA}_${data}.gps"
        echo "         - $target_dir/${ESTACAO_ESCOLHIDA}_${data}.battery"
    fi

    pushd "$target_dir" >/dev/null
      echo "   - Convertendo para MSEED (rt2ms_py3) e enviando ao SDS..."

      RT2MS_ROOT="$base_dir/python/rt2ms_py3"
      CF_ROOT="$binary_dir"

      run_cmd bash -lc "cd '$target_dir' && PYTHONPATH='$RT2MS_ROOT' python3 -m rt2ms_py3.rt2ms_py3 -d '$CF_ROOT' -e"

      [[ -f "$target_dir/parfile.txt" ]] || { echo "[ERRO] parfile.txt não foi gerado."; exit 1; }

      local msg_file="$target_dir/rt2ms.msg"
      resumir_auto_substituicoes_parfile "$msg_file"

      par_template="$PARFILES_DIR/${ESTACAO_ESCOLHIDA}_parfile.txt"
      local review_marker="${par_template}.NEEDS_REVIEW"


	  local -a orientation_summary=()

      bootstrap_parfile_template() {
      	echo "      • [AVISO] Template de parfile não encontrado em $par_template; iniciando fluxo de primeira execução."

      	run_cmd mkdir -p "$PARFILES_DIR"

      	run_cmd bash -lc "cd '$target_dir' && PYTHONPATH='$RT2MS_ROOT' python3 -m rt2ms_py3.rt2ms_py3 -d '$CF_ROOT' -X"

      	local rtlog_dir="$target_dir/LOGS"
      	local rtlog_file=""
      	if [[ -d "$rtlog_dir" ]]; then
      		rtlog_file="$(ls -t "$rtlog_dir"/RT130_*.log 2>/dev/null | head -n1 || true)"
      	fi
      	if [[ -z "$rtlog_file" ]]; then
      		echo "[ERRO] Log RT130 não encontrado após rt2ms -X em $rtlog_dir." >&2
      		exit 1
      	fi

      	# Mapa correto: refchan (1/2/3) -> orientação (Z/N/E)
      	declare -A orient_by_refchan=()
      	local upper_station="${ESTACAO_ESCOLHIDA^^}"

      	infer_orientacao_reftek() {
      		local name="$1"
      		local az_raw="$2"
      		local inc_raw="$3"
      		local tol=5
      		local az inc

      		az="$(awk -v v="$az_raw" 'BEGIN{ if (match(v,/[-+]?[0-9]*\.?[0-9]+/)) print substr(v,RSTART,RLENGTH) }')"
      		inc="$(awk -v v="$inc_raw" 'BEGIN{ if (match(v,/[-+]?[0-9]*\.?[0-9]+/)) print substr(v,RSTART,RLENGTH) }')"

      		local orientation=""
      		if [[ -n "$inc" ]]; then
      			orientation="$(awk -v inc="$inc" -v az="$az" -v tol="$tol" '
      				function abs(x){return x<0?-x:x}
      				BEGIN {
      					if (abs(inc-0) <= tol) print "Z";
      					else if (abs(inc-90) <= tol && abs(az-0) <= tol) print "N";
      					else if (abs(inc-90) <= tol && abs(az-90) <= tol) print "E";
      				}
      			')"
      		fi

      		# Fallback por nome (v/ns/ew)
      		if [[ -z "$orientation" ]]; then
      			local lower_name
      			lower_name="$(echo "$name" | tr -d '[:space:]' | tr '[:upper:]' '[:lower:]')"
      			case "$lower_name" in
      				v*  ) orientation="Z" ;;
      				ns* ) orientation="N" ;;
      				ew* ) orientation="E" ;;
      			esac
      		fi

      		printf "%s" "$orientation"
      	}

      	# Extrai do RT130 log: "Channel Number = X" + "Name - ..." + "Azimuth - ..." + "Inclination - ..."
      	# (corrige: uso de variável "in" no awk + corrige ":" vs "-" no formato do log)
      	while IFS=';' read -r refchan name az inc; do
      		refchan="$(echo "$refchan" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
      		name="$(echo "$name" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"

      		# Inferência principal por (inc, az) e fallback por nome
      		local orientation
      		orientation="$(infer_orientacao_reftek "$name" "$az" "$inc")"

      		# Fallback final por refchan se vier vazio
      		if [[ -z "$orientation" ]]; then
      			case "$refchan" in
      				1) orientation="Z" ;;
      				2) orientation="N" ;;
      				3) orientation="E" ;;
      			esac
      		fi

      		if [[ -n "$refchan" && -n "$orientation" ]]; then
      			orient_by_refchan["$refchan"]="$orientation"
      			orientation_summary+=( "${refchan}:${name}:${orientation}" )
      		fi
      	done < <(
      		awk '
      			function trim(s){ gsub(/^[ \t]+|[ \t]+$/, "", s); return s }

      			/Station Channel Definition/ {
      				in_def=1; ch=""; name=""; az=""; inc=""; next
      			}

      			in_def && /Channel Number[[:space:]]*=/ {
      				# flush do canal anterior
      				if (ch != "") print ch ";" name ";" az ";" inc
      				ch=$0; sub(/.*=/, "", ch); ch=trim(ch)
      				name=az=inc=""
      				next
      			}

      			in_def && /Name[[:space:]]*[-=]/ {
      				t=$0; sub(/.*[-=]/, "", t); name=trim(t); next
      			}
      			in_def && /Azimuth[[:space:]]*[-=]/ {
      				t=$0; sub(/.*[-=]/, "", t); az=trim(t); next
      			}
      			in_def && /Inclination[[:space:]]*[-=]/ {
      				t=$0; sub(/.*[-=]/, "", t); inc=trim(t); next
      			}

      			# termina o bloco ao entrar em OM (após o Station Channel Definition)
      			in_def && /^OM exp/ {
      				if (ch != "") print ch ";" name ";" az ";" inc
      				exit
      			}

      			END {
      				if (in_def && ch != "") print ch ";" name ";" az ";" inc
      			}
      		' "$rtlog_file"
      	)

      	run_cmd cp "$target_dir/parfile.txt" "$par_template"
      	run_cmd touch "$review_marker"

      	# Arquivo de mapa refchan->orient para o awk de normalização
      	local orient_map_file
      	orient_map_file="$(mktemp)"
      	for refchan in "${!orient_by_refchan[@]}"; do
      		printf "%s %s\n" "$refchan" "${orient_by_refchan[$refchan]}" >> "$orient_map_file"
      	done

      	local normalized_tmp
      	normalized_tmp="$(mktemp)"
      	if ! awk -F';' -v OFS='; ' -v sta="$upper_station" -v net="$project_code" '
      		function trim(s){ gsub(/^[ \t]+|[ \t]+$/, "", s); return s }

      		FNR==NR {
      			ch=trim($1); o=trim($2)
      			if (ch != "" && o != "") map[ch]=o
      			next
      		}

      		NR==1 { print $0; next }

      		{
      			for (i=1;i<=NF;i++) $i = trim($i)
      			$4 = net
      			$5 = sta

      			if ($3 == 1) {
      				refchan = trim($2)
      				orient = map[refchan]

      				if (orient == "") {
      					# fallback robusto por refchan
      					if (refchan == "1") orient = "Z"
      					else if (refchan == "2") orient = "N"
      					else if (refchan == "3") orient = "E"
      				}

      				if (orient == "") {
      					printf("[ERRO] Orientação não inferida para refchan=%s (refstrm=1)\n", refchan) > "/dev/stderr"
      					erro = 1
      				} else {
      					if (orient == "Z") $7 = "HHZ"
      					else if (orient == "N") $7 = "HHN"
      					else if (orient == "E") $7 = "HHE"
      				}
      			}

      			print $0
      		}

      		END { exit erro }
      	' "$orient_map_file" "$par_template" > "$normalized_tmp"; then
      		echo "[ERRO] Falha ao normalizar template do parfile." >&2
      		rm -f "$orient_map_file" "$normalized_tmp"
      		exit 1
      	fi

      	run_cmd mv "$normalized_tmp" "$par_template"
      	run_cmd chmod 664 "$par_template" "$review_marker" 2>/dev/null || true
      	rm -f "$orient_map_file"

      	local minimal_tmp
      	minimal_tmp="$(mktemp)"
      	if ! awk -F';' -v OFS='; ' '
      		function trim(s){ gsub(/^[ \t]+|[ \t]+$/, "", s); return s }
      		NR==1 { print $0; next }
      		{
      			refchan = trim($2)
      			refstrm = trim($3)
      			if (refstrm == 1 && (refchan == 1 || refchan == 2 || refchan == 3)) print $0
      		}
      	' "$par_template" > "$minimal_tmp"; then
      		echo "[ERRO] Falha ao reduzir template do parfile." >&2
      		rm -f "$minimal_tmp"
      		exit 1
      	fi

      	run_cmd mv "$minimal_tmp" "$par_template"
      	run_cmd chmod 664 "$par_template" "$review_marker" 2>/dev/null || true
      }

      if [[ -f "$par_template" ]]; then
          echo "      • Validando parfile.txt contra template: $par_template"
          if ! comparar_parfiles_com_tolerancia "$par_template" "$target_dir/parfile.txt"; then
              echo
              echo "[ERRO] O parfile gerado (parfile.txt) difere do template padrão fora dos limites permitidos." >&2
              exit 1
          fi
      else
          bootstrap_parfile_template

          local -a ignored_triggers=()
          mapfile -t ignored_triggers < <(
              awk -F';' '
                  function trim(s){ gsub(/^[ \t]+|[ \t]+$/, "", s); return s }
                  NR>1 {
                      refchan = trim($2)
                      refstrm = trim($3)
                      if (refstrm != 1) print refchan "/" refstrm
                  }
              ' "$par_template"
          )

          echo "      • Template normalizado: netcode=$project_code, station=$upper_station"
          if (( ${#orientation_summary[@]} )); then
              printf "      • Orientações inferidas (refstrm=1): %s\n" "${orientation_summary[*]}"
          else
              echo "      • [AVISO] Nenhuma orientação inferida a partir do log RT130."
          fi
          if (( ${#ignored_triggers[@]} )); then
              printf "      • Triggers ignorados (refstrm 2/3): %s\n" "${ignored_triggers[*]}"
          fi

          "${EDITOR:-nvim}" "$par_template"
      fi

      local skipped_streams_dir="$target_dir/_SKIPPED_STREAMS"
      run_cmd mkdir -p "$skipped_streams_dir"
      local stream_dir
      while IFS= read -r stream_dir; do
          local rel_path="${stream_dir#"$binary_dir/"}"
          local stash_path="$skipped_streams_dir/$rel_path"
          run_cmd mkdir -p "$(dirname "$stash_path")"
          run_cmd mv "$stream_dir" "$stash_path"
      done < <(find "$binary_dir" -mindepth 3 -maxdepth 3 -type d \( -name 2 -o -name 3 \))

      if [[ ! -f "$par_template" ]]; then
          bootstrap_parfile_template
          "${EDITOR:-nvim}" "$par_template"
      fi

      if [[ -f "$review_marker" ]]; then
          echo "[ERRO] Template marcado para revisão: $review_marker. Revise e remova o marcador antes de continuar." >&2
          exit 2
      fi

      outdir="${project_code}.${ESTACAO_ESCOLHIDA}.MSEED"
      run_cmd bash -lc "cd '$target_dir' && PYTHONPATH='$RT2MS_ROOT' python3 -m rt2ms_py3.rt2ms_py3 -d '$CF_ROOT' -p '$par_template' -o '$outdir'"

      log_r2m_file="$log_dir/${ESTACAO_ESCOLHIDA}_r2m.log"
      run_cmd "/home/suporte/TMP/SYNC/python/dataselect/dataselect" -Ps -SDS sds "$outdir"/${ESTACAO_ESCOLHIDA}/*..HH?.*
      run_cmd sc3 exec /home/suporte/bin/sdsClone.py -s sds/ -l "${ESTACAO_ESCOLHIDA}_${data}.log"
      echo 's' | run_cmd /home/suporte/bin/workthisout.sh --nostop
    popd >/dev/null

    echo "→ Processamento REFTEK concluído."
}
# DOC-END: SYNC-FUNC-processar_reftek

################################################################################
########################## PROCESSAMENTO RASPBERRY ##############################
################################################################################
# DOC-SECTION: SYNC-FUNC-processar_raspberry
function processar_raspberry() {
    echo
    echo "→ Iniciando processamento RASPBERRY para estação $ESTACAO_ESCOLHIDA"

    local year_last="${last_date:0:4}"
    local julian_last="${last_date:4:3}"
    data="$(date -d "$year_last-01-01 +$((10#$julian_last - 1)) days" +%Y%m%d)"
    target_dir="$base_dir/${ESTACAO_ESCOLHIDA}_$data"
    run_cmd mkdir -p "$target_dir"

    echo "   - Listando arquivos no ZIP ($closest_zip) com dia ≥ $ultimo_sinc..."
    mapfile -t to_extract < <(
        unzip -Z1 "$closest_zip" 2>/dev/null | \
        awk -v das="$das_code" -v US="$ultimo_sinc" -F"/" '
            index($0, "/" das "/") && match($NF, /[0-9]{4}\.[0-9]{3}$/) {
                split($NF, partes, ".");
                if (partes[2] >= US) print $0
            }' | sort -u
    )

    [[ ${#to_extract[@]} -eq 0 ]] && {
        echo "[ERRO] Nenhum arquivo ≥ $ultimo_sinc encontrado. Abortando." >&2
        exit 1
    }

    echo "   - Extraindo ${#to_extract[@]} arquivos para $target_dir"
    local MSEED_DIR="$target_dir/${ESTACAO_ESCOLHIDA}_${data}_MSEED"
    run_cmd mkdir -p "$MSEED_DIR"
    run_cmd unzip -qq -j "$closest_zip" "${to_extract[@]}" -d "$MSEED_DIR"

    echo "   - Renomeando canais EH? → HH?..."
    pushd "$MSEED_DIR" >/dev/null
    local chan file
    for chan in EHZ EHN EHE; do
        for file in *"$chan"*; do
            local newchan="HH${chan:2}"
            local newname="${file/.$chan/.${project_code}.${ESTACAO_ESCOLHIDA}..$newchan}"
            run_cmd msmod --net "$project_code" --sta "$ESTACAO_ESCOLHIDA" --loc '' --chan "$newchan" "$file" -o "$newname"
            run_cmd rm "$file"
            echo "      → $file → $newname"
        done
    done
    popd >/dev/null

    echo "   - Enviando .mseed para SDS"
    pushd "$target_dir" >/dev/null
        run_cmd dataselect -Ps -Sd -A sds/%Y/%n/%s/%c.D/%n.%s.%l.%c.D.%Y.%j "${MSEED_DIR}"/*
        run_cmd sc3 exec /home/suporte/bin/sdsClone.py -s sds/ -l "${ESTACAO_ESCOLHIDA}_${data}.log"
        run_cmd /home/suporte/bin/workthisout.sh --nostop
    popd >/dev/null

    unset -v log_r2m_file || true
    echo "→ Processamento RASPBERRY concluído."
}
# DOC-END: SYNC-FUNC-processar_raspberry

################################################################################
########################### RENOMEAR LOG FINAL ##################################
################################################################################
# DOC-SECTION: SYNC-FUNC-finalizar_log
function finalizar_log() {
    if [[ -f "$log_file" ]]; then
        local sds_size
        sds_size=$(du -sh "$target_dir/sds" 2>/dev/null | awk '{print $1}' || echo "NA")

        local zip_ref="${closest_zip_orig:-$closest_zip}"
        local md5sum_zip
        md5sum_zip=$(md5sum "$zip_ref" | awk '{print $1}')
        local zip_size
        zip_size=$(du -sh "$zip_ref" | awk '{print $1}')

        echo "→ MD5 do $(basename "$zip_ref"): $md5sum_zip" >> "$log_file"
        echo "→ Tamanho do ZIP: $zip_size" >> "$log_file"
        echo "→ Tamanho do SDS: $sds_size" >> "$log_file"

        local hora_minuto
        hora_minuto="$(date +%H%M)"

        local new_log="$log_dir/${ESTACAO_ESCOLHIDA}_${data}_${hora_minuto}_sync.log"
        run_cmd mv "$log_file" "$new_log"
        echo "→ Log sincronização renomeado para: $new_log"
        # chave de associação: mesmo prefixo do _sync.log
        local key="${ESTACAO_ESCOLHIDA}_${data}_${hora_minuto}"

        # move RT130_*.log para LOGS/ com o mesmo prefixo
        shopt -s nullglob
        local -a rtlogs=( "$target_dir/LOGS"/RT130_*.log )
        shopt -u nullglob

        if (( ${#rtlogs[@]} > 0 )); then
            local rt
            for rt in "${rtlogs[@]}"; do
                local b="$(basename "$rt")"
                run_cmd mv -- "$rt" "$log_dir/${key}_${b}"
            done
        fi

        if [[ -n "${log_r2m_file:-}" && -f "$log_r2m_file" ]]; then
            local new_r2m="$log_dir/${ESTACAO_ESCOLHIDA}_${data}_${hora_minuto}_r2m.log"
            run_cmd mv "$log_r2m_file" "$new_r2m"
            echo "→ Log r2m renomeado para: $new_r2m"
        fi

        echo "→ Sincronização concluída em: $(date '+%Y-%m-%d %H:%M:%S')" >> "$new_log"
    else
        echo "[WARN] Arquivo de log '$log_file' não encontrado." >&2
    fi
}
# DOC-END: SYNC-FUNC-finalizar_log

################################################################################
########################### CONFIG + MAIN #######################################
################################################################################
# DOC-SECTION: SYNC-MAIN-CONFIG-LOGGING
VERBOSE=1
base_dir="$HOME/TMP/SYNC"
log_dir="$base_dir/LOGS"
PARFILES_DIR="$base_dir/PARFILES/"
mkdir -p "$log_dir"
log_file="$log_dir/test.log"
: > "$log_file"
exec > >(tee -a "$log_file") 2>&1
echo "→ Sincronização iniciada em: $(date '+%Y-%m-%d %H:%M:%S')" >> "$log_file"

# DOC-END: SYNC-MAIN-CONFIG-LOGGING

# DOC-SECTION: SYNC-MAIN-CLI-USAGE
usage() {
  cat << EOF
Uso: $0 [opções]

  -p PROJETO   Nome exato do projeto (por ex: "BAESA ENERCAN")
  -e ESTAÇÃO   Código da estação (por ex: "BC4")
  -y ANO       (opcional) Ano para procurar o último sincronizado (YYYY).
               Se omitido, tenta ano atual e ano anterior.
  -f           Força sincronização (ignora último dia na SDS).
  -d           Debug: mostra TODOS os comandos executados (set -x) com timestamp
  -h           Exibe esta ajuda

Exemplos:
  $0 -p "MACHADINHO" -e "MC9"
  $0 -p "ITA" -e "IT1" -y 2024
  $0
EOF
  exit 1
}
# DOC-END: SYNC-MAIN-CLI-USAGE

# DOC-SECTION: SYNC-MAIN-CLI-GETOPTS
while getopts ":p:e:y:hfd" opt; do
  case "$opt" in
    p) PROJETO_ESCOLHIDO="$OPTARG" ;;
    e) ESTACAO_ESCOLHIDA="$OPTARG" ;;
    y) ANO_FORCADO="$OPTARG" ;;
    f) FORCE_SYNC=1 ;;
    d) DEBUG_TRACE=1 ;;
    h) usage ;;
    *) usage ;;
  esac
done
shift $((OPTIND -1))

# Debug trace (mostra todos os comandos com timestamp)
if [[ "${DEBUG_TRACE:-0}" -eq 1 ]]; then
  # xtrace em arquivo separado (não passa pelo tee do log principal)
  mkdir -p "$log_dir"
  exec 9> "$log_dir/${ESTACAO_ESCOLHIDA:-SYNC}_$(date +%Y%m%d_%H%M%S).xtrace"
  export BASH_XTRACEFD=9

  # evita fork de `date` a cada comando; usa variável builtin do bash (segundos desde epoch)
  export PS4='[${EPOCHSECONDS}.${EPOCHREALTIME#*.}] ${BASH_SOURCE##*/}:${LINENO}:${FUNCNAME[0]:-MAIN}: '

  set -x
fi
# DOC-END: SYNC-MAIN-CLI-GETOPTS

# DOC-SECTION: SYNC-MAIN-SELECT-CONTEXT
if [[ -n "$PROJETO_ESCOLHIDO" && -n "$ESTACAO_ESCOLHIDA" ]]; then
  found=0
  for key in "${!projects[@]}"; do
    IFS='|' read -r p e <<< "${projects[$key]}"
    if [[ "$p" == "$PROJETO_ESCOLHIDO" && "$e" == "$ESTACAO_ESCOLHIDA" ]]; then
      found=1
      break
    fi
  done
  if [[ "$found" -ne 1 ]]; then
    echo "[ERRO] Combinação PROJETO='$PROJETO_ESCOLHIDO' e ESTAÇÃO='$ESTACAO_ESCOLHIDA' não encontrada." >&2
    exit 1
  fi

  project_code="${project_map[$PROJETO_ESCOLHIDO]}"
  das_code="${das_codes[$ESTACAO_ESCOLHIDA]}"
  origin_dir="$base_dir/ZIP/$ESTACAO_ESCOLHIDA"

  # >>> FIX CRÍTICO: code_pattern também no modo -p/-e
  code_pattern="$(build_code_pattern "$das_code")"
  [[ -n "$code_pattern" ]] || { echo "[ERRO] code_pattern vazio para das_code='$das_code'"; exit 1; }

  if is_station_in_list "$ESTACAO_ESCOLHIDA" "${reftek_stations[@]}"; then
    station_type="reftek"
    echo "→ Estação $ESTACAO_ESCOLHIDA ($das_code) é do tipo Reftek."
  elif is_station_in_list "$ESTACAO_ESCOLHIDA" "${raspberry_stations[@]}"; then
    station_type="raspberry"
    echo "→ Estação $ESTACAO_ESCOLHIDA ($das_code) é do tipo Raspberry Shake."
  else
    echo "[ERRO] Estação '$ESTACAO_ESCOLHIDA' não pertence a nenhuma lista conhecida." >&2
    exit 1
  fi
else
  seleciona_projeto_estacao
fi
# DOC-END: SYNC-MAIN-SELECT-CONTEXT

# DOC-SECTION: SYNC-MAIN-ANO-FORCADO
if [[ -n "$ANO_FORCADO" ]]; then
  log_debug "Ano forçado: $ANO_FORCADO"
  export _SHA_ANO_FORCADO="$ANO_FORCADO"
  function obter_ultimo_sinc() {
    local ano="$_SHA_ANO_FORCADO"
    local sds_dir="/SDS/$ano/$project_code/$ESTACAO_ESCOLHIDA/HHZ.D"
    if [[ ! -d "$sds_dir" ]]; then
      echo "[ERRO] Diretório '$sds_dir' não existe para o ano forçado $ano." >&2
      exit 1
    fi
    local last_file
    last_file=$(
        ls -1 "$sds_dir" \
          | awk -F'.' '{print $NF}' \
          | sort -u \
          | tail -n1
    )
    if [[ -z "$last_file" ]]; then
      echo "[ERRO] Nenhum arquivo '*.YYYYJJJ' em '$sds_dir'." >&2
      exit 1
    fi
    ultimo_sinc="$last_file"
    ano_sinc="$ano"
    echo "→ Último dia sincronizado na SDS ($sds_dir): $ultimo_sinc"
  }
fi
# DOC-END: SYNC-MAIN-ANO-FORCADO

# DOC-SECTION: SYNC-MAIN-AUTO-SELECTION
obter_ultimo_sinc
encontrar_closest_zip
# DOC-END: SYNC-MAIN-AUTO-SELECTION

# DOC-SECTION: SYNC-MAIN-REFTEK-SDS-SHORTCUT
# Atalho: se ZIP já vier com /sds/ (Reftek), apenas extrai e publica
if [[ "$station_type" == "reftek" ]]; then
  local_year_last="${last_date:0:4}"
  local_julian_last="${last_date:4:3}"
  data="$(date -d "$local_year_last-01-01 +$((10#${local_julian_last}-1)) days" +%Y%m%d)"
  target_dir="$base_dir/${ESTACAO_ESCOLHIDA}_${data}"
  mseed_dir="${ESTACAO_ESCOLHIDA}_${data}_MSEED"

  if unzip -l "$closest_zip" 2>/dev/null | awk 'NR>3 && NF>=4 {print $4}' | grep -q "/sds/"; then
    echo "→ ZIP já vem em SDS/MiniSEED; extraindo em $target_dir e pulando reftek2mseed"
    run_cmd mkdir -p "$target_dir"
    run_cmd unzip -j -qq "$closest_zip" -d "$target_dir/$mseed_dir"

    pushd "$target_dir" >/dev/null
      echo "   - Dataselect ..."
      run_cmd dataselect -Ps -Sd -A sds/%Y/%n/%s/%c.D/%n.%s.%l.%c.D.%Y.%j "$mseed_dir"/*
      echo "   - sdsClone.py ..."
      run_cmd sc3 exec /home/suporte/bin/sdsClone.py -s sds/ -l "${ESTACAO_ESCOLHIDA}_${data}.log"
      echo 's' | run_cmd /home/suporte/bin/workthisout.sh --nostop
    popd >/dev/null

    finalizar_log
    exit 0
  fi
fi
# DOC-END: SYNC-MAIN-REFTEK-SDS-SHORTCUT

# DOC-SECTION: SYNC-MAIN-DISPATCH
dispatch_processing() {
  case "$station_type" in
    reftek) processar_reftek ;;
    raspberry) processar_raspberry ;;
    *) echo "[ERRO] Tipo de estação desconhecido: $station_type" >&2; exit 1 ;;
  esac
}

dispatch_processing
finalizar_log
exit 0
# DOC-END: SYNC-MAIN-DISPATCH
