# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/02_Imputation.ipynb.

# %% auto 0
__all__ = ['GPFAFakeData']

# %% ../nbs/02_Imputation.ipynb 6
class GPFAFakeData:
    def __init__(self,
                    n_features: int,
                    n_obs: int,
                    latent_func = torch.sin, # Functions used to generate the true latent:
                    noise_std = .2
                ):
        
        self.n_features, self.n_obs = n_features, n_obs
        self.T = torch.arange(n_obs)
        
        self.latent = latent_func(self.T)
        
        self.Lambda = torch.rand(n_features, 1)
        
        self.exact_X = (self.Lambda * self.latent).T
        
        self.X =  self.exact_X + torch.normal(0., noise_std, size = (n_obs, n_features)) 
        