"""Real time R_eff estimation Daniele Proverbio - LCSB - 2020-05-09.

The basic reproduction number R_0 quantifies the potential strength of an epidemic outbreak, at the
very beginning of a pandemic. During the epidemic evolution, we can further estimate the
time-dependent effective reproduction number R_t, to have a quantitative probe of its severity. This
is also useful for cross-country comparison. The algorithm we use is based on Kevin Systrom's: git
and website - April 2020. It is consistent with the one from Mathematical Modelling of Infectious
Disases, London School of Hygiene and Tropical Medicine (link). Here, we adapted it for Luxembourg,
with updated stream flow for estimation and plotting. Given the latest literature, serial interval
for COVID-19 is about 4 days.

Note: during COVID-19 pandemics, there is a delay from infection to detection during to latency,
sampling times and so on. Hence, it is necessary to refer all data to their true infection time.
Here, we assume constant shift. By comparison with more advanced nowcasting procedures (e.g. RKI's),
we estimated such shift to be equal 8±1 days. Hence, be aware that we are looking at the past. This
is considered in plots below."""

import os
import os.path
import csv

import pandas as pd
import numpy as np
import datetime as DT

from abmlux.reporters import Reporter
from matplotlib import pyplot as plt
#plt.rc('font',**{'family':'sans-serif','sans-serif':['Helvetica']})
#plt.rc('text', usetex=True)
from matplotlib.dates import date2num, num2date
from matplotlib import dates as mdates
from matplotlib import ticker
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch

from scipy import stats as sps
from scipy.interpolate import interp1d

from IPython.display import clear_output

from abmlux.reporters import Reporter

class EffectiveReproductionNumber(Reporter):
    """Reporter that writes to a CSV file as it runs."""

    def __init__(self, host, port, config):
        super().__init__(host, port)

        self.cum_positive_tests = 0

        self.filename_rescaled_cum_counts = config['filename_rescaled_cum_counts']
        self.filename_rt_estimate = config['filename_rt_estimate']
        self.state = config['state']

        self.subscribe("simulation.start", self.start_sim)
        self.subscribe("notify.testing.result", self.new_test_result)
        self.subscribe("notify.time.midnight", self.midnight_reset)
        self.subscribe("simulation.end", self.stop_sim)

    def start_sim(self, scale_factor):
        """Called when the simulation starts.  Writes headers and creates the file handle."""

        self.scale_factor = scale_factor

        # TODO: handle >1 sim at the same time using the run_id
        # Check dir exists and open handle
        dirname = os.path.dirname(self.filename_rescaled_cum_counts)
        os.makedirs(dirname, exist_ok=True)
        self.handle = open(self.filename_rescaled_cum_counts, 'w')
        self.writer = csv.writer(self.handle)
        
        # Write header
        header = ["date", "state", "positive"]

        self.writer.writerow(header)

    def midnight_reset(self, clock, t):
        """Save data and reset daily counts"""

        row = [clock.now().strftime("%Y%m%d"), self.state, int(self.cum_positive_tests * (1 / self.scale_factor))]
        self.writer.writerow(row)

    def new_test_result(self, clock, test_result, age, uuid, coord, resident):
        """Update the CSV, writing a single row for every clock tick"""
        #if self.writer is None or self.handle is None:
        #    raise AttributeError("Call to iterate before call to start()")

        if test_result:
            self.cum_positive_tests += 1

    def stop_sim(self):
        """Called when the simulation ends.  Closes the file handle."""
        if self.handle is not None:
            self.handle.close()

        state_name = self.state

        # prepare data, to get daily cases and smoothing
        def prepare_cases(cases, cutoff=25):
            new_cases = cases.diff()

            smoothed = new_cases.rolling(7,    #7 days moving window for smoothing
                #win_type='gaussian',   #or comment whole line to have uniform
                min_periods=1,
                center=False).mean().round()
            
            idx_start =22 #np.searchsorted(smoothed, cutoff) #Better to fix it to prevent mismatches when numbers get very low
            
            smoothed = smoothed.iloc[idx_start:]
            original = new_cases.loc[smoothed.index]

            return original, smoothed

        # getting highest density intervals
        def highest_density_interval(pmf, p=.9, debug=False):
            # If we pass a DataFrame, just call this recursively on the columns
            if(isinstance(pmf, pd.DataFrame)):
                return pd.DataFrame([highest_density_interval(pmf[col], p=p) for col in pmf],
                                    index=pmf.columns)
            
            cumsum = np.cumsum(pmf.values)
            
            # N x N matrix of total probability mass for each low, high
            total_p = cumsum - cumsum[:, None]
            
            # Return all indices with total_p > p
            lows, highs = (total_p > p).nonzero()

            print(lows)
            print(highs)
            
            # Find the smallest range (highest density)
            best = (highs - lows).argmin()
            
            low = pmf.index[lows[best]]
            high = pmf.index[highs[best]]
            
            return pd.Series([low, high],
                            index=[f'Low_{p*100:.0f}',
                                    f'High_{p*100:.0f}'])

        # getting posteriors for R_t evaluation
        def get_posteriors(sr, date, sigma=0.15):

            # (1) Calculate Lambda
            gamma=1/np.random.normal(4, 0.2, len(r_t_range))
            lam = sr[:-1] * np.exp(gamma[:, None] * (r_t_range[:, None] - 1))
            #lam = sr[:-1].values * np.exp(GAMMA * (r_t_range[:, None] - 1))

            
            # (2) Calculate each day's likelihood
            likelihoods = pd.DataFrame(
                data = sps.poisson.pmf(sr[1:], lam),
                index = r_t_range,
                columns = date[1:])
            
            # (3) Create the Gaussian Matrix
            process_matrix = sps.norm(loc=r_t_range,
                                    scale=sigma
                                    ).pdf(r_t_range[:, None]) 

            # (3a) Normalize all rows to sum to 1
            process_matrix /= process_matrix.sum(axis=0)
            
            # (4) Calculate the initial prior
            #prior0 = sps.gamma(a=4).pdf(r_t_range)
            prior0 = np.ones_like(r_t_range)/len(r_t_range)
            prior0 /= prior0.sum()

            # Create a DataFrame that will hold our posteriors for each day
            # Insert our prior as the first posterior.
            posteriors = pd.DataFrame(
                index=r_t_range,
                columns=date,
                data={date[0]: prior0}
            )
            
            # We said we'd keep track of the sum of the log of the probability
            # of the data for maximum likelihood calculation.
            log_likelihood = 0.0

            # (5) Iteratively apply Bayes' rule
            for previous_day, current_day in zip(date[:-1], date[1:]):

                #(5a) Calculate the new prior
                current_prior = process_matrix @ posteriors[previous_day]
                
                #(5b) Calculate the numerator of Bayes' Rule: P(k|R_t)P(R_t)
                numerator = likelihoods[current_day] * current_prior
                
                #(5c) Calcluate the denominator of Bayes' Rule P(k)
                denominator = np.sum(numerator)
                
                # Execute full Bayes' Rule
                posteriors[current_day] = numerator/denominator
                
                # Add to the running sum of log likelihoods
                log_likelihood += np.log(denominator)
            
            return posteriors, log_likelihood

        #load data

        path = self.filename_rescaled_cum_counts
        states = pd.read_csv(path,
                            usecols=['date', 'state', 'positive'],
                            parse_dates=['date'],
                            index_col=['state', 'date'],
                            squeeze=True).sort_index()

        # Prepare data for analysis

        cases = states.xs(state_name).rename(f"{state_name} cases")
        original, smoothed = prepare_cases(cases)

        #convert into array for easier handling
        original_array = original.values
        smoothed_array = smoothed.values

        # dates: what we have in real time are detected of cases, but they refer to infection happened several days ago
        # comparing with Nowcasting procedures, this latancy is 8±1 days
        dates = smoothed.index
        dates_detection = date2num(smoothed.index.tolist())
        dates_infection = smoothed.index - DT.timedelta(days=9)
        dates_infection = date2num(dates_infection.tolist())

        #estimate R_t (for detection) and print 

        R_T_MAX = 10
        r_t_range = np.linspace(0, R_T_MAX, R_T_MAX*100+1)

        print(smoothed_array, dates)

        posteriors, log_likelihood = get_posteriors(smoothed_array, dates, sigma=.15)    #optimal sigma already chosen in original Notebook

        print(posteriors)

        # Note that this is not the most efficient algorithm, but works fine
        hdis = highest_density_interval(posteriors, p=.5)          # confidence bounds, p=50%

        most_likely = posteriors.idxmax().rename('R_t-estimate')   #mean R_t value

        result = pd.concat([most_likely, hdis], axis=1)            #global result for R_t-estimate
        # print(result.tail())

        result.to_csv(self.filename_rt_estimate)