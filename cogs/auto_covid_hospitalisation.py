import asyncio, datetime, os, sys
from dataclasses import dataclass

from discord.ext import commands
import pandas as pd

from functions._local_datetime import local_dt
from model import covid_hospitalisation
from view import views_embed as ve
from settings import locale_value, ROLE_CS, SALON_INFO_COVID, MESSAGES_IDS_COVID, PANDAS_SPF_SPECS  # Modifier le format des milliers  # locale_value = lambda x: '{:,}'.format(x).replace(',', ' ').replace('.0', ' ')


TITRE = 'Hospitalisation'
URL_ANSM = 'https://ansm.sante.fr/dossiers-thematiques/covid-19-vaccins/covid-19-vaccins-autorises'
URL_DF = 'https://www.data.gouv.fr/fr/datasets/r/63352e38-d353-4b54-bfd1-f1b3ee1cabd7'
DESCRIPTION = 'actualisé vers 20h-23h'
MESSAGES_UTILISES = MESSAGES_IDS_COVID[1], MESSAGES_IDS_COVID[3], MESSAGES_IDS_COVID[5]


@dataclass()
class AutoHopital(commands.Cog):
    """Traite les DF, crée un graphique, puis l'embed."""
    bot: object
    df = None

    async def main(self) -> None:
        """Génère les DF et les objets, puis lance le traitement des DF et des graphiques."""
        try:
            df = self.df  # Téléchargé par la méthode <commande> ou <check_update>
            group_drop = df[df['sexe'] == 0]
            group_init = group_drop.groupby('dep')

            # Pour le 92
            group92 = group_init.get_group('92')
            hosp_92 = covid_hospitalisation.Hopital(group92, 'Hauts-de-Seine', MESSAGES_UTILISES[0], '#FBE3E1')

            # Pour les Hauts-de-Seine
            group75 = group_init.get_group('75')
            group91 = group_init.get_group('91')
            # group92 = group_init.get_group('92')
            group93 = group_init.get_group('93')
            group94 = group_init.get_group('94')
            group95 = group_init.get_group('95')
            group77 = group_init.get_group('77')
            group78 = group_init.get_group('78')
            group_idf = pd.concat([group75, group91, group92, group93, group94, group95, group77, group78]).groupby(
                ['jour'], as_index=False).sum(min_count=1)
            hosp_idf = covid_hospitalisation.Hopital(group_idf, 'IDF', MESSAGES_UTILISES[1], '#F9D5D2')

            # Pour la France
            group_fr = group_drop.groupby(['jour']).sum(min_count=1)
            group_fr.reset_index(level=0, inplace=True)
            hosp_fr = covid_hospitalisation.Hopital(group_fr, 'France', MESSAGES_UTILISES[2], '#F6C1BC')

            await hosp_fr(); await hosp_idf(); await hosp_92()
            for obj in (hosp_fr, hosp_idf, hosp_92):
                # Création du champ (field)
                name = '\u200b'
                result_dept = str()
                for libelle_court, dict_y in obj.dict_coord_y_.items():
                    # Si le libelle_court de l'attribut se trouve dans la constante.
                    phrase = f"{dict_y['libelle_long2']} : {locale_value(dict_y['derniere_valeur'])}\n"
                    if libelle_court in covid_hospitalisation.DICT_COORD_Y:
                        result_dept += phrase
                    else:
                        result_dept += f'\n{phrase}'

                # Initialisation de l'embed et modification du message
                await ve.embed_edit_gc(bot=self.bot,
                                       salon_id=SALON_INFO_COVID,
                                       message_id=obj.message_id,
                                       title=f'Hospitalisations · {obj.zone_nom}',
                                       description=DESCRIPTION,
                                       fields=[(name, result_dept, False)],
                                       url=URL_ANSM,
                                       footer=f"Données du {obj.jour}\nSanté publique France",
                                       image_path=obj.image_path,
                                       color_hex=obj.color_hex)
                del obj; await asyncio.sleep(30)
            await asyncio.sleep(60 * 60 * 6)
        except Exception as err:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            raise Exception(err, exc_type, fname, exc_tb.tb_lineno)

    @commands.command(brief='Hospitalisations liéées à la Covid-19', aliases=['hospitalisation', 'hospitalisations'])
    @commands.check_any(commands.has_role(ROLE_CS))
    async def hopital(self, ctx) -> None:
        '''Lance le programme manuellement via une entrée utilisateur sur Discord.

        Note:
            La commande utilisateur est le nom de la fonction ou ses alias.
        '''
        df = pd.read_csv(URL_DF, infer_datetime_format=True, **PANDAS_SPF_SPECS)
        df.sort_values(by='jour', inplace=True)
        self.df = df
        await self.main()

    async def check_update(self) -> None:
        """Méthode appelée par le programme en boucle.
        Elle vérifie que les dernières données sont disponibles.

        Note:
            La date des dernières données correspond au jour actuel.
        """
        df = pd.read_csv(URL_DF, infer_datetime_format=True, **PANDAS_SPF_SPECS)
        df.sort_values(by='jour', inplace=True)

        # On détermine si le jour des données du CSV (=la veille) correspond au jour recherché (=la veille).
        date_attendue = dt_local_time.date()
        date_obtenue =  datetime.datetime.strptime(str(df['jour'].iat[-1]), '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')  # Jour issu du CSV

        # Si ces deux jours ne correspondent pas, attendre 30 min puis relancer la requête.
        if str(date_attendue) != str(date_obtenue):
            raise ValueError(f'{TITRE} : La date demandée est indisponible.\n {date_attendue = }; {date_obtenue = }')

        # Si ces deux jours correspondent, la requête peut être lancée, et puis interrompue jusqu'à demain.
        else:
            self.df = df
            await self.main()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Lance automatiquement le programme en boucle.

        Raises:
            Exception générale.
        """
        running = True
        while running:
            try:
                global dt_local_time
                dt_local_time = await local_dt()
                if 18 <= dt_local_time.hour <= 23 and dt_local_time.minute in {10, 40}:
                    await self.check_update()
            except Exception as err:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                print(TITRE, err, exc_type, fname, exc_tb.tb_lineno)
            finally:
                await asyncio.sleep(55)


def setup(bot):
    bot.add_cog(AutoHopital(bot))


if __name__ == '__main__':
    pass
