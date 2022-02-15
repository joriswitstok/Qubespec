#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb 11 09:17:06 2022

@author: jansen
"""

#importing modules
import numpy as np
import matplotlib.pyplot as plt; plt.ioff()

from astropy.io import fits as pyfits
from astropy import wcs
from astropy.table import Table, join, vstack
from matplotlib.backends.backend_pdf import PdfPages
import pickle
from scipy.optimize import curve_fit

import Graph_setup as gst 

nan= float('nan')

pi= np.pi
e= np.e

plt.close('all')
c= 3.*10**8
h= 6.62*10**-34
k= 1.38*10**-23

Ken98= (4.5*10**-44)
Conversion2Chabrier=1.7 # Also Madau
Calzetti12= 2.8*10**-44
arrow = u'$\u2193$' 


PATH='/Users/jansen/My Drive/Astro/'
fsz = gst.graph_format()


import IFU_tools_class as IFU 

plot_it=1
'''
IFU_cube_path = PATH +'KMOS_SIN/KMOS_data/H_band/COMBINE_SHIFT_cdfs_39849_x_r_01spax.fits' 
instrument = 'KMOS'
ID = 'XID_208'
z= 1.61


Cube = IFU.Cube(IFU_cube_path, z, ID, instrument, 'path', 'H')

Cube.mask_emission()
Cube.mask_sky( 1.5)
Cube.collapse_white(plot_it)
Cube.find_center( plot_it)

Cube.choose_pixels(plot_it, rad= 0.3)#, flg='K587')

Cube.stack_sky(plot_it, expand=0)
Cube.D1_spectra_collapse( plot_it, addsave='_inner')


Cube.fitting_collapse_Halpha( plot_it, broad=1)



'''

import importlib
importlib.reload(IFU )

IFU_cube_path = PATH +'KMOS_SIN/KMOS_data/H_band/COMBINE_SHIFT_SCI_RECONSTRUCTED_GS3_19791_H.fits' 
#IFU_cube_path = PATH +'KMOS_SIN/KMOS_data/YJ_band/COMBINE_SHIFT_AGN6.fits' 
instrument = 'KMOS'
ID = 'XID_208'
z= 2.2246
#z= 1.61
Band = 'H'

Cube = IFU.Cube(IFU_cube_path, z, ID, instrument, 'path', Band)

Cube.mask_emission()
Cube.mask_sky( 1.5)
Cube.collapse_white(plot_it)
Cube.find_center( plot_it)

Cube.choose_pixels(plot_it, rad= 0.5)#, flg='K587')

Cube.stack_sky(plot_it, expand=0)
Cube.D1_spectra_collapse( plot_it, addsave='_inner')


Cube.fitting_collapse_OIII( plot_it, outflow=1)

#Cube.Spaxel_fit_OIII()


plt.show()


'''


storage_H = IFU.choose_pixels(storage_H, plot_it, rad= rds , flg = fl)

storage_H = IFU.astrometry_correction(storage_H)
pdf_plots.savefig()


if Sample['Sky_mask_flag_Hal'][i]==1:

    msk = np.loadtxt(PATH+'KMOS_SIN/Masks/'+Hal_band+'_band/'+ID+'_pixel.mask')
    spcm = np.array(msk, dtype=int)

    print spcm

    storage_H = IFU.stack_sky(storage_H, Hal_band,plot_it, spcm, expand=0)

elif Sample['Sky_mask_flag_Hal'][i]==0:
    storage_H = IFU.stack_sky(storage_H, Hal_band, plot_it, expand=0)

else:
    print 'Flag for pixel mask not understood'

      

if Spat== True:
    storage_H = IFU.Spaxel_fit_sig(storage_H, 'H',1, binning,broad=New['Halpha_nBroad'][i], localised=0 )


emplot.Spax_fit_plot_sig(storage_H, 'H', z, ID, binning, addsave='_inner')


#IFU.Broad_PSF(storage_H, ID,z, binning)

if (ID=='XID_751') | (ID=='XID_614') | (ID=='XID_427') :
    IFU.Regions_cube(storage_H, 'H', broad=0)

else:
    IFU.Regions_cube(storage_H, 'H')       
'''