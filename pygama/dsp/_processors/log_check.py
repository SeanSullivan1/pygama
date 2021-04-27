import numpy as np
from numba import guvectorize



@guvectorize(["void(float32[:], float32[:])",
              "void(float64[:], float64[:])"],
             "(n)->(n)", nopython=True, cache=True)


def log_check(w_in, w_log):


    '''
    This processor takes in a waveform slice and outputs its logarithm if all the values are positive otherwise returns nan.
    Typically used to log the decay tail before applying a linear fit to find the pole zero constant.

    Parameters
    ----------
    w_in : array-like
           input waveform slice or whole waveform
    
    w_log : array-like
            the output of the processor the logged waveform

    '''
    
    
    w_log[:] = np.nan
    
    if np.any(w_in<0) == True:
        return
        
    w_log[:] = np.log(w_in[:])
