import os, sys
from abc import ABC
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
from matplotlib import pyplot as plt
from matplotlib import ticker
import matplotlib.dates as mdates

from settings import locale, MESSAGES_IDS_COVID, PANDAS_SPF_SPECS
# PANDAS_SPF_SPECS = {'sep': ';', 'parse_dates': ['jour'], 'low_memory': False}


PATH_DIR = os.getcwd() if __name__ == '__main__' else Path('./data/temp/vaccination/âge')


@dataclass()
class AgeModele(ABC):
    df_main:      object
    color_str:    str
    particule:    str
    localisation: str
    color_hex:    int = field(init=False)

    def __post_init__(self):
        '''Convertir la couleur str() en int()'''

        self.color_hex = int(f'0x{self.color_str[1:]}', 16)

    async def creer_image(self) -> Path:
        '''Graphique de l'évolution de la vaccination par tranche d'âges pour chaque zone géographique.'''

        df = self.df_main
        df = df[df['jour'] >= str(df['jour'].unique()[-45])]

        dict_main = deepcopy(self.DICT_MAIN)

        df = df[['jour', self.CLAGE] + [*dict_main]]
        # df.info(memory_usage="deep")

        # Dans chaque DF, on remplace le nom actuel de la colonne par des libellés explicites.
        def age_num_2_str(df, colonne):
            """Convertit une liste d'âges en texte.

            Args:
                df(pandas.core.frame.DataFrame): Le DF utilisé qui contient la colonne avec les âges.

            Returns:
                columns_dict: Un dictionnaire des âges {int: str}.
            """
            liste_ages = sorted(list(df[colonne].unique()))
            columns_dict = dict()
            for num, val in enumerate(liste_ages, 0):
                if not num:                 columns_dict[val] = 'Tous âges'  # if 0
                elif num == 1:              columns_dict[val] = f'{int(liste_ages[num - 1])} à {val} ans'  # 0 à 4 ans
                elif val == liste_ages[-1]: columns_dict[val] = f'{val} ans et +'
                else:                       columns_dict[val] = f'{int(liste_ages[num - 1]) + 1} à {val} ans'
            return columns_dict

        columns_dict = age_num_2_str(df, self.CLAGE)

        # Depuis le même DF, on sépare en 3 DF la couverture 1 dose, la couverture complète et les rappels.
        df_pivot = lambda values: df.pivot(index='jour', columns=self.CLAGE, values=values)

        # On crée un DF par type de couverture et par classe d'âges.
        for key, val in dict_main.items():
            df_pivot_key = df_pivot(key)
            val['df_rev'] = df_pivot_key.rename(columns=columns_dict)

        # On crée les plots
        fig, axes = plt.subplots(figsize=self.FIGSIZE, nrows=self.NROWS, ncols=self.NCOLS)

        # plt.gcf().autofmt_xdate()  # Formattage si besoin
        # plt.xticks(rotation=0)  # Rotation de la date
        plt.tight_layout()
        fig.subplots_adjust(left=None, bottom=0.175, top=.85, right=0.9, wspace=.7, hspace=.7)

        # Des caractéristiques générales du tableau
        fig.suptitle(f'{self.TITRE_GRAPH}\n'
                     f'{self.particule} {self.localisation} depuis 45 jours jusqu\'au {pd.Timestamp(df["jour"].max()).strftime("%A %x")}',
                     fontsize=14)
        fig.set_facecolor(self.color_str)

        # Date du jour pour l'embed et le graphique
        self.__setattr__('jour', pd.Timestamp(df["jour"].max()).strftime("%A %x"))

        # Infos en pied de page
        pied_page_texte = self.PIED_PAGE_TEXTE + f'Dernière donnée : {self.jour}'
        fig.text(self.PIED_PAGE_X, self.PIED_PAGE_Y, pied_page_texte, ha='left')

        # Nécessaire pour boucler chaque plot
        axes = axes.reshape(-1)

        # Mettre le 1er plot dans un cadre formatté différemment pour le démarquer, car il regroupe tous les âges.
        [axes[0].spines[elem].set_linewidth(3) for elem in ['bottom', 'top', 'left', 'right']]

        # Formule pour formatter les pourcentages ou les séparateurs de milliers
        if self.FMT_POURCENTAGE is True:   locale_value = lambda x: f'{str(x).replace(".", ",")}%'
        else:                              from settings import locale_value

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
                for date_ in [0, -1]:
                    var_couv = df_rev[df_rev.columns[m]].iat[date_]
                    ax.annotate(locale_value(var_couv),
                                xy=(mdates.date2num(pd.Timestamp(df['jour'].iat[date_])), var_couv),
                                xytext=xytext, xycoords='data', textcoords='offset points', color=couleur)

            plotter(**kwargs)
            annoter(**kwargs)

        for m, ax in enumerate(axes):
            try:
                # S'il faut modifier la limite du 1er plot ou la limite des autres plots
                if (self.SET_YLIM_1ER_PLOT and not m) or (self.SET_YLIM_AUTRES_PLOTS and m):
                    if isinstance(self.SET_YLIM, int):
                        ax.set_ylim((0, self.SET_YLIM))
                    else:
                        ylim = df[self.SET_YLIM].max() // 3  # Limite à 1/3 du max total pour les autres plots
                        ax.set_ylim((0, ylim))

                ax.set_xlim(pd.Timestamp(df['jour'].min()), pd.Timestamp(df['jour'].max()))
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

                # Séparateur de millier
                ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, loc: locale.format_string('%d', x, 1)))

                def title_majorticklabel_plot_annot(dictionnaire):
                    """"""
                    ax.title.set_text(dictionnaire[list(dictionnaire)[0]]['df_rev'].columns[m])  # Correspond au libellé de chaque colonne
                    plt.setp(ax.xaxis.get_majorticklabels(), rotation=0, ha='left')
                    dict_plots = [dict_sub for dict_sub in dictionnaire.values()]
                    [plotter_annoter(**kwargs) for kwargs in dict_plots]
                title_majorticklabel_plot_annot(dict_main)

            except IndexError:
                fig.delaxes(ax)

            except Exception as err:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                raise Exception(self.TITRE_COURT, err, exc_type, fname, exc_tb.tb_lineno)

        # Insérer la légende
        axes[0].legend(loc='center', bbox_to_anchor=(.171, .945), bbox_transform=fig.transFigure, facecolor='white',
                       framealpha=1)

        # Nom du graphique et enregistrement
        if not os.path.exists(image_path_dir := PATH_DIR):
            try:                      os.mkdir(image_path_dir)
            except FileNotFoundError: image_path_dir = os.getcwd()
        fichier_graphique = f'{self.TITRE_COURT} - {self.localisation}.png'
        self.__setattr__('image_path', os.path.join(image_path_dir, fichier_graphique))
        # Créer le fichier et le dossier s'ils n'existent pas

        if not os.path.exists(self.image_path): open(self.image_path, 'x')

        plt.savefig(self.image_path, bbox_inches='tight')

        return self.image_path

    async def __call__(self) -> Path:
        try:
            return await self.creer_image()
        except Exception as err:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            raise Exception(self.TITRE_COURT, err, exc_type, fname, exc_tb.tb_lineno)


class VaccinModele(AgeModele):

    TITRE_COURT = 'Vaccin_Age'  # Nom de l'image PNG et utilisé dans certaines Exception
    TITRE_GRAPH = 'Couverture vaccinale par tranche d\'âges'
    MESSAGE_ID = MESSAGES_IDS_COVID[6]
    DESCRIPTION = 'actualisé vers 20h-23h\n(du lundi au vendredi)'

    FIGSIZE, NROWS, NCOLS = (14, 8), 3, 5
    SET_YLIM, SET_YLIM_1ER_PLOT, SET_YLIM_AUTRES_PLOTS = 100, True, True
    FMT_POURCENTAGE = True
    PIED_PAGE_X = 0
    PIED_PAGE_Y = -.0125
    PIED_PAGE_TEXTE = ('NB : La vaccination des enfants de <12 ans (avant autorisation généralisée) correspond '
                       'probablement à de très hauts risques de forme grave de Covid.\n\n'
                       'Source : Santé publique France\n')
    DICT_MAIN = {'couv_dose1': {'titre': 'couv_dose1',
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
    CLAGE = 'clage_vacsi'

    def __init__(self, df_main, color_str, particule, localisation):
        super().__init__(df_main, color_str, particule, localisation)


class PositiviteModele(AgeModele):

    TITRE_COURT = 'Positivite_Age'  # Nom de l'image PNG et utilisé dans certaines Exception
    TITRE_GRAPH = 'Tests positifs quotidiens par tranche d\'âges'
    MESSAGE_ID = MESSAGES_IDS_COVID[6]
    DESCRIPTION = 'actualisé vers 20h-23h'

    FIGSIZE, NROWS, NCOLS = (14, 8), 3, 4
    SET_YLIM, SET_YLIM_1ER_PLOT, SET_YLIM_AUTRES_PLOTS = 'T', False, True
    FMT_POURCENTAGE = False
    PIED_PAGE_X = 0
    PIED_PAGE_Y = 0
    PIED_PAGE_TEXTE = ('NB : L\'échelle des graphiques par tranche d\'âges correspond à 1/3 de celle tous âges confondus.\n\n'
                       'Source : Santé publique France\n')
    DICT_MAIN = {'T': {'titre':     'T',
                       'couleur':   'blue',
                       'linestyle': '-',
                       'label':     'Personnes testées',
                       'xytext':    (3, 3)},
                 'P': {'titre': 'P',
                       'couleur': 'red',
                       'linestyle': '-',
                       'label': 'Personnes positives',
                       'xytext': (3, -7)},
                 }
    CLAGE = 'cl_age90'

    def __init__(self, df_main, color_str, particule, localisation):
        super().__init__(df_main, color_str, particule, localisation)


if __name__ == '__main__':
    import asyncio

    # Vaccin
    URL_DF = 'https://www.data.gouv.fr/fr/datasets/r/54dd5f8d-1e2e-4ccb-8fb8-eac68245befd'
    df = pd.read_csv(URL_DF, infer_datetime_format=True, **PANDAS_SPF_SPECS)
    fr = VaccinModele(df, '#70E6E4', 'en', 'France')
    asyncio.run(fr())

    # Positifs aux tests
    URL_DF = 'https://www.data.gouv.fr/fr/datasets/r/406c6a23-e283-4300-9484-54e78c8ae675'
    df = pd.read_csv(URL_DF, infer_datetime_format=True, **PANDAS_SPF_SPECS)
    df = df[df['dep'] == '92']
    positivite = PositiviteModele(df, '#fed6ff', 'dans les', 'Hauts-de-Seine')
    asyncio.run(positivite())
