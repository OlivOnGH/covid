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

async def upload_image_bdd(image_path, image_bdd_table, image_keep=False) -> str:
    """Téléverser l'image sur un serveur distant et obtenir son url l'URL.

    Returns:
        upload_link (str): URL de l'image.

    Raises:
        Exception générale.
    """
    try:
        # Si le chemin est un :str:, convertir en :Path:
        if not isinstance(image_path, Path):
            image_path = Path(image_path)

        # Si on souhaite conserver l'image, vérifier si l'URL est déjà présente dans la BDD.
        if image_keep:
            image_nom, image_ext = os.path.basename(image_path).rsplit('.', 1)
            image_dirpath = os.path.dirname(image_path)
            print('Vérification dans la BDD de l\'image : ', image_nom)
            from functions.f_mysql import Image
            image = Image(table=image_bdd_table,
                          name=image_nom,
                          endpoint=image_dirpath,
                          file_format=image_ext)
            return await image()  # URL

        # Sinon, téléverser l'image et retourner l'URL.
        return await image_upload(image_path)  # URL  # Todo : Logger

    except Exception as err:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        raise Exception(err, exc_type, fname, exc_tb.tb_lineno)


@dataclass
class EmbedView:
    '''Créer un embed.'''
    bot:                  discord
    salon_id:             int = None
    ctx:                  discord.TextChannel = None
    title:                str = '\u200b'
    message_id:           int = None
    description:          str = '\u200b'
    footer:               str = None
    color_hex:            int = None
    url:                  str = None
    fields:               list = None
    image_path:           Path = None
    image_keep:           bool = False
    image_bdd_table:      str = 'updates'
    thumbnail_path:       Path = None
    thumbnail_keep:       bool = False
    thumbnail_bdd_table:  str = 'updates'
    file:                 tuple = None

    __slots__ = '__dict__', 

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

    async def embed_prep(self) -> None:
        """Prépare l'embed, que ce soit pour self.edit ou self.send."""
        self.embed_sans_image = await self.create_embed()  # Créer l'embed sans image

        if self.image_path or self.thumbnail_path:
            if self.image_path:
                self.embed = deepcopy(self.embed_sans_image)  # Puis l'embed avec image
                self.image_url = Threads(upload_image_bdd(self.image_path, self.image_bdd_table, self.image_keep))
                image_url = self.image_url()
                print(f'{image_url = }')
                self.embed.set_image(url=image_url)

            if self.thumbnail_path:
                try:  # Copier l'embed qui pourrait déjà contenir une image.
                    self.embed = deepcopy(self.embed)
                except Exception as err:  # Sinon, cet embed n'existe pas, donc copier l'embed sans image.
                    self.embed = deepcopy(self.embed_sans_image)
                self.thumbnail_url = Threads(upload_image_bdd(self.thumbnail_path, self.thumbnail_bdd_table, self.thumbnail_keep))
                thumbnail_url = self.thumbnail_url()
                print(f'{thumbnail_url = }')
                self.embed.set_thumbnail(url=thumbnail_url)

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
