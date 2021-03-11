from discord.ext import commands
from PIL import Image, ImageFont, ImageDraw
from typing import Optional

import io
import discord
import aiohttp
import time

MEMEMAN_IMG = "https://i.ibb.co/4YmHZCm/cumm.png"
FONT_LIMIT = 31 # depende muito da fonte e do tamanho usado.

def splitlen(string, per):
    return [string[i : i + per] for i in range(0, len(string), per)]

class ImageCog(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

        self._avatar_cache = {}
        self._mememan_bytes = None

    async def fetch_mememan(self):
        if self._mememan_bytes is not None:
            return self._mememan_bytes

        async with aiohttp.ClientSession() as session:
            async with session.get(MEMEMAN_IMG) as request:
                self._mememan_bytes = await request.read()
                return self._mememan_bytes

    @commands.command()
    @commands.cooldown(1, 30, commands.BucketType.member)
    async def mememan(self, ctx, *, text: str):
        async with ctx.typing():
            image: Image.Image = Image.open(io.BytesIO(await self.fetch_mememan()))

            if len(text) > FONT_LIMIT:
                text = "\n".join(splitlen(text, FONT_LIMIT))

            # a gente vai soltar um JPG, e JPGs não suportam alpha.
            image = image.convert("RGB")
            image_draw = ImageDraw.Draw(image)

            font = ImageFont.truetype("assets/coolvetica.ttf", 45)

            image_draw.text((10,0), text, (10,10,10), font=font)
            image.save("mememan.jpg")

        with open("mememan.jpg", "rb") as file:
            timm = str(round(time.time()))
            await ctx.reply(file=discord.File(file, filename=timm + ".jpg"))

    def get_colors(self, image, colors=10, resize=150):
        if isinstance(image, bytes):
            image = io.BytesIO(image)
        image = Image.open(image)

        image = image.copy()
        image.thumbnail((resize, resize))

        palt = image.convert("P", palette=Image.ADAPTIVE, colors=colors)
        palette = palt.getpalette()
        color_counts = sorted(palt.getcolors(), reverse=True)
        colors = []

        for c in range(len(colors) + 1):
            palette_index = color_counts[c][1]
            dominant_color = palette[palette_index*3:palette_index*3+3]

            colors.append(tuple(dominant_color))

        return colors

    def save_palette(self, colors, swatchsize=20, outfile="palette.png"):
        num_colors = len(colors)
        palette = Image.new('RGB', (swatchsize*num_colors, swatchsize))
        draw = ImageDraw.Draw(palette)

        posx = 0
        for color in colors:
            draw.rectangle([posx, 0, posx+swatchsize, swatchsize], fill=color)
            posx = posx + swatchsize

        del draw
        palette.save(outfile, "PNG")

    @commands.command()
    @commands.cooldown(1, 30, commands.BucketType.member)
    async def domin(self, ctx, member: Optional[discord.Member]):
        """
        Pega a cor dominante do seu avatar ou do membro *member*.

        As vezes a cor retornada, pode parecer não ser precisa, mas é basicamente
        a cor com a maior quantidade de pixels coloridos com aquela cor, então
        pode variar com o tamanho da imagem.
        """
        avatar = (member or ctx.author).avatar_url

        colors = self.get_colors(await avatar.read())
        self.save_palette(colors)

        with open("palette.png", "rb") as fp:
            file = discord.File(fp, "palette.png")

        await ctx.reply(file=file)

    @commands.command()
    @commands.cooldown(1, 40, commands.BucketType.member)
    async def marry(self, ctx, user: discord.User, other_user: Optional[discord.User]):
        """
        Casa com alguém.
        """
        async with ctx.typing():
            if other_user is None:
                other_user = user
                user = ctx.author

            image: Image.Image = Image.open("assets/facebook.png")
            user_avatar: Image.Image = Image.open(io.BytesIO(await user.avatar_url.read()))
            other_user_avatar: Image.Image = Image.open(io.BytesIO(await other_user.avatar_url.read()))

            # o tamanho é um par de (largura,altura).
            # a posição é um par de (coord. x, coord. y)
            user_avatar = user_avatar.resize((534, 525))
            other_user_avatar = other_user_avatar.resize((534, 525))
            image.paste(user_avatar, (0,170))
            image.paste(other_user_avatar, (544,171))

            smol_user_avatar = Image.open(io.BytesIO(await user.avatar_url_as(format="png", size=64).read()))
            smol_user_avatar.resize((77,78))
            image.paste(smol_user_avatar, (56,35))

            draw = ImageDraw.Draw(image)
            font = ImageFont.truetype("assets/montserrat.ttf", 35)
            big_font = ImageFont.truetype("assets/montserrat.ttf", 45)

            draw.text((140, 45), f"{user.name} está com {other_user.name}.", (10,10,10), font=font)
            draw.text((165, 784), f"Casou-se com {other_user.name}", (10,10,10), font=big_font)

            image.save("fb.png")

        with open("fb.png", "rb") as fp:
            file = discord.File(fp, filename="facebook.png")
        await ctx.reply(file=file)

def setup(client):
    client.add_cog(ImageCog(client))
