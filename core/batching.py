"""CPU-backed mini-batch helpers for recurrent-model training."""

import numpy as np
import torch
from torch.utils.data import DataLoader, TensorDataset

from core.cancellation import check_cancelled


DEFAULT_BATCH_SIZE = 64


def make_tensor_loader(features, targets, *, batch_size=DEFAULT_BATCH_SIZE,
                       shuffle=False, seed=0):
    if batch_size < 1:
        raise ValueError('批次大小必须大于 0')
    features = np.asarray(features, dtype=np.float32)
    targets = np.asarray(targets, dtype=np.float32)
    if len(features) != len(targets):
        raise ValueError('特征和标签数量必须一致')
    dataset = TensorDataset(
        torch.from_numpy(features), torch.from_numpy(targets))
    generator = torch.Generator()
    generator.manual_seed(int(seed))
    return DataLoader(
        dataset,
        batch_size=min(batch_size, max(1, len(dataset))),
        shuffle=shuffle,
        generator=generator,
        num_workers=0,
        pin_memory=False,
    )


def train_recurrent_epoch(model, loader, optimizer, criterion, device,
                          stop_flag=None):
    model.train()
    weighted_loss = 0.0
    sample_count = 0
    for features, targets in loader:
        check_cancelled(stop_flag)
        features = features.to(device)
        targets = targets.to(device)
        output = model(features).reshape(-1, 1)
        loss = criterion(output, targets.reshape(-1, 1))
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        count = len(features)
        weighted_loss += float(loss.item()) * count
        sample_count += count
    return weighted_loss / max(1, sample_count)


def evaluate_recurrent_loss(model, loader, criterion, device,
                            stop_flag=None):
    model.eval()
    weighted_loss = 0.0
    sample_count = 0
    with torch.no_grad():
        for features, targets in loader:
            check_cancelled(stop_flag)
            features = features.to(device)
            targets = targets.to(device)
            output = model(features).reshape(-1, 1)
            loss = criterion(output, targets.reshape(-1, 1))
            count = len(features)
            weighted_loss += float(loss.item()) * count
            sample_count += count
    return weighted_loss / max(1, sample_count)
