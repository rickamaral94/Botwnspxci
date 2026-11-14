# Assinatura fixa BOTWDroid Amaral

## Chave atual (desde 14/11/2026, `0.3.4-beta-amaral.4`, versionCode 42)

Decisão de Amaral em 14/11: a chave criada nesse dia passa a ser a fixa a partir da Amaral.4. A Amaral.3 (41) ainda
foi assinada com a chave de 11/11. Não gere outra chave para atualizações.

- Pacote: `com.botwrecomp.android`
- Alias: `botwdroid-amaral` (RSA 4096, PKCS12, válida até 2056)
- **Certificado SHA-256: `56ac29d83a172ea298757d2e565949c6709fe43225235287ab64c064f23b1189`**
- Assinatura v3 (`apksigner`), com `minSdk` 30.
- **O backup** (`BOTWDroid-Amaral-chave-2026-11-14.zip`, com o `.p12` e o `keystore.properties`) foi entregue a Amaral.
  - Não publique nem faça commit do backup nem das senhas.
  - Para o Gradle, restaure-o fora do repositório: o `.p12` e o `~/.botwrecompandroid/keystore.properties`, com
    `storeFile` apontando para o `.p12`.
- O build `release` falha quando a chave está ausente. Não existe fallback para uma chave de debug.
- Antes de publicar, verifique o APK e compare o SHA-256 do certificado com o registrado acima.

**Migração:**
- As Amaral.1, .2 e .3 usam o certificado `bef64ef9aab3164036dfb4d42118ae41cbb198cb89a538bc68123bce09448bd8`. A
  Amaral.4 **não instala por cima delas**: é preciso desinstalar antes.
- A desinstalação apaga os dados do app (saves, configurações, drivers e arquivos do jogo importados). Exporte os
  saves antes (Configurações > Saves > Exportar) e guarde a pasta do jogo.
- Da Amaral.4 em diante, as versões mantêm o mesmo pacote, o mesmo certificado e um `versionCode` crescente.

## Chave anterior (11/11/2026, Amaral.1, .2 e .3)

A partir da versão `0.3.4-beta-amaral.1` (`versionCode 39`), usar sempre a chave RSA 4096 criada em 11 de novembro de 2026. Nunca gerar uma chave temporária para uma atualização.

- Pacote: `com.botwrecomp.android`
- Alias: `botwdroid-amaral`
- Certificado SHA-256: `bef64ef9aab3164036dfb4d42118ae41cbb198cb89a538bc68123bce09448bd8`
- Backup privado persistente: `BOTWDroid-Amaral-Assinatura-Fixa-BACKUP.zip`, Library ID `libfile_0c75b9ed2f1081918cc5d08a9b798855`.
- O backup contém a chave PKCS12, o certificado e as credenciais em `signing.json`. Não publicar nem commitar o backup ou suas credenciais.
- Para Gradle, restaurar o backup fora do repositório e configurar `~/.botwrecompandroid/keystore.properties` com `storeFile`, `storePassword`, `keyAlias` e `keyPassword`.
- O build `release` falha quando a chave fixa está ausente; não existe mais fallback silencioso para uma chave debug.
- Antes de publicar, verificar o APK e comparar o SHA-256 do certificado com o registrado acima.

APKs anteriores usam certificados diferentes e exigem reinstalação. Faça backup dos saves e configurações antes da migração. Depois da primeira instalação assinada por esta chave, versões futuras devem manter o mesmo pacote, certificado e `versionCode` crescente.
