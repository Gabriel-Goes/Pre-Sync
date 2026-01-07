# SYNC — Sincronização e Publicação em SDS

O **SYNC** padroniza a sincronização de dados de estações **REFTEK RT130** e **Raspberry Shake** para a estrutura **SDS** (SeisComP), com rastreabilidade via logs e checagens de integridade.

:::{toctree}
:hidden:
:maxdepth: 2

guia_rapido
guia_operador
visao_geral_do_fluxo
api/sync
_modules/SYNC.sh
fluxo_reftek
fluxo_raspberry
estrutura_diretorios
flags_cli
logs_e_rastreabilidade
troubleshooting
dependencias
:::

::::{grid} 2
:gutter: 2

:::{grid-item-card} Guia rápido
:link: guia_rapido
:link-type: doc

Comandos essenciais para sincronizar e publicar no SDS.
:::

:::{grid-item-card} Guia do operador
:link: guia_operador
:link-type: doc

Procedimento operacional (REFTEK e Raspberry) e validações.
:::

:::{grid-item-card} Visão geral do fluxo
:link: visao_geral_do_fluxo
:link-type: doc

Pipeline completo: entrada (arquivos brutos) → saída (SDS) + logs.
:::

:::{grid-item-card} Fluxo REFTEK (RT130)
:link: fluxo_reftek
:link-type: doc

Extração, checagens horárias, SOH, rt2ms, dataselect e merge.
:::

:::{grid-item-card} Fluxo Raspberry Shake
:link: fluxo_raspberry
:link-type: doc

Fluxo direto para MSEED e merge final na SDS.
:::

:::{grid-item-card} Estrutura de diretórios
:link: estrutura_diretorios
:link-type: doc

Onde entram os ZIP/RAR, onde saem logs e como o SDS é preenchido.
:::

:::{grid-item-card} Flags (CLI)
:link: flags_cli
:link-type: doc

Opções suportadas pelo `SYNC.sh` (`-p`, `-e`, `-y`, `-f`).
:::

:::{grid-item-card} Logs e rastreabilidade
:link: logs_e_rastreabilidade
:link-type: doc

Como interpretar `_sync.log`, `_r2m.log` e `RT130_*.log`.
:::

:::{grid-item-card} Troubleshooting
:link: troubleshooting
:link-type: doc

Causas prováveis e ações para falhas comuns.
:::

:::{grid-item-card} Dependências
:link: dependencias
:link-type: doc

Pacotes Python e binários exigidos pelo pipeline.
:::

::::
