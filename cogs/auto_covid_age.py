import datetime, imageio, os, sys
from dataclasses import dataclass
from pathlib import Path

import discord
from discord.ext import commands
import pandas as pd

from functions._local_datetime import local_dt
from functions._timer import timer
from model import covid_age
from view import views_embed
from settings import SALON_INFO_COVID, MESSAGES_IDS_COVID, ROLE_CS, PANDAS_SPF_SPECS, LISTE_DEPARTEMENTS_INT_STRF


DESCRIPTION = 'actualisé vers 20h-23h\n(du lundi au vendredi)'
URL =         'https://solidarites-sante.gouv.fr/grands-dossiers/vaccin-covid-19/'
PATH_DIR =    covid_age.PATH_DIR


@dataclass()
class AgeCtrl:

    bot: object = None
    liste_obj = list()  # Chemins pour le gif

    async def main(self, key, val) -> None:
        """Génère les DF et les objets, puis lance le traitement des DF et des graphiques."""

        df = pd.read_csv(val[0], **PANDAS_SPF_SPECS)

        # Modifier le type de données par colonne.
        dict_types = dict()
        for col in list(df.columns):
            if col == key:                dict_types[col] = 'object'  # Dans :dep:, mélange object et int8.
            elif col == self.CLAGE:       dict_types[col] = 'int8'
            elif col == 'jour':           dict_types[col] = 'datetime64[ns]'
            elif col.startswith('n_'):    dict_types[col] = 'int32'
            elif col.startswith('couv_'): dict_types[col] = 'float64'
        df = df.astype(dict_types, copy=False)

        # Filtrer sur les seules données utilisées
        zone_num = int(val[1]) if str(val[1]).isnumeric else str(val[1])
        # Un numéro de département peut être considéré comme :str: dans certains DF, et :int: dans d'autres.
        df = df[df[key].isin({str(zone_num), zone_num})]
        df.drop(df[df['jour'] <= pd.Timestamp((datetime.datetime.now() - datetime.timedelta(days=60)))].index, inplace=True)

        # Lancement du modèle
        modele = self.MODELE(df, *val[2:])
        # Générer l'image PNG et obtenir le chemin.
        image = await modele()
        # Ajout du jour de la màj
        self.jour = modele.jour
        return image

    async def main_multiples(self):
        for key, val in self.dict_csv.items():
            image = await self.main(key, val)
            # Ajout à la liste des images PNG en vue de générer le Gif.
            self.liste_obj.append(image)

    async def creer_gif(self, path_=PATH_DIR) -> Path:
        """Réunir les PNG en un seul Gif."""

        fp_out_path = os.path.join(path_, 'images')
        fp_out = os.path.join(fp_out_path, f'{self.GIF_NOM}.gif')

        # Créer le fichier et le dossier s'ils n'existent pas
        if not os.path.exists(fp_out_path): os.mkdir(fp_out_path)
        if not os.path.exists(fp_out):      open(fp_out, 'x')

        # Aggréger les images en Gif
        images = list()
        for filename in self.liste_obj:
            images.append(imageio.imread(filename))
            imageio.mimsave(fp_out, images, duration=self.ROTATION_TPS_GIF)

        return fp_out

    async def publi_embed(self, image_path) -> None:
        """Edition du message."""
        field = [('\u200b', f'Gif avec rotation toutes les {self.ROTATION_TPS_GIF} secondes.', False)]
        embed = views_embed.EmbedView(bot=self.bot,
                                      salon_id=SALON_INFO_COVID,
                                      message_id=self.MESSAGE_ID,
                                      title=self.TITRE_LONG,
                                      description=DESCRIPTION,
                                      fields=field,
                                      url=URL,
                                      footer=f"Données du {self.jour}\nSanté publique France",
                                      image_path=image_path,
                                      color_hex=self.COULEUR_HEX)
        await embed.edit(); del embed; await asyncio.sleep(60 * 30)

    async def launch_main_embed(self) -> None:
        """Créer les PNG puis le Gif."""

        await self.main_multiples()
        fp_out = await self.creer_gif()
        setattr(self, 'image_path', fp_out)
        await self.publi_embed(fp_out)

    async def commande_utilisateur(self, ctx, zone):
        """Lance le programme manuellement via une entrée utilisateur sur Discord.

                Args:
                    zone (:int:92, optionnel): Correspond au département. None par défaut.
                    None génère un Gif dans le salon dédié à la Covid-19,
                    tandis que zone(:int:) génère un PNG envoyé à l'utilisateur.

                Raises:
                    ValueError: Mauvais numéro de département.

                Note:
                    La commande utilisateur est le nom de la fonction, pas d'alias ici.
                """
        if not zone and discord.utils.get(ctx.author.roles, id=ROLE_CS):
            await self.launch_main_embed()

        elif str(zone) in LISTE_DEPARTEMENTS_INT_STRF:
            tuple_dpt = (self.DICT_CSV['dep'][0], zone, '#ebfffe', 'dans', str(zone))
            image = await self.main('dep', tuple_dpt)
            # Todo : Mettre dans la vue, ajouter limite de temps
            await ctx.send(content=f'Voici l\'info pour le {zone}',
                           file=discord.File(image, filename=f'{self.TITRE_COURT}-{zone}.png'))

        else:
            raise ValueError(('La zone doit correspondre au numéro du département souhaité.'
                              f'Exemple : `!{self.NOM_COMMANDE} 75`'))

    @timer(Path(__file__).stem)
    async def check_update(self) -> None:
        """Méthode appelée par le programme en boucle.
        Elle vérifie que les dernières données sont disponibles.

        Note:
            La date des dernières données correspond au jour précédent.
        """

        try:
            # On vérifie la date de màj à partir d'un des CSV.
            url = self.dict_csv['fra'][0]
            df = pd.read_csv(url, sep=';', parse_dates=['jour'])

            # On détermine si le jour des données du CSV (=la veille) correspond au jour recherché (=la veille).
            date_attendue = (dt_local_time - datetime.timedelta(days=1)).date()
            date_obtenue = datetime.datetime.strptime(str(df['jour'].max()),
                                                      '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')  # Jour issu du CSV

            # Si ces deux jours ne correspondent pas, attendre 30 min puis relancer la requête.
            assert str(date_attendue) == str(date_obtenue), \
                (f'{self.TITRE_COURT} : La date demandée est indisponible. {date_attendue = }; {date_obtenue = }')

            # Si ces deux jours correspondent, la requête peut être lancée, et puis interrompue jusqu'à demain.
            setattr(self, 'jour', date_attendue)
            setattr(self, 'vaccination_fra', df)
            await self.launch_main_embed()
            await asyncio.sleep(3600 * 6)  # 6 heures

        except AssertionError as err:
            raise AssertionError(err)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        '''Envoi du nombre de vaccinés dans le salon # transport et infos.'''

        running = True
        while running:
            global dt_local_time
            dt_local_time = await local_dt()
            try:
                if 18 <= dt_local_time.hour <= 23 and dt_local_time.minute in self.MINUTES_VERIF:
                    await self.check_update()
            except Exception as err:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                print(self.TITRE_COURT, err, exc_type, fname, exc_tb.tb_lineno)
            await asyncio.sleep(55)


@dataclass()
class VaccinCtrl(commands.Cog, AgeCtrl):

    TITRE_COURT = 'Vaccin_Age'
    TITRE_LONG = 'Vaccination par âge en France · IDF · 92'
    MESSAGE_ID = MESSAGES_IDS_COVID[6]
    MINUTES_VERIF = {20, 50}
    ROTATION_TPS_GIF = 10  # en secondes
    COULEUR_HEX = 0x70E6E4
    MODELE = covid_age.VaccinModele
    NOM_COMMANDE = 'vaccin_age'
    DICT_CSV = {'fra': ('https://www.data.gouv.fr/fr/datasets/r/54dd5f8d-1e2e-4ccb-8fb8-eac68245befd', 'FR', '#70E6E4', 'en', 'France'),
                'reg': ('https://www.data.gouv.fr/fr/datasets/r/c3ccc72a-a945-494b-b98d-09f48aa25337', 11, '#c7faff', 'en', 'Île-de-France'),
                'dep': ('https://www.data.gouv.fr/fr/datasets/r/83cbbdb9-23cb-455e-8231-69fc25d58111', 92, '#E3FFFF', 'dans les', 'Hauts-de-Seine')}
    dict_csv = DICT_CSV
    CLAGE = 'clage_vacsi'
    GIF_NOM = 'Vaccination'

    @commands.command(brief='Vaccination par âge contre la Covid-19')
    async def vaccin_age(self, ctx, zone=None) -> None:  # @commands.check_any(commands.has_role(ROLE_CS))
        """Lance le programme manuellement via une entrée utilisateur sur Discord."""
        await self.commande_utilisateur(ctx, zone)


@dataclass()
class PositiviteCtrl(commands.Cog, AgeCtrl):

    TITRE_COURT = 'Positivite_Age'
    TITRE_LONG = 'Personnes testées et personnes positives par âge en France · IDF · 92'
    MESSAGE_ID = MESSAGES_IDS_COVID[7]
    MINUTES_VERIF = {22, 52}
    ROTATION_TPS_GIF = 10  # en secondes
    COULEUR_HEX = 0xdf03fc
    MODELE = covid_age.PositiviteModele
    NOM_COMMANDE = 'positivite_age'
    DICT_CSV = {'fra': ('https://www.data.gouv.fr/fr/datasets/r/57d44bd6-c9fd-424f-9a72-7834454f9e3c', 'FR', '#fd87ff', 'en', 'France'),
                'reg': ('https://www.data.gouv.fr/fr/datasets/r/ad09241e-52fa-4be8-8298-e5760b43cae2', 11, '#feb8ff', 'en', 'Île-de-France'),
                'dep': ('https://www.data.gouv.fr/fr/datasets/r/19a91d64-3cd3-42fc-9943-d635491a4d76', 92, '#fed6ff', 'dans les', 'Hauts-de-Seine')}
    dict_csv = DICT_CSV
    CLAGE = 'cl_age90'
    GIF_NOM = 'Positivite'

    @commands.command(brief='Tests positifs par âge contre la Covid-19')
    async def positivite_age(self, ctx, zone=None) -> None:  # @commands.check_any(commands.has_role(ROLE_CS))
        """Lance le programme manuellement via une entrée utilisateur sur Discord."""
        await self.commande_utilisateur(ctx, zone)


def setup(bot):
    bot.add_cog(VaccinCtrl(bot))
    bot.add_cog(PositiviteCtrl(bot))


if __name__ == '__main__':
    print(Path(__file__).stem)


    @dataclass()
    class TestCtrl(AgeCtrl):
        TITRE_COURT = 'Positivite_Age'
        TITRE_LONG = 'Personnes testées et personnes positives par âge en France · IDF · 92'
        MESSAGE_ID = MESSAGES_IDS_COVID[7]
        MINUTES_VERIF = {22, 52}
        ROTATION_TPS_GIF = 10  # en secondes
        COULEUR_HEX = 0xdf03fc
        MODELE = covid_age.PositiviteModele
        NOM_COMMANDE = 'positivite_age'
        DICT_CSV = {'fra': ('https://www.data.gouv.fr/fr/datasets/r/dd0de5d9-b5a5-4503-930a-7b08dc0adc7c', 'FR', '#fd87ff', 'en', 'France'),              # sp-pos-quot
                    'reg': ('https://www.data.gouv.fr/fr/datasets/r/001aca18-df6a-45c8-89e6-f82d689e6c01', 11, '#feb8ff', 'en', 'Île-de-France'),         # sp-pos-quot
                    'dep': ('https://www.data.gouv.fr/fr/datasets/r/406c6a23-e283-4300-9484-54e78c8ae675', 92, '#fed6ff', 'dans les', 'Hauts-de-Seine')}  # sp-pos-quot
        dict_csv = DICT_CSV
        CLAGE = 'cl_age90'
        GIF_NOM = 'Positivite'

        async def test(self):
            tuple_dpt = (self.DICT_CSV['dep'][0], '92', '#ebfffe', 'dans', str('92'))
            image = await self.main('dep', tuple_dpt)
            # Todo : Mettre dans la vue, ajouter limite de temps
            print(image)
            return image

    test = TestCtrl()
    import asyncio
    asyncio.run(test.test())

