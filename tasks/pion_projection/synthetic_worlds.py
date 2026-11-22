"""Versioned paired synthetic signals for fixed basis1/basis2 MC."""
import numpy as np
from .statistics import shape

def generate_world(rng,scenario,p,n):
    T=p['geometry'][3];t=np.arange(T);d=len(p['powers'])
    amps=np.linspace(1,.2,d);ground=.8;excited=1.3
    contamination=np.zeros(d);contamination[1:3]=.5
    if scenario=='known_lower_excited_overlap':contamination[2]=.1
    if scenario=='window_mismatch':contamination[:]=3
    if scenario=='wrong_state':
        ground=1.5;excited=2.;contamination[1]=.5;contamination[2]=.1
    signal=amps[:,None]*(shape(ground,t,T)+contamination[:,None]*shape(excited,t,T))
    shared=rng.normal(size=(n,1,T));independent=rng.normal(size=(n,d,T))
    noise=2.5 if scenario=='relative_error' else .03
    raw=signal[None]*(1+noise*(shared+independent)/np.sqrt(2))
    if scenario=='reflection':raw[...,1:8]*=1.15
    if scenario=='nonfinite':raw[0,0,5]=np.nan
    return raw
