import asyncio, datetime, imageio, os, sys
from dataclasses import dataclass
from pathlib import Path

from discord.ext import commands
import pandas as pd

from functions._local_datetime import local_dt
from functions._timer import timer
from model import covid_vaccin_age
from view import views_embed
from settings import SALON_INFO_COVID, MESSAGES_IDS_COVID, ROLE_CS


TITRE_COURT = 'Vaccin_Age'
TITRE_LONG =  'Vaccination par âge en France · IDF · 92'
MESSAGE_ID =  MESSAGES_IDS_COVID[6]
DESCRIPTION = 'actualisé vers 20h-23h\n(du lundi au vendredi)'
URL =         'https://solidarites-sante.gouv.fr/grands-dossiers/vaccin-covid-19/'
PATH_DIR =    covid_vaccin_age.PATH_DIR
DICT_CSV =    {'fra': ('https://www.data.gouv.fr/fr/datasets/r/54dd5f8d-1e2e-4ccb-8fb8-eac68245befd', 'FR', '#70E6E4', 'en', 'France'),
               'reg': ('https://www.data.gouv.fr/fr/datasets/r/c3ccc72a-a945-494b-b98d-09f48aa25337', 11, '#c7faff', 'en', 'Île-de-France'),
               'dep': ('https://www.data.gouv.fr/fr/datasets/r/83cbbdb9-23cb-455e-8231-69fc25d58111', 92, '#E3FFFF', 'dans les', 'Hauts-de-Seine')}

@dataclass()
class VaccinCtrl(commands.Cog):
    bot: object = None

    dict_csv = DICT_CSV
    liste_obj = list()  # Chemins pour le gif

    async def main(self) -> None:
        """Génère les DF et les objets, puis lance le traitement des DF et des graphiques."""

        for key, val in self.dict_csv.items():
            df_vaccin = pd.read_csv(val[0], sep=';', parse_dates=['jour'], low_memory=False)

            # Modifier le type de données par colonne.
            dict_types = dict()
            for col in list(df_vaccin.columns):
                if col == key:                dict_types[col] = 'object'  # Dans 'dep', mélange object et int8.
                elif col == 'clage_vacsi':    dict_types[col] = 'int8'
                elif col == 'jour':           dict_types[col] = 'datetime64[ns]'
                elif col.startswith('n_'):    dict_types[col] = 'int8'
                elif col.startswith('couv_'): dict_types[col] = 'float64'
            df_vaccin = df_vaccin.astype(dict_types, copy=False)

            # Filtrer sur les seules données utilisées
            df_vaccin = df_vaccin[df_vaccin[key].isin({str(val[1]), val[1]})]
            df_vaccin.drop(df_vaccin[df_vaccin['jour'] <= pd.Timestamp((datetime.datetime.now() - datetime.timedelta(days=60)))].index, inplace=True)

            # Lancement du modèle
            vaccin = covid_vaccin_age.VaccinModele(df_vaccin, *val[2:])
            # Ajout à la liste des images PNG en vue de générer le Gif.
            self.liste_obj.append(await vaccin())
            # Ajout du jour de la màj
            self.jour = vaccin.jour

    async def vaccin_age_gif(self, path_=PATH_DIR) -> Path:
        """Réunir les PNG en un seul Gif."""

        fp_out_path = os.path.join(path_, 'images')
        fp_out = os.path.join(fp_out_path, 'Vaccination.gif')

        # Créer le fichier et le dossier s'ils n'existent pas
        if not os.path.exists(fp_out_path): os.mkdir(fp_out_path)
        if not os.path.exists(fp_out):      open(fp_out, 'x')

        # Aggréger les images en Gif
        images = list()
        for filename in self.liste_obj:
            images.append(imageio.imread(filename))
            imageio.mimsave(fp_out, images, duration=7)

        return fp_out

    async def vaccin_age_launch(self) -> None:
        """Créer les PNG puis le Gif."""

        await self.main()
        fp_out = await self.vaccin_age_gif()
        setattr(self, 'image_path', fp_out)
        await self.publi_embed(fp_out)

    async def publi_embed(self, image_path) -> None:
        """Edition du message."""

        embed = views_embed.EmbedView(bot=self.bot,
                                      salon_id=SALON_INFO_COVID,
                                      message_id=MESSAGE_ID,
                                      title=TITRE_LONG,
                                      description=DESCRIPTION,
                                      fields=None,
                                      url=URL,
                                      footer=f"Données du {self.jour}\nSanté publique France",
                                      image_path=image_path,
                                      color_hex=0x70E6E4)
        await embed.edit(); del embed; await asyncio.sleep(60 * 30)

    @timer(TITRE_COURT)
    async def check_update(self) -> None:
        """Méthode appelée par le programme en boucle.
        Elle vérifie que les dernières données sont disponibles.

        Note:
            La date des dernières données correspond au jour précédent.
        """

        try:
            url = self.dict_csv['fra'][0]
            setattr(self, 'vaccination_fra', pd.read_csv(url, sep=';', parse_dates=['jour']))

            # On détermine si le jour des données du CSV (=la veille) correspond au jour recherché (=la veille).
            date_attendue = (dt_local_time - datetime.timedelta(days=1)).date()
            setattr(self, 'jour', date_attendue)
            date_obtenue = datetime.datetime.strptime(str(self.vaccination_fra['jour'].max()),
                                                          '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')  # Jour issu du CSV

            # Si ces deux jours ne correspondent pas, attendre 30 min puis relancer la requête.
            assert str(date_attendue) == str(date_obtenue), \
                (f'{TITRE_COURT} : La date demandée est indisponible. {date_attendue = }; {date_obtenue = }')

            # Si ces deux jours correspondent, la requête peut être lancée, et puis interrompue jusqu'à demain.
            await self.vaccin_age_launch()
            await asyncio.sleep(3600 * 6)  # 6 heures

        except AssertionError as err:
            raise AssertionError(err)

    @commands.command(brief='Vaccination par âge contre la Covid-19')
    @commands.check_any(commands.has_role(ROLE_CS))
    async def vaccin_age(self, ctx) -> None:
        """Lance le programme manuellement via une entrée utilisateur sur Discord.

        Note:
            La commande utilisateur est le nom de la fonction, pas d'alias ici.
        """

        await self.vaccin_age_launch()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        '''Envoi du nombre de vaccinés dans le salon # transport et infos.'''

        running = True
        while running:
            global dt_local_time
            dt_local_time = await local_dt()
            try:
                if 18 <= dt_local_time.hour <= 23 and dt_local_time.minute in {20, 50}:
                    await self.check_update()
            except Exception as err:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                print(TITRE_COURT, err, exc_type, fname, exc_tb.tb_lineno)
            await asyncio.sleep(55)


def setup(bot):
    bot.add_cog(VaccinCtrl(bot))


if __name__ == '__main__':
    pass
