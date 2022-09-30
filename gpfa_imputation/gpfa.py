# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/00_GPFA.ipynb.

# %% auto 0
__all__ = ['GPFAKernel', 'compute_gpfa_covariance', 'GPFAZeroMean', 'GPFA']

# %% ../nbs/00_GPFA.ipynb 12
import torch
import gpytorch

# %% ../nbs/00_GPFA.ipynb 14
class GPFAKernel(gpytorch.kernels.Kernel):
    """
    Kernel to implement Gaussian Processes Factor Analysis
    """
    def __init__(self, n_features: int, latent_kernel: gpytorch.kernels.Kernel, latent_dims = 1, Lambda: torch.tensor = None, psi: torch.tensor = None, **kwargs):
        """
        :n_features: number of variables at each time step
        :latent_kernel: any valid GPyTorch Kernel used to model the relationship over time of the latent
        :latent_dims: Number of latent dims, for now only 1 supported
        :Lambda: (n_features * latent_dims) initial value for factor loading matrix
        :psi: (n_features) initial value for random noise covariance. Note this is only the diagonal matrix
        """
        super(GPFAKernel, self).__init__(**kwargs)
        
        # Number of features in the X for each time step
        self.n_features = n_features
        assert latent_dims == 1 # Not implemented yet
        self.latent_dims = latent_dims
        
        # see GPyTorch Kernels
        self.register_parameter(
            name = "Lambda",
            parameter = torch.nn.Parameter(torch.ones(self.n_features, self.latent_dims)))
        
        self.latent_kernel = latent_kernel
        
        self.register_parameter(
            name = "raw_psi_diag",
            parameter = torch.nn.Parameter(torch.zeros(self.n_features))) 
        self.register_constraint("raw_psi_diag", gpytorch.constraints.Positive())
        if psi is not None: self.psi = psi
    
    # Convenient getter and setter for psi, since there is the Positive() constraint
    @property
    def psi(self):
        # when accessing the parameter, apply the constraint transform
        return self.raw_psi_diag_constraint.transform(self.raw_psi_diag)

    @psi.setter
    def psi(self, value):
        return self._set_psi(value)

    def _set_psi(self, value):
        if not torch.is_tensor(value):
            value = torch.as_tensor(value).to(self.raw_psi_diag)
        # when setting the paramater, transform the actual value to a raw one by applying the inverse transform
        self.initialize(raw_psi_diag=self.raw_psi_diag_constraint.inverse_transform(value))
    

        
    # perform the actual calculation
    def forward(self, t1, t2, diag = False, last_dim_is_batch=False, **params):

        # not implemented yet
        assert diag is False
        assert last_dim_is_batch is False

        # take the number of observations from the input
        n_obs = t1.shape[0]

        # compute the latent kernel
        kT = self.latent_kernel(t1, t2, diag, last_dim_is_batch, **params).evaluate() # this may make the whole thing slow
       
        return compute_gpfa_covariance(self.Lambda, kT, self.psi, self.n_features, n_obs)
    
    def num_outputs_per_input(self, x1,x2):
        return self.n_features

# this is a separate function, because torch script cannot take self as a parameter
@torch.jit.script
def compute_gpfa_covariance(Lambda, kT, psi, n_features, n_obs):
    # pre allocate covariance matrix
    X_cov = torch.empty(n_features * n_obs, n_features * n_obs)
    for i in torch.arange(n_obs):
        for j in torch.arange(n_obs):
            # i:i+1 is required to keep the number of dimensions
            cov =  Lambda @ kT[i:i+1,j:j+1] @ Lambda.T
            # only diagonals add the noise
            if i == j: cov += torch.diag(psi)
            # add a block of size n_features*n_features to the covariance matrix
            X_cov[i*n_features:(i*n_features + n_features),j*n_features:(j*n_features+n_features)] = cov
    return X_cov

# %% ../nbs/00_GPFA.ipynb 21
class GPFAZeroMean(gpytorch.means.Mean):
    """
    Zero Mean function to be used in GPFA, as it takes into account the number of features
    """
    def __init__(self, n_features):
        super().__init__()
        self.n_features = n_features
    def forward(self, input):
        shape = input.shape[0] * self.n_features
        return torch.zeros(shape)

# %% ../nbs/00_GPFA.ipynb 22
class GPFA(gpytorch.models.ExactGP):
    def __init__(self, train_x, train_y, likelihood, n_features, latent_kernel):
        super(GPFA, self).__init__(train_x, train_y, likelihood)
        self.mean_module = GPFAZeroMean(n_features)
        self.covar_module = GPFAKernel(n_features, latent_kernel)

    def forward(self, x, **params):
        mean_x = self.mean_module(x)
        covar_x = self.covar_module(x, **params)
        return gpytorch.distributions.MultivariateNormal(mean_x, covar_x)
