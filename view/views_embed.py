"""Ce module d'enveloppe (wrapper) facilite l'utilisation de la bibliothèque discord.py
et la migration ultérieure vers une nouvelle bibliothèque.
"""


import gc, os, sys
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

import discord

from functions._local_datetime import local_dt_sync
from functions._image_upload import image_upload
from functions.a_threads import Threads


verif_droit = lambda ctx, role: discord.utils.get(ctx.author.roles, id=role)

async def embed_edit_gc(*args, **kwargs) -> None:
    embed = EmbedView(*args, **kwargs)
    await embed.edit()
    del embed
    gc.collect()

async def embed_send_gc(*args, **kwargs) -> None:
    embed = EmbedView(*args, **kwargs)
    await embed.send()
    del embed
    gc.collect()


@dataclass
class EmbedView:
    '''Créer un embed.'''
    bot:         discord
    salon_id:    int = None
    ctx:         discord.TextChannel = None
    title:       str = '\u200b'
    message_id:  int = None
    description: str = '\u200b'
    footer:      str = None
    color_hex:   int = None
    url:         str = None
    fields:      list = None
    image_path:  Path = None
    file:        tuple = None

    __slots__ = ('__dict__', 'msg', 'embed_sans_image', 'embed', 'upload_link', 'image_url', 'file_discord', 'n', 'v', 'i')

    # def __post_init__(self):
    #     '''Convertir la couleur str() en int()'''
    #
    #     self.color_hex = int(f'0x{self.color_str[1:]}', 16)

    async def create_embed(self) -> object:
        """Crée et retourne un embed.

        Returns:
            embed (discord.Embed): L'objet embed.

        Raises:
            Exception générale.
        """
        try:
            self.embed = discord.Embed(title=f'**{self.title}**',
                                  description=f'*{self.description}*',
                                  url=self.url,
                                  color=self.color_hex)
            if self.fields:  # [(Name, Value, True/False)]
                [self.embed.add_field(name=f'**{self.n}**', value=f'{self.v}\n\u200b', inline=self.i) for self.n, self.v, self.i in self.fields]
            self.embed.set_footer(text=self.footer)
            self.embed.timestamp = local_dt_sync()
            return self.embed
        except Exception as err:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            raise Exception(err, exc_type, fname, exc_tb.tb_lineno)

    async def upload(self) -> str:
        """Téléverser l'image sur un serveur distant et obtenir son url l'URL.

        Returns:
            upload_link (str): URL de l'image.

        Raises:
            Exception générale.
        """
        try:
            if self.image_path:
                return await image_upload(Path(self.image_path))
            print('image_path', self.image_path)  # Todo : Logger
        except Exception as err:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            raise Exception(err, exc_type, fname, exc_tb.tb_lineno)

    async def embed_prep(self) -> None:
        self.embed_sans_image = await self.create_embed()  # Créer l'embed sans image

        if self.image_path:
            self.embed = deepcopy(self.embed_sans_image)  # Puis l'embed avec image
            self.image_url = Threads(self.upload())
            image_url = self.image_url()
            print('image_url', image_url)
            self.embed.set_image(url=image_url)
        else:
            self.embed = self.embed_sans_image

    async def edit(self) -> None:
        """Edition du message souhaité.

        Returns:
            None

        Raises:
            Exception générale.
        """
        self.msg = await self.bot.get_channel(self.salon_id).fetch_message(self.message_id)
        async with self.msg.channel.typing():
            await self.embed_prep()

            try:
                await self.msg.edit(content=None, embed=self.embed)
            except discord.errors.HTTPException as err:
                print(err)
                await self.msg.edit(content=None, embed=self.embed_sans_image)
            except Exception as err:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                await self.msg.edit(content=None, embed=self.embed_sans_image)
                raise Exception(err, exc_type, fname, exc_tb.tb_lineno)

    async def send(self) -> None:
        """Publie un nouveau message.

        Returns:
            None

        Result:
            Publie le message souhaité dans un salon défini.

        Raises:
            Exception générale.
        """
        try:
            self.msg = self.ctx.channel
        except AttributeError:
            self.msg = self.bot.get_channel(self.salon_id)

        async with self.msg.typing():
            await self.embed_prep()

            if self.file:
                self.file_discord = discord.File(self.file[0], filename=self.file[1])

            try:
                await self.msg.send(content=None, embed=self.embed, file=self.file_discord)
            except discord.errors.HTTPException as err:
                print(err)
                await self.msg.edit(content=None, embed=self.embed_sans_image)
            except Exception as err:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                await self.msg.send(content=None, embed=self.embed_sans_image)
                raise Exception(err, exc_type, fname, exc_tb.tb_lineno)
