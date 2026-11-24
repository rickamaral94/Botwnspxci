# 2026-11-24 — Release Amaral.17: a versão para jogar

**Pedido do Rick:** parar de lançar versões só para medir e entregar uma versão para jogar, com as melhorias já medidas
e sem medições pesando no desempenho.

## O que entra, e com que evidência

| Melhoria | Estado | Evidência |
| --- | --- | --- |
| Lista de pipelines pré-aquecidos, do aparelho e semente no APK | ligada | Amaral.10: pipelines novos em jogo ~820 → 99–151 por sessão; draws pulados ~10.000 → 83–397 |
| Pré-aquecimento do upstream | automático (ligado com Turnip) | Amaral.6/.10 |
| Leitura de alvos no lugar (Adreno 7xx/8xx) | automática | Amaral.7: −17 ms de cópias por quadro |
| UBWC nos alvos de cor (lista de formatos, Turnip 7xx) | ligada | Amaral.14/.15: −3 ms de GPU por quadro real a 4.500 draws (26,85 contra 29,0–30,3), segurou 29,8 fps reais. Uma sessão só; nenhuma cor trocada registrada. `LARECOMP_VK_RT_FORMAT_LIST=0` volta ao anterior |
| Máscara do HUD da geração de quadros pela metade do tamanho | ligada | Amaral.13: a máscara mais barata, sem perda no modelo |
| Conta de GPU por quadro correta (fins inválidos descartados) | ligada | Amaral.12 |
| Thread de fila | **desligada** | Amaral.12: sem ganho, p95 pior |
| Teste de profundidade antecipado | **desligado** | o Turnip já faz EARLY_Z nesses draws |
| Driver lab (bindless mask) | não usar | Amaral.14: sem ganho |

**Medições:** tudo que mede fica parado até "Medir desempenho" começar a gravar:
- a tabela por quadro real;
- a tabela de GPU por passe;
- a previsão do LRZ (agora também presa à medição; `LARECOMP_LRZ_TRACK=1` força);
- o registro cru de GPU.

Fora da medição sobram contadores de soma e duas leituras de relógio por envio, um custo desprezível.

## Configuração recomendada no Odin 2

| Opção | Valor |
| --- | --- |
| Driver | Turnip v5.9.19.1 (o padrão, não o lab) |
| Resolução | 1x (a cena de 900p do Switch; HUD em 1080p) |
| Upscaler | SGSR 1 |
| Anti-aliasing | SMAA (~1 ms; FXAA ~0,4 ms) |
| Taxa de quadros | 60 |
| Geração de quadros | 2x |
| Máscara do HUD | ligada |
| LRZ | ligado |
| Thread de fila | desligada |
| Variáveis do driver | nenhuma |

Com a geração de quadros, o jogo roda no modo de 30, e a geração leva a 60 na tela. O Lossless.dll é do usuário e não
vem no APK.

## Limites conhecidos

- **Trechos muito pesados.** Com mais de ~5.000 draws por quadro, a GPU fica perto do limite de 33 ms. Sem a UBWC, ela
  passava disso (25–27 fps reais). Com a UBWC, espera-se que caiba. A causa raiz é a GPU, no clock máximo de 680 MHz.
- **Travadas logo depois dos carregamentos:** os primeiros pipelines vistos pela primeira vez. A lista do aparelho
  cresce a cada sessão.
- **O LRZ ainda não funciona** (Amaral.16). A correção fica para depois dos dados das linhas `[lrz]`.

## Verificação

| Verificação | Resultado |
| --- | --- |
| `tools/run_host_tests.sh` | 16 de 16 |
| `assembleDebug` | compilou |
| No Odin | as melhorias acima foram medidas nas sessões citadas; a combinação final não foi rodada como um todo |
