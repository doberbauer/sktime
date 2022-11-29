# -*- coding: utf-8 -*-
"""MiniRocket transformer."""

__author__ = "angus924"
__all__ = ["MiniRocket"]

import multiprocessing

import numpy as np
import pandas as pd

from sktime.transformations.base import BaseTransformer


class MiniRocket(BaseTransformer):
    """MINIROCKET.

    MINImally RandOm Convolutional KErnel Transform

    **Univariate** and **equal length**

    Unviariate input only.  Use class MiniRocketMultivariate for multivariate
    input, or MiniRocketMultivariate for unequal length time-series . [1]_


    Parameters
    ----------
    num_kernels              : int, (default=10,000)
                                number of random convolutional kernels
    max_dilations_per_kernel : int, (default=32)
                                maximum number of dilations per kernel
    n_jobs                   : int, (default=1)
                                The number of jobs to run in parallel
                                for `transform`. ``-1`` means using all processors.
    random_state             : int or None, (default=None)
                                random seed, not set by default

    References
    ----------
    .. [1] Angus Dempster, Daniel F Schmidt, Geoffrey I Webb
        MINIROCKET: A Very Fast (Almost) Deterministic Transform for
        Time Series Classification, 2020, arXiv:2012.08791

    See Also
    --------
    MultiRocket, MiniRocketMultivariate, MiniRocketMultivariateVariable, Rocket

    Examples
    --------
    >>> from sktime.transformations.panel.rocket import MiniRocket
    >>> from sktime.datasets import load_gunpoint
    >>> # load univariate dataset
    >>> X_train, _ = load_gunpoint(split="train", return_X_y=True)
    >>> X_test, _ = load_gunpoint(split="test", return_X_y=True)
    >>> pre_clf = MiniRocket()
    >>> pre_clf.fit(X_train, y=None)
    MiniRocket(...)
    >>> X_transformed = pre_clf.transform(X_test)
    >>> X_transformed.shape
    (150, 9996)
    """

    _tags = {
        "univariate-only": True,
        "fit_is_empty": False,
        "scitype:transform-input": "Series",
        # what is the scitype of X: Series, or Panel
        "scitype:transform-output": "Primitives",
        # what is the scitype of y: None (not needed), Primitives, Series, Panel
        "scitype:instancewise": False,  # is this an instance-wise transform?
        "X_inner_mtype": "numpy3D",  # which mtypes do _fit/_predict support for X?
        "y_inner_mtype": "None",  # which mtypes do _fit/_predict support for X?
        "python_dependencies": "numba",
    }

    def __init__(
        self,
        num_kernels=10_000,
        max_dilations_per_kernel=32,
        n_jobs=1,
        random_state=None,
    ):
        self.num_kernels = num_kernels
        self.max_dilations_per_kernel = max_dilations_per_kernel

        self.n_jobs = n_jobs
        self.random_state = random_state
        super(MiniRocket, self).__init__()

    def _fit(self, X, y=None):
        """Fits dilations and biases to input time series.

        Parameters
        ----------
        X : 3D np.ndarray of shape = [n_instances, n_dimensions, series_length]
            panel of time series to transform
        y : ignored argument for interface compatibility

        Returns
        -------
        self
        """
        from sktime.transformations.panel.rocket._minirocket_numba import _fit

        random_state = (
            np.int32(self.random_state) if isinstance(self.random_state, int) else None
        )

        X = X[:, 0, :].astype(np.float32)
        _, n_timepoints = X.shape
        if n_timepoints < 9:
            raise ValueError(
                (
                    f"n_timepoints must be >= 9, but found {n_timepoints};"
                    " zero pad shorter series so that n_timepoints == 9"
                )
            )
        self.parameters = _fit(
            X, self.num_kernels, self.max_dilations_per_kernel, random_state
        )
        return self

    def _transform(self, X, y=None):
        """Transform input time series.

        Parameters
        ----------
        X : 3D np.ndarray of shape = [n_instances, n_dimensions, series_length]
            panel of time series to transform
        y : ignored argument for interface compatibility

        Returns
        -------
        pandas DataFrame, transformed features
        """
        from numba import get_num_threads, set_num_threads

        from sktime.transformations.panel.rocket._minirocket_numba import _transform

        X = X[:, 0, :].astype(np.float32)

        # change n_jobs dependend on value and existing cores
        prev_threads = get_num_threads()
        if self.n_jobs < 1 or self.n_jobs > multiprocessing.cpu_count():
            n_jobs = multiprocessing.cpu_count()
        else:
            n_jobs = self.n_jobs
        set_num_threads(n_jobs)
        X_ = _transform(X, self.parameters)
        set_num_threads(prev_threads)
        return pd.DataFrame(X_)
