# Deploy no Render

O bot é hospedado como um **Web Service gratuito** para que possa permanecer
ativo por meio de um monitor externo. O bot expõe apenas `GET /health`; ele
não tem painel web nem API pública.

> O Render não oferece Background Workers gratuitos. O arquivo
> `render.yaml` usa um Web Service no plano `free`, que hiberna após 15 minutos
> sem tráfego HTTP recebido.

## Antes do deploy

1. Suba este repositório para o GitHub, sem o arquivo `.env`.
2. Crie e verifique um backup do MongoDB.
3. No Discord Developer Portal, habilite **Server Members Intent** em
   *Bot > Privileged Gateway Intents*.
4. Convide o bot com os escopos `bot` e `applications.commands`. As
   permissões por tipo de servidor estão em [docs/bot-permissions.md](docs/bot-permissions.md).
5. Confirme que a CI do GitHub está verde. O Blueprint só faz deploy após
   esses checks passarem.

## Criar pelo Blueprint

1. No painel do Render, selecione **New + > Blueprint** e conecte o
   repositório.
2. O Render detectará o arquivo [render.yaml](render.yaml) e criará o serviço
   `uma-portal-bot` como Web Service gratuito.
3. Na tela de variáveis de ambiente, informe os valores abaixo. Nunca coloque
   tokens, URI do MongoDB ou outros segredos no Git.
4. Crie o serviço e acompanhe os logs até aparecer `Bot online as ...`.

O `render.yaml` instala as dependências fixadas em `docs/requirements.txt` e
inicia o processo com `python bot.py`. O bot abre `GET /health` na porta
definida automaticamente pelo Render em `PORT`, usa Python 3.12 e mantém
Rotection desativado em produção.

## Variáveis de ambiente

| Variável | Obrigatória | Valor de produção |
| --- | --- | --- |
| `DISCORD_TOKEN` | Sim | Token do bot no Discord Developer Portal. |
| `MONGODB_URI` | Sim | String de conexão do MongoDB/Atlas, com acesso liberado para o Render. |
| `MAIN_GUILD_ID` | Sim | ID numérico do servidor Uma Portal. |
| `BOT_ENV` | Não | `production` (já definido pelo Blueprint). |
| `ROTECTOR_ENABLED` | Não | `false` (já definido pelo Blueprint). |
| `ROTECTOR_API_KEY` | Só se Rotection for ativado | Chave do serviço Rotection. |
| `ROTECTOR_API_BASE_URL` | Não | Só altere se a URL padrão do Rotection mudar. |

Se o Atlas usar uma lista de acesso por IP, permita conexões originadas do
Render conforme a política de rede do seu cluster. Prefira um usuário MongoDB
exclusivo para o bot, com acesso apenas ao banco necessário.

## Monitor para manter o serviço ativo

Depois do primeiro deploy, copie a URL pública do Render, por exemplo:

```text
https://uma-portal-bot.onrender.com/health
```

Configure um monitor externo para fazer uma requisição **HTTP GET** a essa URL
a cada 5 a 10 minutos. UptimeRobot, Better Stack ou serviço equivalente podem
ser usados para isso. Não use `/robots.txt`: quando o serviço está suspenso,
o Render responde essa rota sem iniciar a aplicação.

O monitor não é uma garantia de disponibilidade: se ele parar, o bot hiberna
após 15 minutos e só volta quando receber uma nova requisição. O endpoint
retorna `200` com `discord_ready: true` depois que o bot conclui a conexão ao
Discord.

## Primeira publicação e comandos antigos

Se uma versão antiga do bot usava comandos globais, faça esta etapa **uma única
vez**, com a instância de produção parada. Execute em uma máquina confiável com
as mesmas três variáveis obrigatórias configuradas:

```powershell
python -m scripts.cleanup_global_commands --confirm-bot-stopped
```

Depois, inicie ou faça redeploy no Render. Não execute esse script como Build
Command, Start Command ou Pre-Deploy Command.

## Migrações de dados

Migrações não são executadas no startup. Quando uma release exigir uma,
agende uma janela de manutenção, pare o worker e siga o procedimento em
[docs/readme.md](docs/readme.md#deployment-checklist): preflight, backup
verificado, migração manual e validação antes de iniciar o bot novamente.

## Operação

- Para atualizar: envie um commit para a branch conectada; o Render faz deploy
  após a CI passar.
- Para alterar um segredo: atualize-o em **Environment** no Render e faça um
  redeploy. Não é necessário alterar o `render.yaml`.
- Para parar o bot: suspenda o Web Service no Render. Isso é necessário
  antes de executar tarefas de manutenção que pedem o bot parado.
- Os dados permanecem no MongoDB; o sistema de arquivos do Render não é usado
  para persistência.
