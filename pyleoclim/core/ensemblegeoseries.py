"""
The EnsembleSeries class is a child of EnsembleSeries, designed for ensemble applications (e.g. draws from a posterior distribution of ages, model ensembles with randomized initial conditions, or some other stochastic ensemble).
In addition to an EnsembleSeries object, an EnsembleGeoSeries object has the following properties:
- The addition of location data (latitude, longitude, and optionally elevation).   
- Optional depth data.
- Optional proxy sensor type, observation type, and archive type metadata

"""

from ..core.ensembleseries import EnsembleSeries
from ..core.geoseries import GeoSeries
from ..utils import mapping, lipdutils, plotting

import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

class EnsembleGeoSeries(EnsembleSeries):
    ''' EnsembleSeries object

    The EnsembleSeries object is a child of the MultipleSeries object, that is, a special case of MultipleSeries, aiming for ensembles of similar series.
    Ensembles usually arise from age modeling or Bayesian calibrations. All members of an EnsembleSeries object are assumed to share identical labels and units.

    All methods available for MultipleSeries are available for EnsembleSeries. Some functions were modified for the special case of ensembles.
    The class enables ensemble-oriented methods for computation (e.g., quantiles) 
    and visualization (e.g., envelope plot) that are unavailable to other classes.

    Parameters
    ----------

    series_list : list
        List of GeoSeries objects

    lat : float
        latitude N in decimal degrees. Must be in the range [-90;+90]
        
    lon : float
        longitude East in decimal degrees. Must be in the range [-180;+360]
        No conversion is applied as mapping utilities convert to [-180,+180] internally
       
    elevation : float
        elevation of the sample, in meters above sea level. Negative numbers indicate depth below global mean sea level, therefore.                                                                                          

    label : string
        Name of the time series (e.g., 'Nino 3.4')
        Default is None

    log : dict
        Dictionary of tuples documentating the various transformations applied to the object
        
    keep_log : bool
        Whether to keep a log of applied transformations. False by default
        
    importedFrom : string
        source of the dataset. If it came from a LiPD file, this could be the datasetID property 

    archiveType : string
        climate archive, one of 'Borehole', 'Coral', 'FluvialSediment', 'GlacierIce', 'GroundIce', 'LakeSediment', 'MarineSediment', 'Midden', 'MolluskShell', 'Peat', 'Sclerosponge', 'Shoreline', 'Speleothem', 'TerrestrialSediment', 'Wood'                                                                                   
        Reference: https://lipdverse.org/vocabulary/archivetype/
    
    control_archiveType  : [True, False]
        Whether to standardize the name of the archiveType agains the vocabulary from: https://lipdverse.org/vocabulary/paleodata_proxy/. 
        If set to True, will only allow for these terms and automatically convert known synonyms to the standardized name. Only standardized variable names will be automatically assigned a color scheme.  
        Default is False. 
        
    sensorType : string
        sensor, e.g. a paleoclimate proxy sensor. This property can be used to differentiate between species of foraminifera
        
    observationType : string
        observation type,  e.g. a proxy observation. See https://lipdverse.org/vocabulary/paleodata_proxy/. Note: this is preferred terminology but not enforced
        
    depth : array
        depth at which the values were collected
        
    depth_name : string
        name of the field, e.g. 'mid-depth', 'top-depth', etc   
        
    depth_unit : string
         units of the depth axis, e.g. 'cm'

    '''
    def __init__(self, series_list,lat=None,lon=None,elevation=None,archiveType=None,control_archiveType = False, 
                 sensorType = None, observationType = None, depth = None, depth_name = None, depth_unit= None):

        super().__init__(series_list)

        if lat is None:
            # check that all components are GeoSeries
            if not all([isinstance(ts, GeoSeries) for ts in series_list]):
                raise ValueError('If lat is not passed, all components must be GeoSeries objects')
            else:
                self.lat = series_list[0].lat
        elif lon is None:
            if not all([isinstance(ts, GeoSeries) for ts in series_list]):
                raise ValueError('If lon is not passed, all components must be GeoSeries objects')
            else:
                self.lon = series_list[0].lon

        else:
            lat = float(lat) 
            if -90 <= lat <= 90: 
                self.lat = lat
            else:
                ValueError('Latitude must be a number in [-90; 90]')
            
            lon = float(lon)
            if -180 < lon <= 360:     
                self.lon = lon
            else:
                ValueError('Longitude must be a number in [-180,360]')

        self.elevation = elevation
        self.archiveType = archiveType
        self.control_archiveType = control_archiveType
        self.sensorType = sensorType
        self.observationType = observationType
        self.depth = depth
        self.depth_name = depth_name
        self.depth_unit = depth_unit

    def make_labels(self):
        '''Initialization of labels

        Returns
        -------

        time_header : str

            Label for the time axis

        value_header : str

            Label for the value axis

        '''
        ts_list = self.series_list

        if ts_list[0].time_name is not None:
            time_name_str = ts_list[0].time_name
        else:
            time_name_str = 'time'

        if ts_list[0].value_name is not None:
            value_name_str = ts_list[0].value_name
        else:
            value_name_str = 'value'

        if ts_list[0].value_unit is not None:
            value_header = f'{value_name_str} [{ts_list[0].value_unit}]'
        else:
            value_header = f'{value_name_str}'

        if ts_list[0].time_unit is not None:
            time_header = f'{time_name_str} [{ts_list[0].time_unit}]'
        else:
            time_header = f'{time_name_str}'

        return time_header, value_header
    
    def dashboard(self, figsize=[11, 8], gs=None, plt_kwargs=None, histplt_kwargs=None, spectral_kwargs=None,
                  spectralfig_kwargs=None, map_kwargs=None,
                  hue='archiveType', marker='archiveType', size=None, scatter_kwargs=None,
                  gridspec_kwargs=None,
                  savefig_settings=None):
        '''

        Parameters
        ----------
        
        figsize : list or tuple, optional
            Figure size. The default is [11,8].

        gs : matplotlib.gridspec object, optional
            Requires at least two rows and 4 columns.
            - top row, left: timeseries
            - top row, right: histogram
            - bottom left: map
            - bottom right: PSD
            See [matplotlib.gridspec.GridSpec](https://matplotlib.org/stable/tutorials/intermediate/gridspec.html) for details.


        plt_kwargs : dict, optional
            Optional arguments for the timeseries plot. See Series.plot() or EnsembleSeries.plot_envelope(). The default is None.

        histplt_kwargs : dict, optional
            Optional arguments for the distribution plot. See Series.histplot() or EnsembleSeries.plot_distplot(). The default is None.

        spectral_kwargs : dict, optional
            Optional arguments for the spectral method. Default is to use Lomb-Scargle method. See Series.spectral() or EnsembleSeries.spectral(). The default is None.

        spectralfig_kwargs : dict, optional
            Optional arguments for the power spectrum figure. See PSD.plot() or MultiplePSD.plot_envelope(). The default is None.

        map_kwargs : dict, optional
            Optional arguments for map configuration
            - projection: str; Optional value for map projection. Default 'auto'.
            - proj_default: bool
            - lakes, land, ocean, rivers, borders, coastline, background: bool or dict;
            - lgd_kwargs: dict; Optional values for how the map legend is configured
            - gridspec_kwargs: dict; Optional values for adjusting the arrangement of the colorbar, map and legend in the map subplot
            - legend: bool; Whether to draw a legend on the figure. Default is True
            - colorbar: bool; Whether to draw a colorbar on the figure if the data associated with hue are numeric. Default is True
            The default is None.

        hue : str, optional
            Variable associated with color coding for points plotted on map. May correspond to a continuous or categorical variable.
            The default is 'archiveType'.

        size : str, optional
            Variable associated with size. Must correspond to a continuous numeric variable.
            The default is None.

        marker : string, optional
            Grouping variable that will produce points with different markers. Can have a numeric dtype but will always be treated as categorical.
            The default is 'archiveType'.

        scatter_kwargs : dict, optional
            Optional arguments configuring how data are plotted on a map. See description of scatter_kwargs in pyleoclim.utils.mapping.scatter_map

        gridspec_kwargs : dict, optional
            Optional dictionary for configuring dashboard layout using gridspec
            For information about Gridspec configuration, refer to `Matplotlib documentation <https://matplotlib.org/3.5.0/api/_as_gen/matplotlib.gridspec.GridSpec.html#matplotlib.gridspec.GridSpec>_. The default is None.

        savefig_settings : dict, optional
            the dictionary of arguments for plt.savefig(); some notes below:
            - "path" must be specified; it can be any existed or non-existed path,
              with or without a suffix; if the suffix is not given in "path", it will follow "format"
            - "format" can be one of {"pdf", "eps", "png", "ps"}.
            The default is None.

        Returns
        -------
        
        fig : matplotlib.figure
            The figure

        ax : dict
            dictionary of matplotlib ax

        See also
        --------

        pyleoclim.core.series.Series.plot : plot a timeseries

        pyleoclim.core.ensembleseries.EnsembleSeries.plot_envelope: Envelope plots for an ensemble

        pyleoclim.core.series.Series.histplot : plot a distribution of the timeseries

        pyleoclim.core.ensembleseries.EnsembleSeries.histplot : plot a distribution of the timeseries across ensembles

        pyleoclim.core.series.Series.spectral : spectral analysis method.

        pyleoclim.core.multipleseries.MultipleSeries.spectral : spectral analysis method for multiple series.

        pyleoclim.core.psds.PSD.signif_test : significance test for timeseries analysis

        pyleoclim.core.psds.PSD.plot : plot power spectrum

        pyleoclim.core.psds.MulitplePSD.plot : plot envelope of power spectrum

        pyleoclim.core.geoseries.GeoSeries.map : map location of dataset

        pyleoclim.utils.mapping.scatter_map : Underlying mapping function for Pyleoclim

        Examples
        --------

        .. jupyter-execute::

            import pyleoclim as pyleo
            ts = pyleo.utils.datasets.load_dataset('EDC-dD')
            ts_interp = ts.convert_time_unit('kyr BP').interp(step=.5) # interpolate for a faster result
            fig, ax = ts_interp.dashboard()

        '''
        savefig_settings = {} if savefig_settings is None else savefig_settings.copy()
        # start plotting
        fig = plt.figure(figsize=figsize)

        if gs == None:
            gridspec_kwargs = {} if type(gridspec_kwargs) != dict else gridspec_kwargs
            gridspec_defaults = dict(wspace=0, width_ratios=[3, .25, 2, 1],
                                     height_ratios=[1, .1, 1], left=0, right=1.1)
            gridspec_defaults.update(gridspec_kwargs)
            gs = gridspec.GridSpec(len(gridspec_defaults['height_ratios']), len(gridspec_defaults['width_ratios']), **gridspec_defaults)

        ax = {}
        # Plot the timeseries
        plt_kwargs = {} if plt_kwargs is None else plt_kwargs.copy()
        ax['ts'] = fig.add_subplot(gs[0, :-1])
        plt_kwargs.update({'ax': ax['ts']})
        # use the defaults if color/markers not specified
        
        if self.archiveType is not None:
            archiveType = lipdutils.LipdToOntology(self.archiveType)
            if archiveType not in lipdutils.PLOT_DEFAULT.keys():
                archiveType = 'Other'                
        else: 
            archiveType = 'Other'
        
        # if 'marker' not in plt_kwargs.keys():
        #     plt_kwargs.update({'marker': lipdutils.PLOT_DEFAULT[archiveType][1]})
        if 'curve_clr' not in plt_kwargs.keys():
            plt_kwargs.update({'curve_clr': lipdutils.PLOT_DEFAULT[archiveType][0]})
        if 'shade_clr' not in plt_kwargs.keys():
            plt_kwargs.update({'shade_clr': lipdutils.PLOT_DEFAULT[archiveType][0]})
        ax['ts'] = self.common_time().plot_envelope(**plt_kwargs)
        
        ymin, ymax = ax['ts'].get_ylim()

        # plot the histplot
        histplt_kwargs = {} if histplt_kwargs is None else histplt_kwargs.copy()
        ax['dts'] = fig.add_subplot(gs[0, -1:])
        histplt_kwargs.update({'ax': ax['dts']})
        histplt_kwargs.update({'ylabel': 'Counts'})
        histplt_kwargs.update({'vertical': True})

        if 'color' not in histplt_kwargs.keys():            
            histplt_kwargs.update({'color': lipdutils.PLOT_DEFAULT[archiveType][0]})

        ax['dts'] = self.histplot(**histplt_kwargs)
        ax['dts'].set_ylim([ymin, ymax])
        ax['dts'].set_yticklabels([])
        ax['dts'].set_ylabel('')
        ax['dts'].set_yticks([])

        # plot map
        map_kwargs = {} if map_kwargs is None else map_kwargs.copy()

        projection = map_kwargs.pop('projection', 'Orthographic')
        proj_default = map_kwargs.pop('proj_default', True)
        lakes = map_kwargs.pop('lakes', False)
        land = map_kwargs.pop('land', False)
        ocean = map_kwargs.pop('ocean', False)
        rivers = map_kwargs.pop('rivers', False)
        borders = map_kwargs.pop('borders', True)
        coastline = map_kwargs.pop('coastline', True)
        background = map_kwargs.pop('background', True)

        map_gridspec_kwargs = map_kwargs.pop('gridspec_kwargs', {})
        lgd_kwargs = map_kwargs.pop('lgd_kwargs', {})

        if 'edgecolor' in map_kwargs.keys():
            scatter_kwargs.update({'edgecolor': map_kwargs['edgecolor']})

        cmap = map_kwargs.pop('cmap', None)
        legend = map_kwargs.pop('legend', False)
        colorbar = map_kwargs.pop('colorbar', False)

        if legend == False:
            map_gridspec_kwargs['width_ratios'] = [.5,16, 1]

        _, ax['map'] =mapping.scatter_map(self, hue=hue, size=size, marker=marker, projection=projection, proj_default=proj_default,
                    background=background, borders=borders, coastline=coastline, rivers=rivers, lakes=lakes, ocean=ocean, land=land,
                    figsize=None, scatter_kwargs=scatter_kwargs,gridspec_kwargs = map_gridspec_kwargs,
                    lgd_kwargs=lgd_kwargs, legend=legend, cmap=cmap, colorbar=colorbar,
                    fig=fig, gs_slot=gs[-1, 0:1])

        # spectral analysis
        spectral_kwargs = {} if spectral_kwargs is None else spectral_kwargs.copy()
        if 'method' in spectral_kwargs.keys():
            pass
        else:
            spectral_kwargs.update({'method': 'lomb_scargle'}) # unneeded as it is already the default 
        if 'freq' in spectral_kwargs.keys():
            pass
        else:
            spectral_kwargs.update({'freq': 'lomb_scargle'})

        ax['spec'] = fig.add_subplot(gs[-1, -2:])
        spectralfig_kwargs = {} if spectralfig_kwargs is None else spectralfig_kwargs.copy()
        spectralfig_kwargs.update({'ax': ax['spec']})

        
        ts_preprocess = self.detrend().standardize().common_time()
        psds = ts_preprocess.spectral(**spectral_kwargs)
        #Avoid excessive legend labels in spectral plot
        for psd in psds.psd_list:
            psd.label = None

        # plot
        if 'curve_clr' not in spectralfig_kwargs.keys():
            spectralfig_kwargs.update({'curve_clr': lipdutils.PLOT_DEFAULT[archiveType][0]})
        if 'shade)clr' not in spectralfig_kwargs.keys():
            spectralfig_kwargs.update({'shade_clr': lipdutils.PLOT_DEFAULT[archiveType][0]})
        ax['spec'] = psds.plot_envelope(**spectralfig_kwargs)

        if 'path' in savefig_settings:
            plotting.savefig(fig, settings=savefig_settings)

        return fig, ax