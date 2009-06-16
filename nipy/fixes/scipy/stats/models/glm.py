"""
General linear models
--------------------

"""

import numpy as np
from nipy.fixes.scipy.stats.models import family
from nipy.fixes.scipy.stats.models.regression import WLSModel

# Note: STATA uses either iterated reweighted least squares optimization
#       of the deviation
# or the default mle using Newton-Raphson

# Note: only these combos make sense for family and link
#              + ident log logit probit cloglog pow opow nbinom loglog logc
# Gaussian     |   x    x                        x
# inv Gaussian |   x    x                        x
# binomial     |   x    x    x     x       x     x    x           x      x
# Poission     |   x    x                        x
# neg binomial |   x    x                        x          x
# gamma        |   x    x                        x
#
#


# Would GLM or GeneralLinearModel be a better class name?
class Model(WLSModel):

    niter = 10

    def __init__(self, design, hascons=True, family=family.Gaussian()):
        self.family = family
        self.hascons = hascons
        super(Model, self).__init__(design, hascons, weights=1)

    def __iter__(self):
        self.iter = 0
        self.dev = np.inf
        return self

    def deviance(self, Y=None, results=None, scale = 1.):
        """
        Return (unnormalized) log-likelihood for GLM.

        Note that self.scale is interpreted as a variance in old_model, so
        we divide the residuals by its sqrt.
        """
        if results is None:
            results = self.results
        if Y is None:
            Y = self.Y
        return self.family.deviance(Y, results.mu) / scale

    def next(self):
        results = self.results
        Y = self.Y
        self.weights = self.family.weights(results.mu)
        self.initialize(self.design, self.hascons)
        Z = results.predict + self.family.link.deriv(results.mu) * (Y - results.mu)
        # TODO: this had to changed to execute properly
        # is this correct? Why? I don't understand super.... -- JT

        newresults = super(Model, self).fit(Z)
        newresults.Y = Y
        newresults.mu = self.family.link.inverse(newresults.predict)
        self.iter += 1
        return newresults

    def cont(self, tol=1.0e-05):
        """
        Continue iterating, or has convergence been obtained?
        """
        if self.iter >= Model.niter:
            return False

        curdev = self.deviance(results=self.results)

        if np.fabs((self.dev - curdev) / curdev) < tol:
            return False

        self.dev = curdev
        return True

    def estimate_scale(self, Y=None, results=None):
        """
        Return Pearson\'s X^2 estimate of scale.
        """

        if results is None:
            results = self.results
        if Y is None:
            Y = self.Y
        resid = Y - results.mu
        return ((np.power(resid, 2) / self.family.variance(results.mu)).sum()
                / results.df_resid)

    def fit(self, Y):
        self.Y = np.asarray(Y, np.float64)
        iter(self)
        self.results = super(Model, self).fit(
            self.family.link.initialize(Y))
        self.results.mu = self.family.link.inverse(self.results.predict)
        self.scale = self.results.scale = self.estimate_scale()

        while self.cont():
            self.results = self.next()
            self.scale = self.results.scale = self.estimate_scale()

        return self.results