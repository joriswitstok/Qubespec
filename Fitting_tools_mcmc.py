#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Wed Aug 16 17:35:45 2017

@author: jscholtz
"""

#importing modules
import numpy as np
import matplotlib.pyplot as plt

from astropy.io import fits as pyfits
from astropy import wcs
from astropy.table import Table, join, vstack
from matplotlib.backends.backend_pdf import PdfPages
import pickle
from scipy.optimize import curve_fit
import os
import emcee
import corner
from astropy.modeling.powerlaws import PowerLaw1D
nan= float('nan')

pi= np.pi
e= np.e

c= 3.*10**8
h= 6.62*10**-34
k= 1.38*10**-23

arrow = u'$\u2193$' 

N = 6000
PATH_TO_FeII = '/Users/jansen/My Drive/Astro/General_data/FeII_templates/'

version = 'Main'    


def gauss(x, k, mu,sig):

    expo= -((x-mu)**2)/(2*sig*sig)
    
    y= k* e**expo
    
    return y

from Halpha_models import *
from OIII_models import *
from Halpha_OIII_models import *
from QSO_models import *
import numba
import Support as sp


class Fitting:
    def __init__(self, wave, flux, error, z, N=5000, progress=True, priors= {'z':[0, 'normal', 0,0.003],\
                                                                                       'cont':[0,'loguniform',-3,1],\
                                                                                       'cont_grad':[0,'normal',0,0.3], \
                                                                                       'Hal_peak':[0,'loguniform',-3,1],\
                                                                                       'BLR_Hal_peak':[0,'loguniform',-3,1],\
                                                                                       'NII_peak':[0,'loguniform',-3,1],\
                                                                                       'Nar_fwhm':[300,'uniform',100,900],\
                                                                                       'BLR_fwhm':[4000,'uniform', 2000,9000],\
                                                                                       'zBLR':[0, 'normal', 0,0.003],\
                                                                                        'SIIr_peak':[0,'loguniform',-3,1],\
                                                                                        'SIIb_peak':[0,'loguniform',-3,1],\
                                                                                        'Hal_out_peak':[0,'loguniform',-3,1],\
                                                                                        'NII_out_peak':[0,'loguniform',-3,1],\
                                                                                        'outflow_fwhm':[600,'uniform', 300,1500],\
                                                                                        'outflow_vel':[-50,'normal', 0,300],\
                                                                                        'OIII_peak':[0,'loguniform',-3,1],\
                                                                                        'OIII_out_peak':[0,'loguniform',-3,1],\
                                                                                        'Hbeta_peak':[0,'loguniform',-3,1],\
                                                                                        'Hbeta_fwhm':[200,'uniform',120,7000],\
                                                                                        'Hbeta_vel':[10,'normal', 0,200],\
                                                                                        'Hbetan_peak':[0,'loguniform',-3,1],\
                                                                                        'Hbetan_fwhm':[300,'uniform',120,700],\
                                                                                        'Hbetan_vel':[10,'normal', 0,100],\
                                                                                        'Fe_peak':[0,'loguniform',-3,1],\
                                                                                        'Fe_fwhm':[3000,'uniform',2000,6000],\
                                                                                        'SIIr_peak':[0,'loguniform', -3,1],\
                                                                                        'SIIb_peak':[0,'loguniform', -3,1],\
                                                                                        'OI_peak':[0,'loguniform', -3,1],\
                                                                                        'OI_out_peak':[0,'loguniform', -3,1],\
                                                                                        'BLR_Hbeta_peak':[0,'loguniform', -3,1]}):
        
        self.N = N
        self.priors = priors
        self.progress = progress
        self.z = z 
        self.wave = wave
        self.fluxs = flux
        self.error = error
        
    # =============================================================================
    #  Primary function to fit Halpha both with or without BLR - data prep and fit 
    # =============================================================================
    def fitting_Halpha(self, model='gal'):
        self.model= model
        if self.priors['z'][0]==0:
            self.priors['z'][0]=self.z
        
        try:
            if self.priors['zBLR'][0]==0:
                self.priors['zBLR'][0]=self.z
        except:
            lksdf=0
            
        self.fluxs[np.isnan(self.fluxs)] = 0
        self.flux = self.fluxs.data[np.invert(self.fluxs.mask)]
        self.wave = self.wave[np.invert(self.fluxs.mask)]
        
        fit_loc = np.where((self.wave>(6564.52-170)*(1+self.z)/1e4)&(self.wave<(6564.52+170)*(1+self.z)/1e4))[0]
           
        sel=  np.where(((self.wave<(6564.52+20)*(1+self.z)/1e4))& (self.wave>(6564.52-20)*(1+self.z)/1e4))[0]
        
        self.flux_zoom = self.flux[sel]
        self.wave_zoom = self.wave[sel]
        
        peak = np.ma.max(self.flux_zoom)
        nwalkers=32
        
        if self.model=='BLR':
            self.labels=('z', 'cont','cont_grad', 'Hal_peak','BLR_Hal_peak', 'NII_peak', 'Nar_fwhm', 'BLR_fwhm', 'zBLR', 'SIIr_peak', 'SIIb_peak')
            
            self.fitted_model = Halpha_wBLR
            self.log_prior_fce = log_prior_Halpha_BLR
            
            
            self.pr_code = prior_create(self.labels, self.priors)
            
            pos_l = np.array([self.z,np.median(self.flux[fit_loc]),0.001, peak/2, peak/4, peak/4, self.priors['Nar_fwhm'][0], self.priors['BLR_fwhm'][0],self.priors['zBLR'][0],peak/6, peak/6])
            
            for i in enumerate(self.labels):
                pos_l[i[0]] = pos_l[i[0]] if self.priors[i[1]][0]==0 else self.priors[i[1]][0] 
                
            pos = np.random.normal(pos_l, abs(pos_l*0.1), (nwalkers, len(pos_l)))
            pos[:,0] = np.random.normal(self.z,0.001, nwalkers)
            
            self.res = {'name': 'Halpha_wth_BLR'}
            
        
        elif self.model=='gal':
            self.fitted_model = Halpha
            self.log_prior_fce = log_prior_Halpha
            self.labels=('z', 'cont','cont_grad', 'Hal_peak', 'NII_peak', 'Nar_fwhm', 'SIIr_peak', 'SIIb_peak')
            self.pr_code = prior_create(self.labels, self.priors)
            
            pos_l = np.array([self.z,np.median(self.flux[fit_loc]),0.01, peak/2, peak/4,self.priors['Nar_fwhm'][0],peak/6, peak/6 ])
            print(pos_l)
            for i in enumerate(self.labels):
                pos_l[i[0]] = pos_l[i[0]] if self.priors[i[1]][0]==0 else self.priors[i[1]][0] 
            
            pos = np.random.normal(pos_l, abs(pos_l*0.1), (nwalkers, len(pos_l)))
            pos[:,0] = np.random.normal(self.z,0.001, nwalkers)

            self.res = {'name': 'Halpha_wth_BLR'}
            
                
        elif self.model=='outflow':
            self.fitted_model = Halpha_outflow
            self.log_prior_fce = log_prior_Halpha_outflow

            self.labels=('z', 'cont','cont_grad', 'Hal_peak', 'NII_peak', 'Nar_fwhm', 'SIIr_peak', 'SIIb_peak', 'Hal_out_peak', 'NII_out_peak', 'outflow_fwhm', 'outflow_vel')
            self.pr_code = prior_create(self.labels, self.priors)
            
            pos_l = np.array([self.z,np.median(self.flux[fit_loc]),0.01, peak/2, peak/4, self.priors['Nar_fwhm'][0],peak/6, peak/6,peak/8, peak/8, self.priors['outflow_fwhm'][0],self.priors['outflow_vel'][0] ])
            for i in enumerate(self.labels):
                pos_l[i[0]] = pos_l[i[0]] if self.priors[i[1]][0]==0 else self.priors[i[1]][0] 
            
            pos = np.random.normal(pos_l, abs(pos_l*0.1), (nwalkers, len(pos_l)))
            pos[:,0] = np.random.normal(self.z,0.001, nwalkers)
            
            
            self.res = {'name': 'Halpha_wth_out'}
            
        
        elif self.model=='QSO_BKPL':
            
            self.labels=('z', 'cont','cont_grad', 'Hal_peak', 'NII_peak', 'Nar_fwhm',
                    'Hal_out_peak', 'NII_out_peak', 
                    'outflow_fwhm', 'outflow_vel', \
                    'BLR_Hal_peak', 'zBLR', 'BLR_alp1', 'BLR_alp2', 'BLR_sig')
                
                
            pos_l = np.array([self.z,np.median(self.flux[fit_loc]),0.01, peak/2, peak/4, self.priors['Nar_fwhm'][0],\
                              peak/6, peak/6,\
                              self.priors['outflow_fwhm'][0],self.priors['outflow_vel'][0], \
                              peak, self.priors['zBLR'][0], self.priors['BLR_alp1'][0], self.priors['BLR_alp2'][0],self.priors['BLR_sig'][0], \
                              ])
            for i in enumerate(self.labels):
                pos_l[i[0]] = pos_l[i[0]] if self.priors[i[1]][0]==0 else self.priors[i[1]][0]    
            
            
            
            pos = np.random.normal(pos_l, abs(pos_l*0.1), (nwalkers, len(pos_l)))
            pos[:,0] = np.random.normal(self.z,0.001, nwalkers)
            
            self.pr_code = prior_create(self.labels, self.priors)
            
            self.fitted_self.model = Hal_QSO_BKPL
            self.log_prior_fce = logprior_general
            
            self.res = {'name': 'Halpha_QSO_BKPL'}
            
        else:
            raise Exception('self.model variable not understood. Available self.model keywords: BLR, outflow, gal, QSO_BKPL')
             
        
        nwalkers, ndim = pos.shape
        sampler = emcee.EnsembleSampler(
             nwalkers, ndim, log_probability_general, args=(self.wave[fit_loc], self.flux[fit_loc], self.error[fit_loc],self.pr_code, self.fitted_model, self.log_prior_fce))
     
        sampler.run_mcmc(pos, self.N, progress=self.progress)
        self.flat_samples = sampler.get_chain(discard=int(0.25*N), thin=15, flat=True)      
        for i in range(len(self.labels)):
            self.res[self.labels[i]] = self.flat_samples[:,i]  
            
        self.chains = self.res
        self.props = sp.prop_calc(self.chains)
        self.chi2, self.BIC = sp.BIC_calc(self.wave, self.fluxs, self.error, self.fitted_model, self.props, 'Halpha')

        
    # =============================================================================
    # Primary function to fit [OIII] with and without outflows. 
    # =============================================================================
    
    def fitting_OIII(self, model, template=0, Hbeta_dual=0):
        self.model = model
        self.template = template
        self.Hbeta_dual = Hbeta_dual
        if self.priors['z'][2]==0:
            self.priors['z'][2]=z
        
        self.flux = self.fluxs.data[np.invert(self.fluxs.mask)]
        self.wave = self.wave[np.invert(self.fluxs.mask)]
        
        fit_loc = np.where((self.wave>4700*(1+self.z)/1e4)&(self.wave<5100*(1+self.z)/1e4))[0]
        
        sel=  np.where((self.wave<5025*(1+self.z)/1e4)& (self.wave>4980*(1+self.z)/1e4))[0]
        self.flux_zoom = self.flux[sel]
        self.wave_zoom = self.wave[sel]
        
        peak_loc = np.argmax(self.flux_zoom)
        peak = (np.max(self.flux_zoom))
        
        selb =  np.where((self.wave<4880*(1+self.z)/1e4)& (self.wave>4820*(1+self.z)/1e4))[0]
        self.flux_zoomb = self.flux[selb]
        self.wave_zoomb = self.wave[selb]
        try:
            peak_loc_beta = np.argmax(self.flux_zoomb)
            peak_beta = (np.max(self.flux_zoomb))
        except:
            peak_beta = peak/3
        
        
        nwalkers=64
        if self.model=='outflow': 
            if self.template==0:
                if self.Hbeta_dual == 0:
                    self.labels=('z', 'cont','cont_grad', 'OIII_peak', 'OIII_out_peak', 'Nar_fwhm', 'outflow_fwhm', 'outflow_vel', 'Hbeta_peak', 'Hbeta_fwhm','Hbeta_vel')
                    self.fitted_model = OIII_outflow
                    self.log_prior_fce = log_prior_OIII_outflow
                    
                    self.pr_code = prior_create(self.labels, self.priors)
                    
                    pos_l = np.array([self.z,np.median(self.flux[fit_loc]),0.001, peak/2, peak/6, self.priors['Nar_fwhm'][0], self.priors['outflow_fwhm'][0],self.priors['outflow_vel'][0], peak_beta, self.priors['Hbeta_fwhm'][0],self.priors['Hbeta_vel'][0]])
                    for i in enumerate(self.labels):
                        pos_l[i[0]] = pos_l[i[0]] if self.priors[i[1]][0]==0 else self.priors[i[1]][0] 
                    pos = np.random.normal(pos_l, abs(pos_l*0.1), (nwalkers, len(pos_l)))
                    pos[:,0] = np.random.normal(self.z,0.001, nwalkers)
            
                    self.res = {'name': 'OIII_outflow'}
                    
                else:
                    self.labels= ('z', 'cont','cont_grad', 'OIII_peak', 'OIII_out_peak', 'Nar_fwhm', 'outflow_fwhm', 'outflow_vel', 'Hbeta_peak', 'Hbeta_fwhm','Hbeta_vel','Hbetan_peak', 'Hbetan_fwhm','Hbetan_vel')
                    self.fitted_model = OIII_outflow_narHb
                    self.log_prior_fce = log_prior_OIII_outflow_narHb
                    
                    self.pr_code = prior_create(self.labels, self.priors)
                    
                    pos_l = np.array([self.z,np.median(self.flux[fit_loc]),0.001, peak/2, peak/6, self.priors['Nar_fwhm'][0], self.priors['outflow_fwhm'][0],self.priors['outflow_vel'][0],\
                                    peak_beta, self.priors['Hbeta_fwhm'][0], self.priors['Hbeta_vel'][0],peak_beta, self.priors['Hbetan_fwhm'][0], self.priors['Hbetan_vel'][0]])
                    for i in enumerate(self.labels):
                        pos_l[i[0]] = pos_l[i[0]] if self.priors[i[1]][0]==0 else self.priors[i[1]][0] 
                    pos = np.random.normal(pos_l, abs(pos_l*0.1), (nwalkers, len(pos_l)))
                    pos[:,0] = np.random.normal(self.z,0.001, nwalkers)
                    
                    self.res = {'name': 'OIII_outflow_HBn'}
                    
             
            else:
                if self.Hbeta_dual == 0:
                    self.labels=('z', 'cont','cont_grad', 'OIII_peak', 'OIII_out_peak', 'Nar_fwhm', 'outflow_fwhm', 'outflow_vel', 'Hbeta_peak', 'Hbeta_fwhm','Hbeta_vel', 'Fe_peak', 'Fe_fwhm')
                    self.fitted_model = OIII_outflow_Fe
                    self.log_prior_fce = log_prior_OIII_outflow_Fe
                    
                    self.pr_code = prior_create(self.labels, self.priors)
                    
                    pos_l = np.array([self.z,np.median(self.flux[fit_loc]),0.001, peak/2, peak/6, self.priors['Nar_fwhm'][0], self.priors['OIII_out'][0],self.priors['outflow_vel'][0], peak_beta, self.priors['Hbeta_fwhm'][0],self.priors['Hbeta_vel'][0],\
                                    np.median(self.flux[fit_loc]), self.priors['Fe_fwhm'][0]])
                        
                    for i in enumerate(self.labels):
                        pos_l[i[0]] = pos_l[i[0]] if self.priors[i[1]][0]==0 else self.priors[i[1]][0] 
                    pos = np.random.normal(pos_l, abs(pos_l*0.1), (nwalkers, len(pos_l)))
                    pos[:,0] = np.random.normal(self.z,0.001, nwalkers)
                    
                    self.res = {'name': 'OIII_outflow_Fe'}
                        
                else:
                    self.labels= ('z', 'cont','cont_grad', 'OIII_peak', 'OIII_out_peak', 'Nar_fwhm', 'outflow_fwhm', 'outflow_vel', 'Hbeta_peak', 'Hbeta_fwhm','Hbeta_vel','Hbetan_peak', 'Hbetan_fwhm','Hbetan_vel', 'Fe_peak', 'Fe_fwhm')
                    self.fitted_model = OIII_outflow_Fe_narHb
                    self.pr_code = prior_create(self.labels, self.priors)
                    
                    pos_l = np.array([self.z,np.median(self.flux[fit_loc])/2,0.001, peak/2, peak/4, 300., 600.,-100, \
                                    peak_beta/2, 4000,self.priors['Hbeta_vel'][0],peak_beta/2, 600,self.priors['Hbetan_vel'][0],\
                                    np.median(self.flux[fit_loc]), 2000])
                    
                    for i in enumerate(self.labels):
                        pos_l[i[0]] = pos_l[i[0]] if self.priors[i[1]][0]==0 else self.priors[i[1]][0] 
                    pos = np.random.normal(pos_l, abs(pos_l*0.1), (nwalkers, len(pos_l)))
                    pos[:,0] = np.random.normal(self.z,0.001, nwalkers)
                
                    self.res = {'name': 'OIII_outflow_Fe_narHb'}
                    
                
        elif self.model=='gal': 
            if self.template==0:
                if self.Hbeta_dual == 0:
                    self.labels=('z', 'cont','cont_grad', 'OIII_peak', 'Nar_fwhm', 'Hbeta_peak', 'Hbeta_fwhm','Hbeta_vel')
                    self.fitted_model = OIII
                    self.log_prior_fce = log_prior_OIII
                    self.pr_code = prior_create(self.labels, self.priors)
                    
                    pos_l = np.array([self.z,np.median(self.flux[fit_loc]),0.001, peak/2,  self.priors['Nar_fwhm'][0], peak_beta, self.priors['Hbeta_fwhm'][0],self.priors['Hbeta_vel'][0]]) 
                    for i in enumerate(self.labels):
                        pos_l[i[0]] = pos_l[i[0]] if self.priors[i[1]][0]==0 else self.priors[i[1]][0] 
                    pos = np.random.normal(pos_l, abs(pos_l*0.1), (nwalkers, len(pos_l)))
                    pos[:,0] = np.random.normal(self.z,0.001, nwalkers)
                    
                    self.res = {'name': 'OIII'}
                    
            
                else:
                    self.labels=('z', 'cont','cont_grad', 'OIII_peak', 'Nar_fwhm', 'Hbeta_peak', 'Hbeta_fwhm','Hbeta_vel','Hbetan_peak', 'Hbetan_fwhm','Hbetan_vel')
                    self.fitted_model = OIII_dual_hbeta
                    self.log_prior_fce = log_prior_OIII_dual_hbeta
                    
                    self.pr_code = prior_create(self.labels, self.priors)
                    
                    pos_l = np.array([self.z,np.median(self.flux[fit_loc]),0.001, peak/2,  self.priors['Nar_fwhm'][0], peak_beta/4, self.priors['Hbeta_fwhm'][0],self.priors['Hbeta_vel'][0],\
                                    peak_beta/4, self.priors['Hbetan_fwhm'][0], self.priors['Hbetan_vel'][0]])
                    for i in enumerate(self.labels):
                        pos_l[i[0]] = pos_l[i[0]] if self.priors[i[1]][0]==0 else self.priors[i[1]][0] 
                         
                    self.res = {'name': 'OIII_HBn'}
            

            else:
                if self.Hbeta_dual == 0:
                    self.labels=('z', 'cont','cont_grad', 'OIII_peak', 'Nar_fwhm', 'Hbeta_peak', 'Hbeta_fwhm','Hbeta_vel', 'Fe_peak', 'Fe_fwhm')
                    self.fitted_model = OIII_Fe
                    self.log_prior_fce = log_prior_OIII_Fe
                    
                    self.pr_code = prior_create(self.labels, self.priors)
                    
                    pos_l = np.array([self.z,np.median(self.flux[fit_loc]),0.001, peak/2,  self.priors['OIII_fwhm'][0], peak_beta, self.priors['Hbeta_fwhm'][0],self.priors['Hbeta_vel'][0],np.median(self.flux[fit_loc]), self.priors['Fe_fwhm'][0]]) 
                    for i in enumerate(self.labels):
                        pos_l[i[0]] = pos_l[i[0]] if self.priors[i[1]][0]==0 else self.priors[i[1]][0] 
                    
                    self.res = {'name': 'OIII_Fe'}
                
                else:
                    self.labels=('z', 'cont','cont_grad', 'OIII_peak', 'Nar_fwhm', 'Hbeta_peak', 'Hbeta_fwhm','Hbeta_vel','Hbetan_peak', 'Hbetan_fwhm','Hbetan_vel','Fe_peak', 'Fe_fwhm')
                    self.fitted_model = OIII_dual_hbeta_Fe
                    self.log_prior_fce = log_prior_OIII_dual_hbeta_Fe
                    
                    self.pr_code = prior_create(self.labels, self.priors)
                    
                    pos_l = np.array([self.z,np.median(self.flux[fit_loc]),0.001, peak/2,  self.priors['OIII_fwhm'][0], peak_beta/2, self.priors['Hbeta_fwhm'][0],self.priors['Hbeta_vel'][0],\
                                    peak_beta/2, self.priors['Hbetan_fwhm'][0],self.priors['Hbetan_vel'][0], \
                                    np.median(self.flux[fit_loc]), self.priors['Fe_fwhm'][0]]) 
                    for i in enumerate(self.labels):
                        pos_l[i[0]] = pos_l[i[0]] if self.priors[i[1]][0]==0 else self.priors[i[1]][0] 
                        
                    self.res = {'name': 'OIII_Fe_HBn'}
        
                    
        elif self.model=='QSO_BKPL':
            self.labels=('z', 'cont','cont_grad', 'OIII_peak', 'OIII_out_peak', 'Nar_fwhm', 'outflow_fwhm',\
                        'outflow_vel', 'BLR_peak', 'zBLR', 'BLR_alp1', 'BLR_alp2','BLR_sig' ,\
                        'Hb_nar_peak', 'Hb_out_peak')
                
            pos_l = np.array([self.z,np.median(self.flux[fit_loc]),0.001, peak/2, peak/6,\
                    self.priors['Nar_fwhm'][0], self.priors['outflow_fwhm'][0],self.priors['outflow_vel'][0],\
                    peak_beta, self.priors['zBLR'][0], self.priors['BLR_alp1'][0], self.priors['BLR_alp2'][0],self.priors['BLR_sig'][0], \
                    peak_beta/4, peak_beta/4])
            
                
            for i in enumerate(self.labels):
                pos_l[i[0]] = pos_l[i[0]] if self.priors[i[1]][0]==0 else self.priors[i[1]][0]    
            pos = np.random.normal(pos_l, abs(pos_l*0.1), (nwalkers, len(pos_l)))
            pos[:,0] = np.random.normal(self.z,0.001, nwalkers)
            pos[:,9] = np.random.normal(self.z,0.001, nwalkers)
            
            self.pr_code = prior_create(self.labels, self.priors)
            self.fitted_model = OIII_QSO_BKPL
            self.log_prior_fce = logprior_general
             
            self.res = {'name': 'OIII_QSO_BKP'}
            
        else:
            raise Exception('self.model variable not understood. Available self.model keywords: outflow, gal, QSO_BKPL')
         
        nwalkers, ndim = pos.shape
        
        if self.template==0:
            sampler = emcee.EnsembleSampler(
                 nwalkers, ndim, log_probability_general, args=(self.wave[fit_loc], self.flux[fit_loc], self.error[fit_loc],self.pr_code, self.fitted_model, self.log_prior_fce))
        
        else:
            sampler = emcee.EnsembleSampler(
                 nwalkers, ndim, log_probability_general, args=(self.wave[fit_loc], self.flux[fit_loc], self.error[fit_loc],self.pr_code, self.fitted_model, self.log_prior_fce, self.template))
            
     
        sampler.run_mcmc(pos, self.N, progress=self.progress)
        self.flat_samples = sampler.get_chain(discard=int(0.25*N), thin=15, flat=True)      
        
        for i in range(len(self.labels)):
            self.res[self.labels[i]] = self.flat_samples[:,i]  
        
        self.chains = self.res
        self.props = sp.prop_calc(self.chains)
        self.chi2, self.BIC = sp.BIC_calc(self.wave, self.fluxs, self.error, self.fitted_model, self.props, 'OIII')

        
    def fitting_Halpha_OIII(self, model):
        self.model = model
        
        if self.priors['z'][2]==0:
            self.priors['z'][2]=self.z
        try:
            if self.priors['zBLR'][2]==0:
                self.priors['zBLR'][2]=self.z
        except:
            lksdf=0
            
            
        self.flux = self.fluxs.data[np.invert(self.fluxs.mask)]
        self.wave = self.wave[np.invert(self.fluxs.mask)]
        
        fit_loc = np.where((self.wave>4700*(1+self.z)/1e4)&(self.wave<5100*(1+self.z)/1e4))[0]
        fit_loc = np.append(fit_loc, np.where((self.wave>(6300-50)*(1+self.z)/1e4)&(self.wave<(6300+50)*(1+self.z)/1e4))[0])
        fit_loc = np.append(fit_loc, np.where((self.wave>(6564.52-170)*(1+self.z)/1e4)&(self.wave<(6564.52+170)*(1+self.z)/1e4))[0])
        
    # =============================================================================
    #     Finding the initial conditions
    # =============================================================================
        sel=  np.where((self.wave<5025*(1+self.z)/1e4)& (self.wave>4980*(1+self.z)/1e4))[0]
        self.flux_zoom = self.flux[sel]
        self.wave_zoom = self.wave[sel]
        try:
            peak_loc_OIII = np.argmax(self.flux_zoom)
            peak_OIII = (np.max(self.flux_zoom))
        except:
            peak_OIII = np.max(self.flux[fit_loc])
        
        sel=  np.where(((self.wave<(6564.52+20)*(1+self.z)/1e4))& (self.wave>(6564.52-20)*(1+self.z)/1e4))[0]
        self.flux_zoom = self.flux[sel]
        self.wave_zoom = self.wave[sel]
        
        peak_loc = np.ma.argmax(self.flux_zoom)
        
        znew = self.wave_zoom[peak_loc]/0.656452-1
        peak_hal = np.ma.max(self.flux_zoom)
        if peak_hal<0:
            peak_hal==3e-3
        
    # =============================================================================
    #   Setting up fitting  
    # =============================================================================
        if self.model=='gal':
            #self.priors['z'] = [z, z-zcont, z+zcont]
            nwalkers=64
            self.fitted_model = Halpha_OIII
            self.log_prior_fce = log_prior_Halpha_OIII
            
            self.labels=('z', 'cont','cont_grad', 'Hal_peak', 'NII_peak', 'Nar_fwhm', 'SIIr_peak', 'SIIb_peak', 'OIII_peak', 'Hbeta_peak', 'OI_peak')
            
            self.pr_code = prior_create(self.labels, self.priors)
            
            
            pos_l = np.array([self.z,np.median(self.flux[fit_loc]), -0.1, peak_hal*0.7, peak_hal*0.3, self.priors['Nar_fwhm'][0], peak_hal*0.15, peak_hal*0.2, peak_OIII*0.8,\
                              peak_hal*0.2, peak_OIII*0.1])  
            
            for i in enumerate(self.labels):
                pos_l[i[0]] = pos_l[i[0]] if self.priors[i[1]][0]==0 else self.priors[i[1]][0] 
                
            if (self.log_prior_fce(pos_l, self.pr_code)==-np.inf):
                logprior_general_test(pos_l, self.pr_code, self.labels)
                
                raise Exception('Logprior function returned nan or -inf on initial conditions. You should double check that your self.priors\
                                boundries are sensible. {pos_l}')
                
            pos = np.random.normal(pos_l, abs(pos_l*0.1), (nwalkers, len(pos_l)))
            pos[:,0] = np.random.normal(self.z,0.001, nwalkers)
            
            self.res = {'name': 'Halpha_OIII'}
            
            
        elif self.model=='outflow':
            nwalkers=64
            self.fitted_model = Halpha_OIII_outflow
            
            self.labels=('z', 'cont','cont_grad', 'Hal_peak', 'NII_peak','OIII_peak', 'Hbeta_peak','SIIr_peak', 'SIIb_peak','OI_peak',\
                    'Nar_fwhm', 'outflow_fwhm', 'outflow_vel', 'Hal_out_peak','NII_out_peak', 'OIII_out_peak', 'OI_out_peak', 'Hbeta_out_peak'   )
            
            self.pr_code = prior_create(self.labels, self.priors)   
            self.log_prior_fce = log_prior_Halpha_OIII_outflow
            
            pos_l = np.array([self.z,np.median(self.flux[fit_loc]), -0.1, peak_hal*0.7, peak_hal*0.3, \
                              peak_OIII*0.8, peak_hal*0.2, peak_hal*0.2, peak_hal*0.2, peak_hal*0.1,\
                              self.priors['Nar_fwhm'][0], self.priors['outflow_fwhm'][0], self.priors['outflow_vel'][0],
                              peak_hal*0.3, peak_hal*0.3, peak_OIII*0.2, peak_hal*0.05, peak_hal*0.05])
            
            for i in enumerate(self.labels):
                pos_l[i[0]] = pos_l[i[0]] if self.priors[i[1]][0]==0 else self.priors[i[1]][0] 
                
            if (self.log_prior_fce(pos_l, self.pr_code)==-np.inf):
                
                logprior_general_test(pos_l, self.pr_code, self.labels)
                
                raise Exception('Logprior function returned nan or -inf on initial conditions. You should double check that your self.priors\
                                boundries are sensible. {%pos_l}')
                                
            pos = np.random.normal(pos_l, abs(pos_l*0.1), (nwalkers, len(pos_l)))
            pos[:,0] = np.random.normal(self.z,0.001, nwalkers)
            
            self.res = {'name': 'Halpha_OIII_outflow'}
            
            
        elif self.model=='BLR':
            self.labels=('z', 'cont','cont_grad', 'Hal_peak', 'NII_peak','OIII_peak', 'Hbeta_peak','SIIr_peak', 'SIIb_peak',\
                    'Nar_fwhm', 'outflow_fwhm', 'outflow_vel', 'Hal_out_peak','NII_out_peak', 'OIII_out_peak', 'Hbeta_out_peak' ,\
                    'BLR_fwhm', 'zBLR', 'BLR_Hal_peak', 'BLR_Hbeta_peak')
                
            nwalkers=64
            
            if self.priors['BLR_Hal_peak'][2]=='self.error':
                self.priors['BLR_Hal_peak'][2]=self.error[-2]; self.priors['BLR_Hal_peak'][3]=self.error[-2]*2
            if self.priors['BLR_Hbeta_peak'][2]=='self.error':
                self.priors['BLR_Hbeta_peak'][2]=self.error[2]; self.priors['BLR_Hbeta_peak'][3]=self.error[2]*2
            
            self.pr_code = prior_create(self.labels, self.priors)   
            self.log_prior_fce = self.log_prior_Halpha_OIII_BLR
            self.fitted_model = Halpha_OIII_BLR
            
            pos_l = np.array([self.z,np.median(self.flux[fit_loc]), -0.1, peak_hal*0.7, peak_hal*0.3, \
                              peak_OIII*0.8, peak_hal*0.3 , peak_hal*0.2, peak_hal*0.2,\
                              self.priors['Nar_fwhm'][0], self.priors['outflow_fwhm'][0], self.priors['outflow_vel'][0],
                              peak_hal*0.3, peak_hal*0.3, peak_OIII*0.2, peak_hal*0.1,\
                              self.priors['BLR_fwhm'][0], self.priors['zBLR'][0], peak_hal*0.3, peak_hal*0.1])
                
            for i in enumerate(self.labels):
                pos_l[i[0]] = pos_l[i[0]] if self.priors[i[1]][0]==0 else self.priors[i[1]][0] 
                 
            
            
            if (self.log_prior(pos_l, self.pr_code)==np.nan)|\
                (self.log_prior_fce(pos_l, self.pr_code)==-np.inf):
                print(logprior_general_test(pos_l, self.pr_code, self.labels))
                raise Exception('Logprior function returned nan or -inf on initial conditions. You should double check that your self.priors\
                                boundries are sensible. {pos_l} ')
            
            pos = np.random.normal(pos_l, abs(pos_l*0.1), (nwalkers, len(pos_l)))
            pos[:,0] = np.random.normal(self.z,0.001, nwalkers)
            pos[:,-3] = np.random.normal(self.priors['zBLR'][0],0.00001, nwalkers)
           
            self.res = {'name': 'Halpha_OIII_BLR'}
            
        elif self.model=='BLR_simple':
            self.labels=('z', 'cont','cont_grad', 'Hal_peak', 'NII_peak','OIII_peak', 'Hbeta_peak','SIIr_peak', 'SIIb_peak',\
                    'Nar_fwhm', 'BLR_fwhm', 'zBLR', 'BLR_Hal_peak', 'BLR_Hbeta_peak')
                
            nwalkers=64
            
            if self.priors['BLR_Hal_peak'][2]=='self.error':
                self.priors['BLR_Hal_peak'][2]=self.error[-2]; self.priors['BLR_Hal_peak'][3]=self.error[-2]*2
            if self.priors['BLR_Hbeta_peak'][2]=='self.error':
                self.priors['BLR_Hbeta_peak'][2]=self.error[2]; self.priors['BLR_Hbeta_peak'][3]=self.error[2]*2
            
            self.pr_code = prior_create(self.labels, self.priors) 
            self.log_prior_fce = self.log_prior_Halpha_OIII_BLR_simple
            self.fitted_model = Halpha_OIII_BLR_simple
            
            pos_l = np.array([self.z,np.median(self.flux[fit_loc]), -0.1, peak_hal*0.7, peak_hal*0.3, \
                              peak_OIII*0.8, peak_hal*0.3 , peak_hal*0.2, peak_hal*0.2,\
                              self.priors['Nar_fwhm'][0], self.priors['BLR_fwhm'][0], self.priors['zBLR'][0], peak_hal*0.3, peak_hal*0.1])
                
            for i in enumerate(self.labels):
                pos_l[i[0]] = pos_l[i[0]] if self.priors[i[1]][0]==0 else self.priors[i[1]][0] 
            
            if (self.log_prior_fce(pos_l, self.pr_code)==np.nan)|\
                (self.log_prior(pos_l, self.pr_code)==-np.inf):
                print(logprior_general_test(pos_l, self.pr_code, self.labels))
                raise Exception('Logprior function returned nan or -inf on initial conditions. You should double check that your self.priors\
                                boundries are sensible. {pos_l} ')
            
            pos = np.random.normal(pos_l, abs(pos_l*0.1), (nwalkers, len(pos_l)))
            pos[:,0] = np.random.normal(z,0.001, nwalkers)
            pos[:,-3] = np.random.normal(self.priors['zBLR'][0],0.00001, nwalkers)
           
            self.res = {'name': 'Halpha_OIII_BLR_simple'}
            
            
        elif outflow=='QSO_BKPL':
            self.labels =[ 'z', 'cont','cont_grad', 'Hal_peak', 'NII_peak', 'OIII_peak','Hbeta_peak', 'Nar_fwhm', \
                                  'Hal_out_peak', 'NII_out_peak','OIII_out_peak', 'Hbeta_out_peak',\
                                  'outflow_fwhm', 'outflow_vel',\
                                  'Hal_BLR_peak', 'Hbeta_BLR_peak',  'BLR_vel', 'BLR_alp1', 'BLR_alp2', 'BLR_sig']
        
        
            nwalkers=64
            self.pr_code = prior_create(self.labels, self.priors)   
            self.log_prior_fce = logprior_general
            self.fitted_model =  Halpha_OIII_QSO_BKPL
            pos_l = np.array([self.z,np.median(self.flux[fit_loc]), -0.1, peak_hal*0.7, peak_hal*0.3, \
                              peak_OIII*0.8, peak_OIII*0.3,self.priors['Nar_fwhm'][0],\
                              peak_hal*0.2, peak_hal*0.3, peak_OIII*0.4, peak_OIII*0.2   ,\
                              self.priors['outflow_fwhm'][0], self.priors['outflow_vel'][0],\
                              peak_hal*0.4, peak_OIII*0.4, self.priors['BLR_vel'][0], 
                              self.priors['BLR_alp1'][0], self.priors['BLR_alp2'][0],self.priors['BLR_sig'][0]])
            
            if (self.log_prior_fce(pos_l, self.pr_code)==np.nan)|\
                (self.log_prior(pos_l, self.pr_code)==-np.inf):
                raise Exception('Logprior function returned nan or -inf on initial conditions. You should double check that your self.priors\
                                boundries are sensible: {pos_l}')
                                
            pos = np.random.normal(pos_l, abs(pos_l*0.1), (nwalkers, len(pos_l)))
            pos[:,0] = np.random.normal(self.z,0.001, nwalkers)
            
            self.res = {'name': 'Halpha_OIII_BLR'}
            
        else:
            raise Exception('self.model variable not understood. Available self.model keywords: outflow, gal, QSO_BKPL')
        
            
        nwalkers, ndim = pos.shape
        sampler = emcee.EnsembleSampler(
                nwalkers, ndim, log_probability_general, args=(self.wave[fit_loc], self.flux[fit_loc], self.error[fit_loc],self.pr_code, self.fitted_model, self.log_prior_fce)) 
        sampler.run_mcmc(pos, self.N, progress=self.progress);
        
        self.flat_samples = sampler.get_chain(discard=int(0.5*N), thin=15, flat=True)
        
        
        for i in range(len(self.labels)):
            self.res[self.labels[i]] = self.flat_samples[:,i]
        self.chains = self.res
        self.props = sp.prop_calc(self.chains)
        
        self.chi2, self.BIC = sp.BIC_calc(self.wave, self.fluxs, self.error, self.fitted_model, self.props, 'Halpha_OIII')

        
        
    def fitting_general(fitted_model, labels, logprior, nwalkers=64):
        self.labels= labels
        self.log_prior_fce = logprior_general
        self.fitted_model = fitted_model
        
        if self.priors['z'][2]==0:
            self.priors['z'][2]=self.z
            
        self.flux = self.fluxs.data[np.invert(self.fluxs.mask)]
        self.wave = self.wave[np.invert(self.fluxs.mask)]
        
        self.pr_code = prior_create(self.labels, self.priors)
       
        pos_l = np.zeros(len(self.labels))
            
        for i in enumerate(self.labels):
            pos_l[i[0]] = self.priors[i[1]][0] 
                
        if (self.log_prior_fce(pos_l, self.pr_code)==-np.inf):
            logprior_general_test(pos_l, self.pr_code, self.labels)
                
            raise Exception('Logprior function returned nan or -inf on initial conditions. You should double check that your priors\
                            boundries are sensible')
                
        pos = np.random.normal(pos_l, abs(pos_l*0.1), (nwalkers, len(pos_l)))
        pos[:,0] = np.random.normal(self.z,0.001, nwalkers)
            
        nwalkers, ndim = pos.shape
        sampler = emcee.EnsembleSampler(
        nwalkers, ndim, log_probability_general, args=(self.wave, self.flux, self.error,self.pr_code, self.fitted_model, self.log_prior_fce)) 
        sampler.run_mcmc(pos, self.N, progress=self.progress);
            
        flat_samples = sampler.get_chain(discard=int(0.5*self.N), thin=15, flat=True)
            
        res = {'name': 'Custom model'}
        for i in range(len(labels)):
            res[labels[i]] = flat_samples[:,i]
        
        self.res= res
        
       

import numba
@numba.njit
def logprior_general(theta, priors):
    results = 0.
    for t,p in zip( theta, priors):
        if p[0] ==0:
            results += -np.log(p[2]) - 0.5*np.log(2*np.pi) - 0.5 * ((t-p[1])/p[2])**2
        elif p[0] ==1:
            results+= np.log((p[1]<t<p[2])/(p[2]-p[1])) 
        elif p[0]==2:
            results+= -np.log(p[2]) - 0.5*np.log(2*np.pi) - 0.5 * ((np.log10(t)-p[1])/p[2])**2
        elif p[0]==3:
            results+= np.log((p[1]<np.log10(t)<p[2])/(p[2]-p[1]))
    
    return results




def log_probability_general(theta, x, y, yerr, priors, model, logpriorfce, template=None):
    lp = logpriorfce(theta,priors)
    
    try:
        if not np.isfinite(lp):
            return -np.inf
    except:
        lp[np.isnan(lp)] = -np.inf
    
    if template:
        evalm = model(x,*theta, template)
    else:
        evalm = model(x,*theta)
       
    sigma2 = yerr*yerr
    log_likelihood = -0.5 * np.sum((y - evalm) ** 2 / sigma2) #+ np.log(2*np.pi*sigma2))
    
    return lp + log_likelihood



def logprior_general_test(theta, priors, labels):
    for t,p,lb in zip( theta, priors, labels):
        print(p)
        if p[0] ==0:
            results = -np.log(p[2]) - 0.5*np.log(2*np.pi) - 0.5 * ((t-p[1])/p[2])**2
        elif p[0] ==1:
            results = np.log((p[1]<t<p[2])/(p[2]-p[1])) 
        elif p[0]==2:
            results = -np.log(p[2]) - 0.5*np.log(2*np.pi) - 0.5 * ((np.log10(t)-p[1])/p[2])**2
        elif p[0]==3:
            results = np.log((p[1]<np.log10(t)<p[2])/(p[2]-p[1]))
    
        print(lb, t, results)
        
def prior_create(labels,priors):
    pr_code = np.zeros((len(labels),3))
    
    for key in enumerate(labels):
        if priors[key[1]][1] == 'normal':
            pr_code[key[0]][0] = 0
            
        
        elif priors[key[1]][1] == 'lognormal':
            pr_code[key[0]][0] = 2
            
        elif priors[key[1]][1] == 'uniform':
            pr_code[key[0]][0] = 1
            
        elif priors[key[1]][1] == 'loguniform':
            pr_code[key[0]][0] = 3
        
        else:
            raise Exception('Sorry mode in prior type not understood: ', key )
        
        pr_code[key[0]][1] = priors[key[1]][2]
        pr_code[key[0]][2] = priors[key[1]][3]
    return pr_code

def Fitting_OIII_unwrap(lst):
    
    i,j,flx_spax_m, error, wave, z = lst
    
    with open(os.getenv("HOME")+'/priors.pkl', "rb") as fp:
        priors= pickle.load(fp) 
    
    flat_samples_sig, fitted_model_sig = fitting_OIII(wave,flx_spax_m,error,z, model='gal', progress=False, priors=priors)
    cube_res  = [i,j,sp.prop_calc(flat_samples_sig)]
    return cube_res

def Fitting_Halpha_OIII_unwrap(lst, progress=False):
    with open(os.getenv("HOME")+'/priors.pkl', "rb") as fp:
        priors= pickle.load(fp) 
    i,j,flx_spax_m, error, wave, z = lst
    deltav = 1500
    deltaz = deltav/3e5*(1+z)
    try:
        flat_samples_sig, fitted_model_sig = fitting_Halpha_OIII(wave,flx_spax_m,error,z,zcont=deltaz, progress=progress, priors=priors,N=10000)
        cube_res  = [i,j,sp.prop_calc(flat_samples_sig), flat_samples_sig,wave,flx_spax_m,error]
    except:
        cube_res = [i,j, {'Failed fit':0}, {'Failed fit':0}]
    return cube_res

def Fitting_Halpha_OIII_AGN_unwrap(lst, progress=False):
    with open(os.getenv("HOME")+'/priors.pkl', "rb") as fp:
        priors= pickle.load(fp) 
    i,j,flx_spax_m, error, wave, z = lst
    deltav = 1500
    deltaz = deltav/3e5*(1+z)
    try:
        flat_samples_sig, fitted_model_sig = fitting_Halpha_OIII(wave,flx_spax_m,error,z,zcont=deltaz, progress=progress, priors=priors, model='BLR', N=10000)
        cube_res  = [i,j,sp.prop_calc(flat_samples_sig), flat_samples_sig,wave,flx_spax_m,error ]
    except:
        cube_res = [i,j, {'Failed fit':0}, {'Failed fit':0}]
    return cube_res

def Fitting_Halpha_OIII_outflowboth_unwrap(lst, progress=False):
    with open(os.getenv("HOME")+'/priors.pkl', "rb") as fp:
        priors= pickle.load(fp) 
     
    
    i,j,flx_spax_m, error, wave, z = lst
    deltav = 1500
    deltaz = deltav/3e5*(1+z)
    try:
        flat_samples_sig, fitted_model_sig = fitting_Halpha_OIII(wave,flx_spax_m,error,z,zcont=deltaz, progress=progress, priors=priors, model='gal', N=10000)    
        flat_samples_out, fitted_model_out = fitting_Halpha_OIII(wave,flx_spax_m,error,z,zcont=deltaz, progress=progress, priors=priors, model='outflow', N=10000)
        
        BIC_sig = sp.BIC_calc(wave, flx_spax_m, error, fitted_model_sig, sp.prop_calc(flat_samples_sig), 'Halpha_OIII' )
        BIC_out = sp.BIC_calc(wave, flx_spax_m, error, fitted_model_out, sp.prop_calc(flat_samples_out), 'Halpha_OIII' )
        
        if (BIC_sig[1]-BIC_out[1])>5:
            fitted_model = fitted_model_out
            flat_samples = flat_samples_out
        else:
            fitted_model = fitted_model_sig
            flat_samples = flat_samples_sig
            
        cube_res  = [i,j,sp.prop_calc(flat_samples), flat_samples,wave,flx_spax_m,error ]
    except:
        cube_res = [i,j, {'Failed fit':0}, {'Failed fit':0}]
        print('Failed fit')
    return cube_res

def Fitting_OIII_2G_unwrap(lst, priors):
    with open(os.getenv("HOME")+'/priors.pkl', "rb") as fp:
        priors= pickle.load(fp) 
        
    i,j,flx_spax_m, error, wave, z = lst
    
    try:
        flat_samples_sig, fitted_model_sig = fitting_OIII(wave,flx_spax_m,error,z, model='gal', progress=False, priors=priors) 
        flat_samples_out, fitted_model_out = fitting_OIII(wave,flx_spax_m,error,z, model='outflow', progress=False, priors=priors)
        
        BIC_sig = sp.BIC_calc(wave, flx_spax_m, error, fitted_model_sig, sp.prop_calc(flat_samples_sig), 'OIII' )
        BIC_out = sp.BIC_calc(wave, flx_spax_m, error, fitted_model_out, sp.prop_calc(flat_samples_out), 'OIII' )
        
        if (BIC_sig[1]-BIC_out[1])>5:
            fitted_model = fitted_model_out
            flat_samples = flat_samples_out
        else:
            fitted_model = fitted_model_sig
            flat_samples = flat_samples_sig
            
        cube_res  = [i,j,sp.prop_calc(flat_samples), flat_samples,wave,flx_spax_m,error ]
    except:
        cube_res = [i,j, {'Failed fit':0}, {'Failed fit':0}]
        print('Failed fit')
    return cube_res
    
import time

def Fitting_Halpha_unwrap(lst): 
    
    with open(os.getenv("HOME")+'/priors.pkl', "rb") as fp:
        priors= pickle.load(fp) 
    
    i,j,flx_spax_m, error, wave, z = lst
    
    deltav = 1500
    deltaz = deltav/3e5*(1+z)
    flat_samples_sig, fitted_model_sig = fitting_Halpha(wave,flx_spax_m,error,z, zcont=deltaz, model='BLR', progress=False, priors=priors,N=10000)
    cube_res  = [i,j,sp.prop_calc(flat_samples_sig)]
    
    return cube_res
    
    

