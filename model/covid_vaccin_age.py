import os, sys
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
from matplotlib import pyplot as plt
import matplotlib.dates as mdates

from settings import MESSAGES_IDS_COVID


TITRE_COURT = 'Vaccin_Age'
TITRE_LONG = 'Vaccination par âge en France · IDF · 92'
MESSAGE_ID = MESSAGES_IDS_COVID[6]
DESCRIPTION = 'actualisé vers 20h-23h\n(du lundi au vendredi)'
URL = f'https://solidarites-sante.gouv.fr/grands-dossiers/vaccin-covid-19/'
PATH_DIR = os.getcwd() if __name__ == '__main__' else Path('./data/temp/vaccination/âge')


@dataclass()
class VaccinModele:
    vaccination: object
    color_str: str
    particule: str
    localisation: str
    color_hex: int = field(init=False)

    def __post_init__(self):
        '''Convertir la couleur str() en int()'''

        self.color_hex = int(f'0x{self.color_str[1:]}', 16)

    async def vaccination_image(self) -> Path:
        '''Graphique de l'évolution de la vaccination par tranche d'âges pour chaque zone géographique.'''

        df = self.vaccination

        dict_vaccin = {'couv_dose1': {'titre': 'couv_dose1',
                                      'couleur': 'blue',
                                      'linestyle': '-',
                                      'label': '1ère dose',
                                      'xytext': (3, 3)},
                       'couv_complet': {'titre': 'couv_complet',
                                        'couleur': 'green',
                                        'linestyle': '--',
                                        'label': 'Schéma complet',
                                        'xytext': (3, -7)},
                       'couv_rappel': {'titre': 'couv_rappel',
                                       'couleur': 'darkgreen',
                                       'linestyle': '--',
                                       'label': 'Dose de rappel',
                                       'xytext': (3, -7)}
                       }

        df = df[['jour', 'clage_vacsi'] + [*dict_vaccin]]
        # df.info(memory_usage="deep")

        # Dans chaque DF, on remplace le nom actuel de la colonne par des libellés explicites.
        liste_ages = sorted(list(df['clage_vacsi'].unique()))
        columns_dict = dict()
        for num, val in enumerate(liste_ages, 0):
            if not num:                 columns_dict[val] = 'Tous âges'  # if 0
            elif num == 1:              columns_dict[val] = f'{int(liste_ages[num - 1])} à {val} ans'  # 0 à 4 ans
            elif val == liste_ages[-1]: columns_dict[val] = f'{val} ans et +'
            else:                       columns_dict[val] = f'{int(liste_ages[num - 1]) + 1} à {val} ans'

        # Depuis le même DF, on sépare en 3 DF la couverture 1 dose, la couverture complète et les rappels.
        df_pivot = lambda values: df.pivot(index='jour', columns='clage_vacsi', values=values)

        # On crée un DF par type de couverture et par classe d'âges.
        for key, val in dict_vaccin.items():
            df_pivot_key = df_pivot(key)
            val['df_rev'] = df_pivot_key.rename(columns=columns_dict)

        # On crée les plots
        fig, axes = plt.subplots(figsize=(14, 8), nrows=3, ncols=5)

        # plt.gcf().autofmt_xdate()  # Formattage si besoin
        # plt.xticks(rotation=0)  # Rotation de la date
        plt.tight_layout()
        fig.subplots_adjust(bottom=0.175, right=0.9)

        # Des caractéristiques générales du tableau
        fig.suptitle(f'Couverture vaccinale par tranche d\'âges\n'
                     f'{self.particule} {self.localisation} depuis 45 jours jusqu\'au {pd.Timestamp(df["jour"].iat[-1]).strftime("%A %x")}',
                     fontsize=14)
        fig.subplots_adjust(left=None, bottom=None, right=None, top=None, wspace=.7, hspace=.7)
        fig.set_facecolor(self.color_str)
        fig.subplots_adjust(top=.85)

        # Date du jour pour l'embed et le graphique
        self.__setattr__('jour', pd.Timestamp(df["jour"].max()).strftime("%A %x"))

        # Infos en pied de page
        plt.annotate(('NB : La vaccination des enfants de <12 ans (avant autorisation généralisée) correspond '
                      'probablement à de très hauts risques de forme grave de Covid.\n\n'
                      'Source : Santé publique France\n'
                      f'Dernière donnée : {self.jour}'),
                     (-7, 0), (0, -50), xycoords='axes fraction', textcoords='offset points', va='top', ha="left")

        # Nécessaire pour boucler chaque plot
        axes = axes.reshape(-1)

        # Mettre le 1er plot dans un cadre formatté différemment pour le démarquer, car il regroupe tous les âges.
        [axes[0].spines[elem].set_linewidth(3) for elem in ['bottom', 'top', 'left', 'right']]

        # Formule pour formatter les pourcentages
        locale_value = lambda x: f'{str(x).replace(".", ",")}%'

        def plotter_annoter(**kwargs) -> None:
            '''Trace et annote chaque plot.

            Note:
                Fonction utilisée dans la boucle juste après.
            '''

            def plotter(df_rev, couleur, linestyle, label, **kwargs) -> None:
                '''Tracer les courbes.'''
                ax.plot(df_rev[df_rev.columns[m]], color=couleur, linestyle=linestyle, label=label)

            def annoter(df_rev, xytext, couleur, **kwargs) -> None:
                '''Annoter les premières et dernières valeurs.'''
                for date_ in [-45, -1]:
                    var_couv = df_rev[df_rev.columns[m]].iat[date_]
                    ax.annotate(locale_value(var_couv),
                                xy=(mdates.date2num(pd.Timestamp(df['jour'].iat[date_])), var_couv),
                                xytext=xytext, xycoords='data', textcoords='offset points', color=couleur)

            plotter(**kwargs)
            annoter(**kwargs)

        for m, ax in enumerate(axes):
            try:
                ax.set_ylim(0, 100)
                ax.set_xlim(pd.Timestamp(df['jour'].iat[-45]), pd.Timestamp(df['jour'].max()))

                ax.grid('on', axis='both', linestyle='-', linewidth=0.35)
                ax.patch.set_facecolor('w')
                ax.set_xlabel('')

                # Intervalle et formattage de la date
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=7))
                ax.tick_params(axis='x', which='major', labelsize=9)
                # Chaque mois commence le 1er jour du mois
                locator = mdates.AutoDateLocator()
                formatter = mdates.ConciseDateFormatter(locator)
                formatter.formats = ['%y',  # ticks are mostly years
                                     '%d\n%b',  # ticks are mostly months
                                     '%d',  # ticks are mostly days
                                     '%H:%M',  # hrs
                                     '%H:%M',  # min
                                     '%S.%f', ]  # secs
                # these are mostly just the level above...
                formatter.zero_formats = [''] + formatter.formats[:-1]
                # ...except for ticks that are mostly hours, then it is nice to have
                # month-day:
                # formatter.zero_formats[3] = '%d-%b'

                formatter.offset_formats = ['', '', '', '', '', '', '']
                ax.xaxis.set_major_locator(locator)
                ax.xaxis.set_major_formatter(formatter)

                ax.title.set_text(
                    dict_vaccin['couv_dose1']['df_rev'].columns[m])  # Correspond au libellé de chaque colonne
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=0, ha='left')

                dict_plots = [dict_sub for dict_sub in dict_vaccin.values()]
                [plotter_annoter(**kwargs) for kwargs in dict_plots]

            except Exception as err:
                fig.delaxes(ax)

        # Insérer la légende
        axes[0].legend(loc='center', bbox_to_anchor=(.171, .945), bbox_transform=fig.transFigure, facecolor='white',
                       framealpha=1)

        # Ajouter les attributs de taux de couverture
        [self.__setattr__(f'taux_{key}', locale_value(val['df_rev'][val['df_rev'].columns[0]].iat[-1])) for key, val
         in [*dict_vaccin.items()]]

        # Nom du graphique et enregistrement
        image_path_dir = PATH_DIR
        fichier_graphique = f'Vaccination-Age - {self.localisation}.png'
        self.__setattr__('image_path', os.path.join(image_path_dir, fichier_graphique))
        # Créer le fichier et le dossier s'ils n'existent pas
        if not os.path.exists(image_path_dir):  os.mkdir(image_path_dir)
        if not os.path.exists(self.image_path): open(self.image_path, 'x')
        plt.savefig(self.image_path)

        return self.image_path

    async def __call__(self) -> Path:
        try:
            return await self.vaccination_image()
        except Exception as err:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            raise Exception(TITRE_COURT, err, exc_type, fname, exc_tb.tb_lineno)

if __name__ == '__main__':
    URL_DF = 'https://www.data.gouv.fr/fr/datasets/r/54dd5f8d-1e2e-4ccb-8fb8-eac68245befd'
    df = pd.read_csv(URL_DF, sep=';', parse_dates=['jour'], infer_datetime_format=True, low_memory=False)
    fr = VaccinModele(df, '#70E6E4', 'en', 'France')
    import asyncio
    asyncio.run(fr())
