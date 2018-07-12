import torch
import torch.nn as nn

from integrate import odeint_adjoint as odeint

__all__ = ["CNF"]


class CNF(nn.Module):
    def __init__(self, odefunc, T):
        super(CNF, self).__init__()
        self.odefunc = odefunc
        self.time_range = torch.tensor([0., float(T)])
        self.odefunc._num_evals = 0

    def forward(self, z, logpz=None, integration_times=None, reverse=False, full_output=False):
        if logpz is None:
            _logpz = torch.zeros(z.shape[0], 1).to(z)
        else:
            _logpz = logpz

        orig_shape = z.shape
        inputs = torch.cat([z.view(z.shape[0], -1), _logpz.view(-1, 1)], 1)

        if integration_times is None:
            integration_times = self.time_range
        if reverse:
            integration_times = _flip(integration_times, 0)

        # fix noise throughout integration and reset counter to 0
        self.odefunc._e = torch.randn(z.shape).to(z.device)
        self.odefunc._num_evals = 0
        outputs = odeint(self.odefunc, inputs, integration_times.to(inputs), atol=1e-6, rtol=1e-5)
        z_t, logpz_t = outputs[:, :, :-1], outputs[:, :, -1:]
        z_t = z_t.view(-1, *orig_shape)

        if len(integration_times) == 2:
            z_t, logpz_t = z_t[1], logpz_t[1]

        if logpz is not None:
            return z_t, logpz_t
        else:
            return z_t

    def num_evals(self):
        return self.odefunc._num_evals


def _flip(x, dim):
    indices = [slice(None)] * x.dim()
    indices[dim] = torch.arange(x.size(dim) - 1, -1, -1, dtype=torch.long, device=x.device)
    return x[tuple(indices)]