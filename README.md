# FARM BOT — profissional v1

Bot de torneios para Discord em Python, com PostgreSQL e implantação no Railway.

## Recursos
- Painel no Discord com botões para inscrição, partidas e regulamento.
- Inscrição em dupla, dois jogadores diferentes.
- Modalidades por jogador: R$ 0,50, R$ 1, R$ 2, R$ 5, R$ 10, R$ 20 e R$ 50. O total da dupla é calculado automaticamente.
- PIX configurável e conferência/aprovação manual pela administração.
- Registro de referência do comprovante, fila de pagamentos e histórico no PostgreSQL.
- Criação e consulta de partidas.
- Regras com idade mínima padrão de 18 anos e política anti-cheat.
- Comandos administrativos protegidos.

## Segurança
Nunca compartilhe o token do Discord, senha do banco ou chave PIX. Cadastre segredos em Railway → serviço do bot → Variables. A aprovação PIX é manual: a equipe deve conferir o crédito no banco antes de aprovar. O bot não movimenta dinheiro nem confirma transferências automaticamente.

## Configuração Discord
Crie uma aplicação no Discord Developer Portal, adicione um Bot e convide-o com `bot` e `applications.commands`. Copie o token para `DISCORD_TOKEN` no Railway. Use o ID do servidor em `GUILD_ID` para sincronizar comandos rapidamente.

## Railway
1. Extraia este ZIP e envie os arquivos para um repositório GitHub.
2. No Railway, crie um serviço a partir do repositório.
3. Adicione as variáveis de `.env.example` em Variables.
4. Use `DATABASE_URL` do serviço PostgreSQL do Railway.
5. O comando de inicialização é `python -m farmbot`.
6. Faça Deploy e confira os logs. Ao conectar, aparecerá `FARM BOT conectado`.

## Comandos públicos
- `/painel`
- `/inscrever`
- `/comprovante`
- `/partidas`
- `/regras`

## Comandos de administração
- `/criar_partida`
- `/fila_pagamentos`
- `/aprovar_pix`
- `/reprovar_pix`
- `/configurar_pix`
- `/configurar_valores`

O valor selecionado é por jogador; uma dupla paga duas vezes esse valor. Teste em canal privado antes de abrir inscrições reais.
