# 2026-11-24 — Ports de Switch para Android: o que aprender com os mais maduros

Pedido do Rick: avaliar o port de Switch para Android mais maduro (o Portário lista os recomps) e trazer o que serve
para tirar desempenho do Odin 2 Portal (QCS8550, Adreno 740).

## Quem é quem

Contagem pelos clones de 24/11 (`git rev-list`).

| Port | Commits | Jogos | Licença | Aparelhos de referência | Observação |
| --- | --- | --- | --- | --- | --- |
| **BOTWRecompAndroid** (mamcjr, o nosso upstream) | 672 (43 tags) | 1 | MIT | vários | a base desta build |
| **Peanuts Native** (igawa6) | 618 em 10 dias (8 tags) | **59** | **GPL-3.0** | AYN Thor | o mais amplo: um runtime para muitos jogos. **Só ideias, nenhum código** |
| **TOTKDroid** (mamcjr) | 515 (9 tags) | 1 | MIT | POCO F7 Ultra (8xx) | mesma arquitetura do BOTW: o que ele faz encaixa direto |
| **totk-android** (AurelioB) | 310 | 1 | MIT | **AYN Thor = QCS8550 / Adreno 740, o SoC do Odin 2** | o mais polido no nosso hardware |
| LASRecompAndroid (mamcjr) | 291 (27 tags) | 1 | MIT | — | Mali, CI |
| letsgo-recomp | 256 | 1 | — | — | — |
| Swap2-Native (mamcjr) | 23 (20 tags) | Switch 2 | — | — | ideias para tilers e para o driver da Qualcomm |
| EoWRecomp, SMO-android-port | 31 / 19 | 1 | — | — | ainda no começo |

**Mais maduro para o nosso caso:**
- **totk-android**, no mesmo SoC do Odin: TOTK, mais pesado que o BOTW, **fica cravado em 30,0 fps no AYN Thor**,
  com p95 de 38,9 ms e 1 quadro acima de 50 ms em 1.200 (README, Hateno).
- **TOTKDroid**, pela mesma arquitetura.
- **Peanuts**, pela amplitude, mas é GPL.

## O que eles fazem e nós não, por ordem de ganho esperado no Odin

| # | Técnica | De onde | Estado aqui |
| --- | --- | --- | --- |
| 1 | **Leitura direta dos alvos no Automático da Adreno 7xx** (o 740 tinha ~10.000 cópias/s no primeiro santuário; o jogador relatou "muito mais suave") | TOTKDroid `12a6d69`, #48 | **Amaral.8** (no Odin as cópias eram 17 de 38,5 ms por quadro) |
| 2 | **Lista de pipelines distribuída no APK**, conferida ao gerar o APK assinado, e cache novo pré-aquecido | Peanuts (`bc4b1d2`, `572a277`, seeds por jogo), totk-android (lista de ~25 mil shaders), SavageWind (8.561 pipelines) | **Amaral.8**: a estrutura e a ferramenta (`tools/pipe_warm_info.py`); falta a lista das sessões do Rick |
| 3 | **Gravação dos comandos Vulkan em várias threads** (command buffers secundários por "seção", montados num primário) | totk-android (`4a805ed`, `a50604c`, `0fc0414`) | não temos: a thread de render faz ~13–15 ms de CPU por quadro sozinha. **O maior ganho de CPU possível, e um projeto grande** |
| 4 | **Perfis por aparelho**: o primeiro início escolhe o preset testado para o chip | totk-android | não temos: o Odin poderia vir com tudo configurado (leitura direta, LRZ, taxa, resolução) |
| 5 | **Hash de texturas grandes em 4 threads** (a thread de render caiu de 27,5% para 24,1% das amostras) | TOTKDroid `99735c5` | não temos. Pequeno e seguro: próximo candidato |
| 6 | **Micro-cortes na thread de render** (tabela de formatos filtráveis, invalidação de snapshot pulada sem snapshot): ~2,4% | TOTKDroid `2bce81c` | não temos. Pequeno |
| 7 | **Piso de clock da GPU pelo KGSL**: o Odin mediu 611–680 MHz de média | Peanuts; o TOTKDroid testou (`11826ea`): sem ganho no 8 Elite | não temos. **Vale um A/B no Odin**, que é outro kernel |
| 8 | **Pipelines de compute feitos no início** (só no Turnip) | Peanuts `bfa8969`, `8bd484c` | não temos. Médio |
| 9 | **Draw pulado só em alvo desenhado todo quadro**; alvo novo espera | Peanuts `4b830f1` | já temos parecido (`rt_one_off`, `rt_is_persistent`) |
| 10 | Frame lag a 60 fps nativo no Odin | totk-android `8e4ddf0` | já temos (Sync lag) |
| 11 | FPCR do host nas threads do Vulkan | Peanuts / Swap2 | só muda no driver da Qualcomm; no Turnip, nada (TOTKDroid mediu) |
| 12 | Reduções opcionais (tamanho do shadow map, plano distante) | TOTKDroid `199f945` (endereços do TOTK) | sem ganho lá, que é limitado pela CPU; aqui precisaria dos endereços do BOTW |

## Conclusão e próximo passo

- **Amaral.8 leva os itens 1 e 2.** Com a lista do Rick, o item 2 vira a lista dentro do APK.
- **Próxima rodada:** 5 e 6, que são pequenos e só de CPU, mais um A/B do 7 no Odin.
- **Projeto à parte:** o 3, gravação em várias threads. É o que separa o totk-android (30 cravados num 740) do
  resto, e vale um plano próprio.
- O código do Peanuts é GPL-3.0: só as ideias entram, reescritas.
