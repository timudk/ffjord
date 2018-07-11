import os
import logging
import torch
import torch.functional as F
import numpy as np


def makedirs(dirname):
    if not os.path.exists(dirname):
        os.makedirs(dirname)



class Preprocess(object):
    """
    Preprocesses a tensor defined on compact input [0, 1.]
    Adds uniform noise and scales back to [0., 1.)

    Args:
        num_bits (int): number of bits to use, min = 1, max = 8
    """

    def __init__(self, alpha=.05, reverse=False):
        self.reverse = reverse
        self.alpha = alpha

    def forward(self, x, logdet=False):
        s = self.alpha + (1 - 2 * self.alpha) * x
        y = torch.log(s) - torch.log(1 - s)
        if logdet:
            return y, -self._logdetgrad(x).view(x.size(0), -1).sum(1, keepdim=True)
        else:
            return y

    def backward(self, y, logdet=False):
        x = (torch.sigmoid(y) - self.alpha) / (1 - 2 * self.alpha)
        if logdet:
            return x, self._logdetgrad(x).view(x.size(0), -1).sum(1, keepdim=True)
        else:
            return x

    def _logdetgrad(self, x):
        s = self.alpha + (1 - 2 * self.alpha) * x
        logdetgrad = -torch.log(s - s * s) + np.log(1 - 2 * self.alpha)
        return logdetgrad

    def add_noise(self, x):
        noise = x.new().resize_as_(x).uniform_()
        x = x * 255 + noise
        x = x / 256
        return x

    def __repr__(self):
        return self.__class__.__name__ + '(backward={}, alpha={})'.format(self.reverse, self.alpha)


def get_logger(logpath, filepath, package_files=[],
               displaying=True, saving=True, debug=False):
    logger = logging.getLogger()
    if debug:
        level = logging.DEBUG
    else:
        level = logging.INFO
    logger.setLevel(level)
    if saving:
        info_file_handler = logging.FileHandler(logpath, mode='w')
        info_file_handler.setLevel(level)
        logger.addHandler(info_file_handler)
    if displaying:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        logger.addHandler(console_handler)
    logger.info(filepath)
    with open(filepath, 'r') as f:
        logger.info(f.read())

    for f in package_files:
        logger.info(f)
        with open(f, 'r') as package_f:
            logger.info(package_f.read())

    return logger


class AverageMeter(object):
    """Computes and stores the average and current value"""
    def __init__(self):
        self.reset()

    def reset(self):
        self.val = 0
        self.avg = 0
        self.sum = 0
        self.count = 0

    def update(self, val, n=1):
        self.val = val
        self.sum += val * n
        self.count += n
        self.avg = self.sum / self.count


class RunningAverageMeter(object):
    """Computes and stores the average and current value"""

    def __init__(self, momentum=0.99):
        self.momentum = momentum
        self.reset()

    def reset(self):
        self.val = None
        self.avg = 0

    def update(self, val):
        if self.val is None:
            self.avg = val
        else:
            self.avg = self.avg * self.momentum + val * (1 - self.momentum)
        self.val = val


def inf_generator(iterable):
    """Allows training with DataLoaders in a single infinite loop:
        for i, (x, y) in enumerate(inf_generator(train_loader)):
    """
    iterator = iterable.__iter__()
    while True:
        try:
            yield iterator.__next__()
        except StopIteration:
            iterator = iterable.__iter__()