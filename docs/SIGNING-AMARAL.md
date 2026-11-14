# Assinatura fixa BOTWDroid Amaral

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
