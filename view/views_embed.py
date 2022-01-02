import asyncio, os, sys
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

import discord

from functions._local_datetime import local_dt
from functions._image_upload import image_upload
from functions.a_threads import Threads


@dataclass
class EmbedView:
    '''Créer un embed.'''
    bot:         discord
    salon_id:    int
    title:       str
    ctx:         discord.TextChannel = None
    message_id:  int = None
    description: str = '\u200b'
    footer:      str = None
    color_hex:   int = None
    url:         str = None
    fields:      list = None
    image_path:  str = None
    file:        tuple = None

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
            embed = discord.Embed(title=f'**{self.title}**',
                                  description=f'*{self.description}*',
                                  url=self.url,
                                  color=self.color_hex)
            if self.fields:  # [(Name, Value, True/False)]
                [embed.add_field(name=f'**{n}**', value=f'{v}\n\u200b', inline=i) for n, v, i in self.fields]
            embed.set_footer(text=self.footer)
            embed.timestamp = await local_dt()
            return embed
        except Exception as err:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            raise Exception(err, exc_type, fname, exc_tb.tb_lineno)

    async def upload(self, image_path) -> str:
        """Téléverser l'image sur un serveur distant et obtenir son url l'URL.

        Args:
            image_path (Path): Chemin de l'image.

        Returns:
            upload_link (str): URL de l'image.

        Raises:
            Exception générale.
        """
        upload_link = '-'
        # On essaie d'envoyer l'image 5 fois au maximum
        try:
            if isinstance(image_path, str): image_path = Path(image_path)
            upload_link = await image_upload(image_path)
        except Exception as err:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            raise Exception(err, exc_type, fname, exc_tb.tb_lineno)
        else:
            print(upload_link)  # Todo : Logger
        return upload_link


    async def edit(self) -> None:
        """Edition du message.

        Returns:
            None

        Result:
            Édite le message souhaité.

        Raises:
            Exception générale.
        """
        msg = await self.bot.get_channel(self.salon_id).fetch_message(self.message_id)
        async with msg.channel.typing():
            embed_sans_image = await self.create_embed()  # Créer l'embed sans image
            embed = deepcopy(embed_sans_image)                 # Puis l'embed avec image

            if self.image_path is not None:
                image_url = Threads(self.upload(self.image_path))
                embed.set_image(url=image_url())

            try:
                await msg.edit(content=None, embed=embed)
            except Exception as err:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                await msg.edit(content=None, embed=embed_sans_image)
                raise Exception(err, exc_type, fname, exc_tb.tb_lineno)
            finally:
                await asyncio.sleep(0.2)

    async def send(self) -> None:
        """Publie un nouveau message.

        Returns:
            None

        Result:
            Publie le message souhaité dans un salon défini.

        Raises:
            Exception générale.
        """
        channel = self.ctx.channel
        async with channel.typing():
            embed_sans_image = await self.create_embed()  # Créer l'embed sans image
            embed = deepcopy(embed_sans_image)  # Puis l'embed avec image

            if self.image_path is not None:
                image_url = Threads(self.upload(self.image_path))
                embed.set_image(url=image_url())

            if self.file is not None:
                file_discord = discord.File(self.file[0], filename=self.file[1])

            try:
                await channel.send(content=None, embed=embed, file=file_discord)
            except Exception as err:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                await channel.send(content=None, embed=embed_sans_image)
                raise Exception(err, exc_type, fname, exc_tb.tb_lineno)
            finally:
                await asyncio.sleep(0.2)
