from pygama.io.raw_to_dsp import build_processing_chain
import pygama.io.lh5 as lh5
import pygama.dsp.units as units

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

class WaveformBrowser:
    """
    The Waveform Browser is a tool meant for interacting with waveforms from
    LH5 files. This defines an interface for drawing waveforms from a file,
    drawing transformed waveforms defined using raw_to_dsp style json files,
    drawing horizontal and verticle lines at the values of calculated
    parameters, and filling a legend with calculated parameters.
    """

    def __init__(self, file_in, lh5_group, dsp_config = None,
                 n_drawn = 1, x_unit = 'ns', x_lim=None,
                 waveforms = 'waveform', lines = None,
                 legend = None, norm = None, align=None,
                 selection = None, buffer_len = 128, block_width = 8):
        """Constructor for WaveformBrowser:
        - file_in: name of LH5 file to browse
        - lh5_group: name of LH5 group in file to browse
        - dsp_config (optional): name of DSP config json file containing transforms available to draw
        - n_drawn (default 1): number of events to draw simultaneously when calling DrawNext
        - x_unit (default ns): unit for x-axis
        - x_lim (default auto): range of x-values passes as tuple
        - waveforms (default 'waveform'): name of wf or list of wf names to draw
        - lines (default None): name of parameter or list of parameters to draw hlines and vlines for
        - legend (default None): name of parameters to include in legend
        - norm (default None): name of parameter (probably energy) to use to normalize WFs; useful when drawing multiple
        - align (default None): name of time parameter to set as 0 time; useful for aligning multiple waveforms
        - selection (optional): selection of events to draw. Can be either a list of event indices or a numpy array mask (ala pandas).
        - buffer_len (default 128): number of waveforms to keep in memory at a time
        - block_width (default 8): block width for processing chain
        """
        # data i/o initialization
        self.lh5_st = lh5.Store(keep_open=True)
        self.lh5_file = file_in
        self.lh5_group = lh5_group
        #self.buffer_len = buffer_len
        #self.lh5_in, n_rows_read = self.lh5_st.read_object(self.lh5_group, self.lh5_file, 0, self.buffer_len)
        # When chunked reading is ready use the previous two uncommented lines
        self.lh5_in, n_rows_read = self.lh5_st.read_object(self.lh5_group, self.lh5_file)
        self.buffer_len = len(self.lh5_in)

        # initialize stuff for iteration
        self.selection = selection
        self.index_it = None
        self.reset()
        self.n_wfs = n_drawn

        # initialize list of objects to draw
        if isinstance(waveforms, str): self.waveforms = [waveforms]
        elif waveforms is None: self.waveforms = []
        else: self.waveforms = list(waveforms)
        
        if isinstance(lines, str): self.lines = [lines]
        elif lines is None: self.lines = []
        else: self.lines = list(lines)
        
        if isinstance(legend, str): self.legend = [legend]
        elif legend is None: self.legend = []
        else: self.legend = list(legend)
        self.labels = []

        self.norm_par = norm
        self.align_par = align

        self.x_unit = units.unit_parser.parse_unit(x_unit)
        self.x_lim = x_lim

        # make processing chain and output buffer
        outputs = self.waveforms + self.lines + self.legend + ([self.norm_par] if self.norm_par is not None else []) + ([self.align_par] if self.align_par is not None else [])
        self.proc_chain, self.lh5_out = build_processing_chain(self.lh5_in, dsp_config, outputs, verbosity=1, block_width=block_width)
        self.current_chunk = None
        
        self.fig = None
        self.ax = None        
    
    def new_figure(self):
        """Create a new figure and draw in it"""
        self.fig, self.ax = plt.subplots(1)
    
    def draw_entry(self, entry, append=False):
        """Draw specified entry from file. If append is True, previously drawn entries will not be cleared from the current axis. Return the axis object"""
        # Make figure/axis if needed
        if not (self.ax and self.fig and plt.fignum_exists(self.fig.number)):
            self.new_figure()
        
        # Update the chunk as needed
        if entry//self.buffer_len != self.current_chunk:
            self.current_chunk = entry//self.buffer_len
            self.lh5_st.read_object(self.lh5_group, self.lh5_file, start_row = self.current_chunk*self.buffer_len, obj_buf = self.lh5_in)
            self.proc_chain.execute()
            
        # get index within this chunk
        index = entry%self.buffer_len

        # get scaling factor/time shift if used
        norm = self.lh5_out[self.norm_par].nda[index] if self.norm_par is not None else 1.
        if self.align_par is not None:
            unit = self.lh5_out[self.align_par].attrs['units']
            dt = units.convert(1, units.unit_parser.parse_unit(unit), self.x_unit)
            ref_time = self.lh5_out[self.align_par].nda[index]*dt
        else:
            ref_time = 0
        leg_handle = None
        
        # now draw all the objects
        if not append:
            self.ax.clear()
            self.labels = []
            
        self.ax.set_xlabel('Time ('+str(self.x_unit)+')')
        if self.x_lim:
            self.ax.set_xlim(*self.x_lim)

        #waveforms
        for wf_name in self.waveforms:
            y = self.lh5_out[wf_name].nda[index]/norm
            dt = units.convert(1, self.proc_chain._clk, self.x_unit)
            x = np.linspace(-ref_time, len(y)*dt-ref_time, len(y), 'f')
            wf_line, = self.ax.plot(x, y, '-')
            if leg_handle is None:
                leg_handle = wf_line
        
        # lines
        for par_name in self.lines:
            unit = self.lh5_out[par_name].attrs['units']
            try: # if unit is time, do vline
                dt = units.convert(1, units.unit_parser.parse_unit(unit), self.x_unit)
                x = self.lh5_out[par_name].nda[index]*dt - ref_time
                self.ax.axvline(x)
                
            except units.InvalidConversion: # else do hline
                dt = None
                y = self.lh5_out[par_name].nda[index]/norm
                self.ax.axhline(y)

        # legend label
        if len(self.legend)>0:
            legend_str = ''
            for par_name in self.legend:
                if legend_str!='':
                    legend_str += ', '
                legend_str += "{} = {:.4g} {}".format(par_name, self.lh5_out[par_name].nda[index], self.lh5_out[par_name].attrs['units'])

            if self.ax.legend_:
                handles = self.ax.legend_.legendHandles
                labels = [t.get_text() for t in self.ax.legend_.texts]
            else:
                handles = []
                labels = []
            handles.append(leg_handle)
            labels.append(legend_str)
            self.ax.legend(handles, labels, loc='upper left')

        self.fig.canvas.draw()
        return self.ax

    def draw_next(self, n_wfs = None):
        """Draw the next n_wfs waveforms on the same axis. If a selection was set, only draw waveforms from that selection. Return a list of waveform indices drawn and the axis object"""
        # reset the axis
        if self.ax is not None:
            self.ax.clear()
        self.labels = []
        if not n_wfs: n_wfs = self.n_wfs

        wf_indices = []
        
        # Draw wfs
        for _ in range(0, n_wfs):
            i_wf = next(self.index_it)
            wf_indices.append(i_wf)
            try:
                self.draw_entry(i_wf, True)
            except StopIteration:
                self.eof = True
                break
        
        return wf_indices
            
    def reset(self):
        """ Reset to the start of the file for draw_next """
        self.eof = False
        try:
            if self.selection is None:
                self.index_it = iter(range(0, len(self.lh5_in)))
            elif isinstance(self.selection, list) or isinstance(self.selection, tuple): # index list
                self.index_it = iter(self.selection)
            elif isinstance(self.selection, np.ndarray): # numpy boolean mask
                self.index_it = iter(np.nonzero(self.selection)[0] )
            elif isinstance(self.selection, pd.Series): # pandas series mask
                self.index_it = iter(np.nonzero(self.selection.values)[0] )
            else:
                raise Exception
        except:
            print("Not sure what to do with selection", self.selection)
        
    def __iter__(self):
        self.reset()
        return self
    
    def __next__(self):
        """ Call draw_next... """
        if self.eof:
            raise StopIteration
        return self.draw_next()