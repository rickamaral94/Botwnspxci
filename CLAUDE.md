# Revisão do BOTW

Abra o [histórico de testes](docs/logs/README.md) e leia as entradas relacionadas à build ou ao sintoma em revisão. Confira o APK, a versão do jogo, o modo de execução, o driver e as condições de coleta. Compare FPS reais e apresentados separadamente.

Se uma hipótese estiver em aberto, indique qual teste consegue verificá-la. Ao revisar ou executar uma nova rodada, acrescente ao registro a data, o parecer, a evidência conferida e o próximo passo. Preserve as observações anteriores quando novas evidências mudarem uma conclusão. Referencie o caminho e o commit do registro na issue ou no PR relacionado.

Quando uma coleta sugerir gargalo ou regressão do driver, consulte a [seção Turnip](docs/logs/TURNIP.md). Registre a identidade do ELF carregado e o teste que separa o custo do app, da GPU e do driver antes de propor uma mudança no Amaral Adreno Tools.

Para implementar os ajustes pendentes de ports de PC e compilar a próxima candidata, consulte a [passagem da Amaral.2](docs/logs/2026-11-12-handoff-claude-ajustes-pc.md). Ela indica a ordem, os pontos de código, os testes e a verificação do APK.
