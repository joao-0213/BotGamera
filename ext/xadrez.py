from discord.ext import commands
import chess
import discord
import asyncio
from typing import Optional, Union
import random
import yaml
import logging
from cairosvg import svg2png
import chess.svg
import chess.engine
from discord.ext import menus

logging.basicConfig(level=logging.INFO)

brd = {}
alias = {}
channels = {}

class Chess(commands.Cog):

    def __init__(self, client):
        logging.info("Carregando engine do xadrez")
        self.client = client
        self.engine = chess.engine.SimpleEngine.popen_uci("stockfish.exe")
        logging.info("engine do xadrez carregada!")


    @commands.command(aliases=["xadin"])
    @commands.bot_has_permissions(manage_channels=True)
    async def xadrez_iniciar(self, ctx, userplayer: Union[discord.Member, str]):
        """
        Cria uma partida de xadrez.
        O oponente pode ser o computador ou um membro do servidor.
        """
        client = self.client

        if ctx.author.id not in alias.keys() and ctx.author.id not in alias.values():
            if userplayer != ctx.author: #and userplayer != client.user.id:
                if userplayer != "computador" and isinstance(userplayer, discord.Member):
                    mensagem = await ctx.send(f'Ok, agora aguarde que o usuário {userplayer.mention} reaja à esta mensagem.')
                    await mensagem.add_reaction("👍")
                    def checkreaction(reaction, user):
                        return user == userplayer and str(reaction.emoji)  == '👍' and reaction.message == mensagem
                    try:
                        reaction, user = await client.wait_for("reaction_add",
                                                 check=checkreaction,
                                                 timeout=120)

                    except asyncio.TimeoutError:
                        await ctx.send("Oh não! O usuário não reagiu a tempo.")
                        return
                    else: pass

                mentions = f"{ctx.author.mention} "
                dificuldade = 0
                if userplayer != 'computador':
                    mentions += f" {userplayer.mention} "
                else:
                    userplayer = ctx.me
                    difficultylist = {"facinho" : 0, "fácil" : 5, "médio" : 10, "difícil" : 15, "hardicori" : 20}
                    await ctx.send("Qual dificuldade você deseja:\n Facinho, fácil, médio, difícil ou hardicori?")
                    def check(message):
                        msgcon = message.content.lower() in difficultylist.keys()
                        return message.author.id == ctx.author.id and message.channel == ctx.channel and msgcon
                    try:
                        message = await client.wait_for("message",
                                                        check=check,
                                                        timeout=30.0)
                    except asyncio.TimeoutError:
                        await ctx.send("Oh não! VocÊ demorou muito para responder. :pensive:")
                        return
                    
                    else:
                        content = message.content.lower()
                        dificuldade = difficultylist[content]
                channel = channels[userplayer.id] = await self.create_channel(ctx, userplayer)
                await channel.send(f"{mentions} Que os jogos comecem!")
                rdm = random.randint(1, 2)

                if rdm == 1:
                    black = userplayer.id
                    white = ctx.author.id
                else:
                    white = userplayer.id
                    black = ctx.author.id

                alias[ctx.author.id] = userplayer.id
                alias[userplayer.id] = userplayer.id
                brd[userplayer.id] = chess.Board('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'), white, black, dificuldade

                color = "branco" if white == ctx.author.id else "preto"

                await channel.send(f"{ctx.author.mention} Você é o {color}")
                await self.imageboard(ctx, list(brd[alias[ctx.author.id]])[0])
                logging.info("Nova partida de xadrez criada.")

        else:
            await ctx.reply('Você já tem uma partida em andamento.')

    async def create_channel(self, ctx, userplayer):
        # cria o canal do xadrez.
        ov = {
            ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
            ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            ctx.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True)
        }

        display = "CPU"
        if userplayer is not None and isinstance(userplayer, discord.Member):
            ov[userplayer] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            display = userplayer.display_name
        category = discord.utils.get(ctx.guild.channels, name='Xadrez')
        if category is None:
            category = await ctx.guild.create_category_channel('Xadrez')
        channel = await ctx.guild.create_text_channel(f"xadrez-{ctx.author.display_name}-{display}",
                    overwrites=ov, topic="cu", category= category)
        return channel

    async def imageboard(self, ctx, tab, move= None):
        print(tab.fen())
        square = None
        if tab.is_check():
            pieces = tab.pieces(piece_type=chess.KING, color=tab.turn)
            for piece in pieces:
                square = piece
        a = chess.svg.board(board=tab, size=800, lastmove=move, check=square)
        channel = channels[alias[ctx.author.id]]

        svg2png(bytestring=a, write_to='outputboard.png')
        file = discord.File('outputboard.png')
        embed = discord.Embed(color=ctx.guild.me.top_role.color)
        embed.set_image(url= "attachment://outputboard.png")
        embed.set_footer(text=" Utilize ,xadrez <coordenada inicial> <coordenada final> para jogar.\nUtilize ,xadrez_finalizar para desistir.")
        await channel.send(file = file, embed= embed)
        if tab.is_game_over() == False:
             turn = self.turn(ctx)
             if tab.is_check():
                 await channel.send('https://cdn.discordapp.com/attachments/597071381586378752/796947748401446952/ezgif-2-9143b9b40c89.gif')
             await channel.send(f'É a vez de <@{turn}>')
             if turn == ctx.me.id:
                async with channel.typing():
                    while True:
                        try:
                            result = self.engine.play(tab, chess.engine.Limit(time=5), options={'Skill Level': list(brd[alias[ctx.author.id]])[3]})
                            tab.push(result.move)
                            await self.imageboard(ctx, tab, result.move)
                            break
                        except:
                            continue
        else:
            if tab.is_checkmate():
                await channel.send("Xeque-mate!")

            elif tab.is_stalemate():
                await ctx.send("Rei afogado!")
            elif tab.is_insufficient_material():
                await ctx.send("Material insuficiente!")
            if tab.result() == '1-0':
                await ctx.send(embed= discord.Embed(title=f"Partida finalizada", description= f'<@{list(brd[alias[ctx.author.id]])[1]}> foi o vencedor. Parabéns!').set_image(url='https://img1.recadosonline.com/713/006.gif'))
            elif tab.result() == '0-1':
                await ctx.send(embed= discord.Embed(title=f"Partida finalizada", description= f'<@{list(brd[alias[ctx.author.id]])[2]}> foi o vencedor. Parabéns!').set_image(url='https://img1.recadosonline.com/713/006.gif'))
            elif tab.result() == '1/2-1/2':
                await ctx.send(embed= discord.Embed(title= 'Temos um empate!', description= 'GG, peguem seus troféus de empate'))
            await self.end_match(ctx)

    async def end_match(self, ctx, winner=None):
        # lógica compartilhada quando uma partida é encerrada.

        try:
            channel = channels[alias[ctx.author.id]]
        except KeyError:
            logging.warn("Não foi possível pegar o canal onde a partida aconteceu.")
            return
        if winner != None:
            if isinstance(winner, int):
                winner = ctx.guild.get_member(winner)
            await channel.send(embed= discord.Embed(title=f"Partida finalizada", description= f'{winner.mention} foi o vencedor. Parabéns!').set_image(url='https://img1.recadosonline.com/713/006.gif'))
        await asyncio.sleep(60)
        await channel.delete()

        user1 = list(brd[alias[ctx.author.id]])[1]
        user2 = list(brd[alias[ctx.author.id]])[2]
        del brd[alias[ctx.author.id]]
        del alias[user1]
        del alias[user2]
        del channels[alias[ctx.author.id]]

    def turn(self, ctx):
        brdauth = list(brd[alias[ctx.author.id]])[0]
        if brdauth.turn == chess.WHITE:
            turn = list(brd[alias[ctx.author.id]])[1]
        if brdauth.turn == chess.BLACK:
            turn = list(brd[alias[ctx.author.id]])[2]
        return turn

    @commands.command(aliases=["xad"])
    async def xadrez(self, ctx, coord1, coord2):
        turn = self.turn(ctx)
        brdauth = list(brd[alias[ctx.author.id]])[0]
        try:
            
            if turn == ctx.author.id:
                Nf3 = chess.Move.from_uci(coord1 + coord2)
                if Nf3 in brdauth.legal_moves:
                    brdauth.push(Nf3)
                    await self.imageboard(ctx=ctx, tab=brdauth, move=Nf3)
                else:
                    await ctx.reply('Este movimento não é permitido.')
            else: await ctx.reply('Espera sua vez de jogar mano')
        except KeyError:
            await ctx.reply("Você não tem uma partida em andamento. Inicie uma com `,xadrez_iniciar`.")

    @commands.command(aliases=["xadfi"])
    async def xadrez_finalizar(self, ctx):
        try:
            reply = await ctx.reply("Você dará a vitória para o oponente, deseja mesmo finalizar o jogo?")

            await reply.add_reaction("👍")

            def checkreaction(reaction, user):
                return user == ctx.author and str(reaction.emoji) == '👍' and reaction.message == reply

            try:
                reaction, user = await self.client.wait_for("reaction_add",
                                                       check=checkreaction,
                                                       timeout=120)
            except asyncio.TimeoutError:
                pass
            else:
                    if ctx.author.id == list(brd[alias[ctx.author.id]])[1]:
                        await self.end_match(ctx, list(brd[alias[ctx.author.id]])[2])
                    else:
                        await self.end_match(ctx, list(brd[alias[ctx.author.id]])[1])

        except KeyError:
            await ctx.reply("Você não tem uma partida em andamento. Inicie uma com `,xadin`.")

def setup(client):
    client.add_cog(Chess(client))