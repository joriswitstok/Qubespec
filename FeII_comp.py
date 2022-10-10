#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Oct 10 14:08:35 2022

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

PATH_TO_FeII = '/Users/jansen/My Drive/Astro/General_data/FeII_templates/'


Veron_d = pyfits.getdata(PATH_TO_FeII+ 'Veron-cetty_2004.fits')
Veron_hd = pyfits.getheader(PATH_TO_FeII+'Veron-cetty_2004.fits')
Veron_wv = np.arange(Veron_hd['CRVAL1'], Veron_hd['CRVAL1']+ Veron_hd['NAXIS1'])


Tsuzuki = np.loadtxt(PATH_TO_FeII+'FeII_Tsuzuki_opttemp.txt')
Tsuzuki_d = Tsuzuki[:,1]
Tsuzuki_wv = Tsuzuki[:,0]



BG92 = np.loadtxt(PATH_TO_FeII+'bg92.con')
BG92_d = BG92[:,1]
BG92_wv = BG92[:,0]

# =============================================================================
# Convolution 
# =============================================================================
from astropy.convolution import Gaussian1DKernel
from astropy.convolution import convolve
from scipy.interpolate import interp1d
import tqdm
FWHMs = np.arange(2000,8000,5)
def find_nearest(array, value):
    """ Find the location of an array closest to a value 
	
	"""
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return idx




Dict = {'FWHMs':FWHMs}
Dict['Veron_wavelength'] = Veron_wv
Dict['Tsuzuki_wavelength'] = Tsuzuki_wv
Dict['BG92_wavelength'] = BG92_wv

Veron = np.zeros((len(Veron_d), len(FWHMs)))
Tsuzuki = np.zeros((len(Tsuzuki_d), len(FWHMs)))
BG92 = np.zeros((len(BG92_d), len(FWHMs)))


for i in tqdm.tqdm(range(len(FWHMs))):
    gk = Gaussian1DKernel(stddev=FWHMs[i]/3e5*5008/2.35)
    
    convolved = convolve(Veron_d, gk)
    convolved_veron = convolved/max(convolved[(Veron_wv<5400) &(Veron_wv>4900)])
    Veron[:,i] = convolved_veron
    
    convolved = convolve(Tsuzuki_d, gk)
    convolved_tsuzuki = convolved/max(convolved[(Tsuzuki_wv<5400) &(Tsuzuki_wv>4900)])
    Tsuzuki[:,i] = convolved_tsuzuki
    
    convolved = convolve(BG92_d, gk)
    convolved_bg92 = convolved/max(convolved[(BG92_wv<5400) &(BG92_wv>4900)])
    BG92[:,i] = convolved_bg92
    
    
Dict['Veron_dat'] = Veron
Dict['Tsuzuki_dat'] = Tsuzuki
Dict['BG92_dat'] = BG92

with open(PATH_TO_FeII+'Preconvolved_FeII.txt', "wb") as fp:
    pickle.dump(Dict, fp)      

