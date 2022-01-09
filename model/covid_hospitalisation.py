import datetime, locale, os, sys
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
from matplotlib import pyplot as plt
from matplotlib import ticker
import matplotlib.dates as mdates

from functions._timer import timer
from settings import locale_value  # Modifier le format des milliers  # locale_value = lambda x: '{:,}'.format(x).replace(',', ' ').replace('.0', ' ')


# https://matplotlib.org/stable/gallery/lines_bars_and_markers/linestyles.html
# https://matplotlib.org/stable/gallery/color/named_colors.html

TITLE = 'Hospitalisation'
IMAGE_PATH_DIR = os.getcwd() if __name__ == '__main__' else Path('./data/temp/vaccination')
DATE_FIN = '2022-06-30'

DICT_COORD_Y = {
    'hosp': {'libelle_long':  'Hospitalisations',
             'libelle_long2': 'Hospitalisations',
             'couleur':       'blue',
             'linestyle':     '-',
             'linewidth':     1,
             'ax':            0},
    'HospConv': {'libelle_long': 'Hospitalisation conventionnelle',
                 'libelle_long2': 'Hospitalisation conventionnelle',
                 'couleur': 'olive',
                 'linestyle': (0, (3, 1, 1, 1, 1, 1)),  # densely dashdotdotted
                 'linewidth': 1,
                 'ax': 0},
    'SSR_USLD': {'libelle_long':  'SSR / USLD (covid long)',
                 'libelle_long2': 'Soins de Suite et de Réadaptation (SSR) ou Unités de Soins de Longue Durée (USLD)',
                 'couleur':       'purple',
                 'linestyle':     '--',
                 'linewidth':     1,
                 'ax':            0},
    'rea': {'libelle_long':  'Réanimations ou soins intensifs',
            'libelle_long2': 'Réanimations ou soins intensifs',
            'couleur':       'red',
            'linestyle':     (0, (1, 1)),  # dotted
            'linewidth':     2.5,
             'ax':           0},
    'autres': {'libelle_long': 'Hospitalisations dans un autre type de service',
               'libelle_long2': 'Hospitalisations dans un autre type de service',
               'couleur': 'dimgrey',
               'linestyle': (0, (3, 1, 1, 1)),  # densely dashdotted
               'linewidth': 1,
               'ax': 0},
    ######################### axe différent #########################
    'rad': {'libelle_long':   'Retours à domicile',
             'libelle_long2': 'Retours à domicile',
            'couleur':        'green',
            'linestyle':      '--',
            'linewidth':      1,
            'ax':             1},
    'dc': {'libelle_long':  'Décès à l\'hôpital',
           'libelle_long2': 'Décès à l\'hôpital',
           'couleur':       'black',
           'linestyle':     '-.',
           'linewidth':     1,
           'ax':            1},
}

@dataclass()
class Hopital:
    df:          object
    zone_nom:    str
    message_id:  int
    color_str:   str
    color_hex:   int = field(init=False)
    jour =       str()
    image_path = str()

    __slots__ = '__dict__',

    def __post_init__(self):
        '''Convertir la couleur str() en int()'''
        self.color_hex = int(f'0x{self.color_str[1:]}', 16)

    @timer(TITLE)
    async def creer_graphique(self) -> None:
        """Traite les DF puis crée le graphique.

        Raises:
            Exception générale.
        """

        try:
            dict_coord_y = deepcopy(DICT_COORD_Y)

            group = self.df
            group = group.sort_values(by='jour')  # On s'assure que les dates sont dans l'ordre chronologique
            fig, ax = plt.subplots(figsize=(15, 7), nrows=2, ncols=1, gridspec_kw={'height_ratios': [2, 1]})
            fig.set_facecolor(self.color_str)
            fig.suptitle(f'Hôpital · {self.zone_nom}', fontsize=20)
            fig.subplots_adjust(bottom=0.225, top=.92)

            # Ecart entre les plots
            plt.subplots_adjust(left=None, bottom=None, right=None, top=None, wspace=.3, hspace=None)

            # Date de la dernière donnée, à insérer sur le graphique et dans l'embed
            last_dt = group['jour'].max()
            last_dt = datetime.datetime.strptime(str(last_dt), '%Y-%m-%d %H:%M:%S').strftime('%A %x')
            # last_dt = datetime.datetime.timestamp(last_dt)
            # last_dt = (await local_dt_jd(await local_dt(last_dt))).capitalize()
            setattr(self, 'jour', last_dt)

            # Annoter la source en bas à gauche
            ax[1].annotate(f'Le nombre d\'établissements déclarants peut varier dans le temps et ils peuvent '
                           f'faire des corrections, d\'où parfois une baisse des décès.\n\n'
                           f'Source : Santé publique France\n'
                           f'Dernière donnée : {last_dt}',
                           (0, 0), (0, -50), xycoords='axes fraction', textcoords='offset points', va='top', ha="left")

            # Format de la date sur le graphique
            # plt.gcf().autofmt_xdate()
            # plt.xticks(rotation=30)

            # Sur l'axe des abscisses, on met la date la plus lointaine appropriée.
            last_y = max(pd.Timestamp(DATE_FIN), pd.Timestamp(group['jour'].max()))

            for libelle_court, value in dict_coord_y.items():
                # Tracer les courbes
                group.plot('jour', y=libelle_court, figure=fig, color=value['couleur'],
                           linestyle=value['linestyle'], ax=ax[value['ax']], label=value['libelle_long'])

            # Paramètres pour chaque plot.
            for _ in ax:
                @ticker.FuncFormatter
                def major_formatter(x, pos):
                    return '{:,}'.format(x).replace(',', ' ').replace('.0', ' ')

                _.xaxis.set_minor_locator(mdates.MonthLocator())
                _.xaxis.set_minor_formatter(mdates.DateFormatter('%b'))
                plt.setp(_.xaxis.get_minorticklabels(), rotation=0, ha='left')
                _.grid(b=True, which='minor', color='#c9c9c9', linestyle='--', linewidth=0.5)

                _.yaxis.set_major_formatter(major_formatter)
                _.xaxis.set_major_locator(mdates.MonthLocator((1, 7)))
                # _.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
                _.xaxis.set_major_formatter(mdates.DateFormatter('%b\n%Y'))
                plt.setp(_.xaxis.get_majorticklabels(), rotation=0, ha='left')
                _.grid(b=True, which='major', color='#4d4d4d', linestyle='--', linewidth=0.5)

                # Aligner le mois à gauche
                [tick.label1.set_horizontalalignment('left') for tick in _.xaxis.get_minor_ticks()]

                _.set_xlim(pd.Timestamp(group['jour'].min()), last_y)
                # _.grid('on', color='grey', axis='both', linestyle='--', linewidth=0.25)

                _.patch.set_facecolor('w')
                _.set_xlabel('')

                # Labels
                _.set(ylabel='Nombre de personnes')

            # Emplacement de la légende pour chaque graphique
            [ax[plot].legend(loc=loc) for plot, loc in [(0, 'center left'), (1, 'upper left')]]

            # Annoter la dernière valeur connue dans le 1er plot.
            # Ajouter le signe +/- pour les variations
            variation = lambda x: ("+" if x >= 0 else "") + locale.format_string("%d", x, grouping=True)
            for libelle_court, dict_coord_y_valeurs in dict_coord_y.items():
                dict_coord_y[libelle_court]['derniere_valeur'] = int(group[libelle_court].iat[-1])
                dict_coord_y[libelle_court]['derniere_variation'] = (int(group[libelle_court].iat[-1]) - int(group[libelle_court].iat[-2]))
                ax[dict_coord_y_valeurs['ax']].annotate(f"{locale_value(dict_coord_y_valeurs['derniere_valeur'])} "
                                                        f"({variation(dict_coord_y_valeurs['derniere_variation'])})",
                                                        xy=(mdates.date2num(pd.Timestamp(group['jour'].max())),
                                                            dict_coord_y_valeurs['derniere_valeur']),
                                                        xytext=(8, -2), xycoords='data', textcoords='offset points',
                                                        color=dict_coord_y_valeurs['couleur'])

            # # Ajouter les données pour le texte de l'embed
            # for libelle_court, libelle_long in (('autres', 'Hospitalisations dans un autre type de service'),):
            #     if libelle_court not in dict_coord_y: dict_coord_y[libelle_court] = dict()
            #     dict_coord_y[libelle_court].update({'derniere_valeur': int(group[libelle_court].iat[-1])})
            #     dict_coord_y[libelle_court]['libelle_long2'] = libelle_long

            # Nom du graphique et enregistrement
            nom_graphique = f'Hospitalisation-{self.zone_nom}'
            self.image_path = os.path.join(IMAGE_PATH_DIR, f'{nom_graphique}.png')

            # Créer le fichier et le dossier s'ils n'existent pas
            if not os.path.exists(IMAGE_PATH_DIR):  os.mkdir(IMAGE_PATH_DIR)
            if not os.path.exists(self.image_path): open(self.image_path, 'x')

            fig.savefig(self.image_path, bbox_inches='tight')
            setattr(self, 'dict_coord_y_', dict_coord_y)

        except Exception as err:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            raise Exception(err, exc_type, fname, exc_tb.tb_lineno)

    async def __call__(self) -> None:
        try:
            await self.creer_graphique()
        except Exception as err:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            raise Exception(err, exc_type, fname, exc_tb.tb_lineno)

if __name__ == '__main__':
    df = pd.read_csv(r'https://www.data.gouv.fr/fr/datasets/r/63352e38-d353-4b54-bfd1-f1b3ee1cabd7',
                         sep=';', parse_dates=['jour'], infer_datetime_format=True, low_memory=False)
    df.sort_values(by='jour', inplace=True)
    group_drop = df[df['sexe'] == 0]
    group_init = group_drop.groupby('dep')
    # Pour le 92
    group92 = group_init.get_group('92')
    hosp_92 = Hopital(group92, 'Hauts-de-Seine', 'MESSAGES_UTILISES[0]', '#FBE3E1')
    import asyncio
    asyncio.run(hosp_92())
    print(f'{hosp_92.dict_coord_y_ = }')
    print(hosp_92.jour)
