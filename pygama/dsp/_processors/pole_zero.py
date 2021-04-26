import numpy as np
from numba import guvectorize


@guvectorize(["void(float32[:], float32, float32[:])",
              "void(float64[:], float64, float64[:])"],
             "(n),()->(n)", nopython=True, cache=True)


def pole_zero(w_in, t_tau, w_out):
    
    """
    Applies a Pole-zero correction using time constant tau

    Parameters
    ----------

    w_in : array-like
            waveform to apply pole zero correction to. Needs to be baseline subtracted
    
    t_tau : float
            Time constant of exponential decay to be deconvolved
    
    w_out : array-like
            Output array for pole zero corrected waveform 
    """


    w_out[:] = np.nan 

    if (np.isnan(w_in).any() or t_tau == np.nan):
        return

    if (not t_tau >= 0):
        raise DSPError('t_tau is out of range')


    const = np.exp(-1/tau)
    w_out[0] = w_in[0]
    for i in range(1, len(wf_in)):
        w_out[i] = w_out[i-1] + w_in[i] - w_in[i-1]*const





@guvectorize(["void(float32[:], float32, float32, float32, float32[:])",
              "void(float64[:], float64, float64, float64, float64[:])"],
             "(n),(),(),()->(n)", nopython=True, cache=True)

def double_pole_zero(w_in, t_tau1, t_tau2, frac, w_out):
    """
    Pole-zero correction using two time constants: one main (long) time constant
    tau1, and a shorter time constant tau2 that contributes a fraction frac

    Parameters
    ----------

    w_in : array-like
            waveform to apply pole zero correction to. Needs to be baseline subtracted
    
    t_tau1 : float
            Time constant of first exponential decay to be deconvolved

    t_tau2 : float
            Time constant of second exponential decay to be deconvolved

    frac : float
            Fraction which tau2 contributes to decay
    
    w_out : array-like
            Output array for pole zero corrected waveform 
    """
    
    w_out[:] = np.nan 

    if (np.isnan(w_in).any() or t_tau1 == np.nan or t_tau1 == np.nan or frac == np.nan):
        return

    if (not t_tau1 >= 0):
        raise DSPError('t_tau1 is out of range')
    if (not t_tau2 >= 0):
        raise DSPError('t_tau2 is out of range')
    if (not frac >= 0):
        raise DSPError('frac is out of range')

    const1 = 1/tau1 #np.exp(-1/tau1)
    const2 = 1/tau2 #np.exp(-1/tau2)
    wf_out[0] = wf_in[0]
    e1 = wf_in[0]
    e2 = wf_in[0]
    e3 = 0
    for i in range(1, len(wf_in)):
        e1 += wf_in[i] - e2 + e2*const1
        e3 += wf_in[i] - e2 - e3*const2
        e2 = wf_in[i]
        wf_out[i] = e1 - frac*e3
