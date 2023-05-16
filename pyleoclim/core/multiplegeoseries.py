"""
A MultipleGeoSeries object is a collection (more precisely, a 
list) of GeoSeries objects. This is handy in case you want to apply the same method 
to such a collection at once (e.g. process a bunch of series in a consistent fashion).
Compared to its parent class MultipleSeries, MultipleGeoSeries opens new possibilites regarding mapping.
"""
from ..core.multipleseries import MultipleSeries
from ..utils import mapping as mp
import warnings

import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib import cm
from itertools import cycle
import matplotlib.lines as mlines
import numpy as np
import copy


class MultipleGeoSeries(MultipleSeries):
    '''MultipleGeoSeries object.

    This object handles a collection of the type GeoSeries and can be created from a list of such objects.
    MultipleGeoSeries should be used when the need to run analysis on multiple records arises, such as running principal component analysis.
    Some of the methods automatically transform the time axis prior to analysis to ensure consistency.

    Parameters
    ----------

    series_list : list
    
        a list of pyleoclim.Series objects

    time_unit : str
    
        The target time unit for every series in the list.
        If None, then no conversion will be applied;
        Otherwise, the time unit of every series in the list will be converted to the target.

    label : str
   
        label of the collection of timeseries (e.g. 'Euro 2k')

    Examples
    --------
    TODO: Euro2k example?
                
    '''

    def __init__(self, series_list, time_unit=None, label=None):
        from ..core.geoseries import GeoSeries

        self.series_list = series_list
        self.time_unit = time_unit
        self.label = label

        # check that all components are GeoSeries
        if not all([isinstance(ts, GeoSeries) for ts in self.series_list]):
            raise ValueError('All components must be GeoSeries objects')

        # check that they all have lat/lon (do we need this?)

        if self.time_unit is not None:
            new_ts_list = []
            for ts in self.series_list:
                new_ts = ts.convert_time_unit(time_unit=self.time_unit)
                new_ts_list.append(new_ts)

            self.series_list = new_ts_list

    # ============ MAP goes here ================
    def map(self, hue='archiveType', marker=None, size=None,
                color_pal=None, legend_attribute=None, projection='Robinson', proj_default=True,
                background=True, borders=False, rivers=False, lakes=False,
                figsize=None, ax=None, scatter_kwargs=None, legend=True,
                lgd_kwargs=None, savefig_settings=None, **kwargs):

        def make_scalar_mappable(cmap, lims=None, n=None):
            if type(cmap) == list:
                if n is None:
                    ax_cmap = mpl.colors.LinearSegmentedColormap.from_list("MyCmapName", ["r", "b"])
                else:
                    ax_cmap = mpl.colors.LinearSegmentedColormap.from_list("MyCmapName", ["r", "b"], N=n)
            elif type(cmap) == str:
                if n is None:
                    ax_cmap = plt.get_cmap(cmap)
                else:
                    ax_cmap = plt.get_cmap(cmap, n)
            else:
                print('what madness is this?')

            if type(lims) in [list, tuple]:
                ax_norm = mpl.colors.Normalize(vmin=min(lims), vmax=max(lims), clip=False)
            else:
                ax_norm = None
            ax_sm = cm.ScalarMappable(norm=ax_norm, cmap=ax_cmap)

            return ax_sm

        mappings = {'color_pal': color_pal}
        f = lambda m, c, s: mlines.Line2D([], [], marker=m, color=c, markersize=s, ls="none")
        for key in ['hue_mapping', 'marker_mapping']:
            if key in kwargs:
                mappings[key] = kwargs[key]

        missing_d = {'hue': kwargs['missing_val_hue'] if 'missing_val_hue' in kwargs else 'k',
                     'marker': kwargs['missing_val_marker'] if 'missing_val_marker' in kwargs else 'x',
                     'size': kwargs['missing_val_size'] if 'missing_val_size' in kwargs else 10,
                     }

        def make_cont_hue(trait_vals, mappings):
            color_pal = mappings['color_pal']
            if color_pal == None:
                color_pal = 'viridis'

            hue_mappable = make_scalar_mappable(color_pal, lims=[min([val for val in trait_vals if val != None]),
                                                                 max([val for val in trait_vals if val != None])])
            return dict(f=hue_mappable.to_rgba, mappable=hue_mappable)

        def make_cat_hue(trait_unique, mappings):
            if 'hue_mapping' in mappings:
                hue_mapping = mappings['hue_mapping']
            else:
                color_pal = mappings['color_pal']
                if color_pal is None:
                    color_pal = 'turbo'
                hue_mappable = make_scalar_mappable(color_pal, lims=None, n=len(trait_unique))
                hue_mapping = {trait_val: hue_mappable.cmap.colors[ik] for ik, trait_val in enumerate(trait_unique)}

            leg_d = {'handles': [], 'labels': []}
            for key in hue_mapping:
                leg_d['handles'].append(f("s", hue_mapping[key], 8))
                leg_d['labels'].append(key)

            return dict(f=lambda x: hue_mapping[x], mapping=hue_mapping, leg=leg_d)  # 'mappable': hue_mappable,

        def make_cont_size(trait_vals, mappings):
            lims = lims = [min([val for val in trait_vals if val != None]),
                           max([val for val in trait_vals if val != None])]
            szes = np.linspace(lims[0], lims[1], 4)
            size_f = lambda x: x * 10 / (lims[1] - lims[0])
            leg_d = {'handles': [], 'labels': []}
            for key in szes:
                leg_d['handles'].append(f('s', "k", size_f(key)))
                leg_d['labels'].append(int(key))
            return dict(f=size_f, lims=lims, leg=leg_d)

        def make_cat_marker(trait_unique, mappings):
            if 'marker_mapping' in mappings:
                marker_mapping = mappings['marker_mapping']
            else:
                m = cycle(mlines.Line2D.filled_markers)
                marker_mapping = {trait_val: next(m) for ik, trait_val in enumerate(trait_unique)}
            leg_d = {'handles': [], 'labels': []}
            for key in marker_mapping:
                leg_d['handles'].append(f(marker_mapping[key], "k", 8))
                leg_d['labels'].append(key)
            return dict(f=lambda x: marker_mapping[x], mapping=marker_mapping, leg=leg_d)

        continuous_d = {'hue': make_cont_hue,
                        'size': make_cont_size,
                        'marker': None
                        }

        categorical_d = {'hue': make_cat_hue,
                         'size': None,
                         'marker': make_cat_marker
                         }

        trait_d = {'hue': hue, 'marker': marker, 'size': size}
        legend_d = {'hue': None, 'marker': None, 'size': None}

        for trait_key in trait_d.keys():
            trait = trait_d[trait_key]
            if trait_d[trait_key] == None:
                trait_vals = [None for ik in range(len(self.series_list))]
                attrib_vals = [missing_d[trait_key] for ik in trait_vals]
                d = {'attrib_vals': attrib_vals}
            else:
                trait_vals = [geos.__dict__[trait] if trait in geos.__dict__.keys() else None for geos in
                              self.series_list]
                trait_vals = [val if val != 'None' else None for val in trait_vals]
                trait_unique = list(set([val for val in trait_vals if val != None]))
                trait_val_types = [True if type(val) == np.str_ else False for val in trait_unique]

                # categorical
                if True in trait_val_types:
                    if categorical_d[trait_key] != None:
                        d = categorical_d[trait_key](trait_unique, mappings)
                        d['attrib_vals'] = [d['mapping'][val] if val != None else missing_d[trait_key] for val in
                                            trait_vals]
                        legend = True
                        if legend_attribute is None:
                            legend_attribute = trait_key
                    else:
                        # attrib_vals = [missing_d[trait_key] for ik in trait_vals]
                        d = {'attrib_vals': None}

                # continuous
                else:
                    if continuous_d[trait_key] != None:
                        d = continuous_d[trait_key](trait_vals, mappings)
                        trait_vals = [int(val) if np.isnan(val) == False else None for val in trait_vals]
                        d['attrib_vals'] = [d['f'](val) if val != None else missing_d[trait_key] for val in trait_vals]
                        legend = False
                    else:
                        attrib_vals = [missing_d[trait_key] for ik in trait_vals]
                        d = {'attrib_vals': None}
                        legend = False

                trait_vals = [val if val != None else 'unknown' for val in trait_vals]
                legend_d[trait_key] = trait_vals
            trait_d[trait_key] = d

        if type(scatter_kwargs) == dict:
            scatter_kwargs['s'] = trait_d['size']['attrib_vals']
        elif scatter_kwargs is None:
            scatter_kwargs = {'s': trait_d['size']['attrib_vals']}

        if type(lgd_kwargs) == dict:
            lgd_kwargs['bbox_to_anchor'] = (1.3, 1)
        else:
            lgd_kwargs = {'bbox_to_anchor': (1.3, 1)}

        lats = [geos.lat for geos in self.series_list]
        lons = [geos.lon for geos in self.series_list]
        if legend_attribute is None:
            legend = False
        else:
            legend = True

        ax2 = mp.map(lats, lons, legend_d[legend_attribute], marker=trait_d['marker']['attrib_vals'],
                     color=trait_d['hue']['attrib_vals'],
                     projection=projection, proj_default=proj_default,
                     background=background, borders=borders, rivers=rivers, lakes=lakes,
                     figsize=figsize, ax=ax, scatter_kwargs=scatter_kwargs, legend=legend,
                     lgd_kwargs=lgd_kwargs, savefig_settings=savefig_settings)

        if legend ==True:
            handles = []
            labels = []
            for key in trait_d:
                if 'leg' in trait_d[key]:
                    handles +=trait_d[key]['leg']['handles']
                    labels += trait_d[key]['leg']['labels']
                    handles.append(copy.copy(handles[0]))
                    handles[-1].set_alpha(0)
                    labels.append('')
            ax2[1].legend(handles, labels,  bbox_to_anchor=(1,1), loc="upper left")

