"""Single-variable D2 repair: an ImageNet-pretrained ResNet18 encoder.

The decoder is deliberately small.  Published-label evaluation, score definitions,
checkpoint selection, seed and optimizer contract are owned by ``d2_runner.py``.
"""
from pathlib import Path

import torch
from torch import nn
from torch.nn import functional as F
from torchvision.models import resnet18


IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)


class DecodeBlock(nn.Sequential):
    def __init__(self, in_channels: int, out_channels: int):
        super().__init__(
            nn.Conv2d(in_channels, out_channels, 3, padding=1, bias=False),
            nn.GroupNorm(8, out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, 3, padding=1, bias=False),
            nn.GroupNorm(8, out_channels),
            nn.ReLU(inplace=True),
        )


class ResNet18UNet(nn.Module):
    """ResNet18 encoder with native-resolution binary segmentation output."""

    def __init__(self, pretrained_weights: str | Path | None = None):
        super().__init__()
        encoder = resnet18(weights=None)
        if pretrained_weights is not None:
            state = torch.load(Path(pretrained_weights), map_location="cpu", weights_only=True)
            encoder.load_state_dict(state, strict=True)
        self.stem = nn.Sequential(encoder.conv1, encoder.bn1, encoder.relu)
        self.maxpool = encoder.maxpool
        self.layer1 = encoder.layer1
        self.layer2 = encoder.layer2
        self.layer3 = encoder.layer3
        self.layer4 = encoder.layer4
        self.dec3 = DecodeBlock(512 + 256, 256)
        self.dec2 = DecodeBlock(256 + 128, 128)
        self.dec1 = DecodeBlock(128 + 64, 64)
        self.dec0 = DecodeBlock(64 + 64, 64)
        self.full = DecodeBlock(64, 32)
        self.out = nn.Conv2d(32, 1, 1)
        self.register_buffer("image_mean", torch.tensor(IMAGENET_MEAN).view(1, 3, 1, 1))
        self.register_buffer("image_std", torch.tensor(IMAGENET_STD).view(1, 3, 1, 1))
        self._init_decoder()

    def _init_decoder(self):
        for module in [self.dec3, self.dec2, self.dec1, self.dec0, self.full, self.out]:
            for layer in module.modules():
                if isinstance(layer, nn.Conv2d):
                    nn.init.kaiming_normal_(layer.weight, mode="fan_in", nonlinearity="relu")
                elif isinstance(layer, nn.GroupNorm):
                    nn.init.ones_(layer.weight)
                    nn.init.zeros_(layer.bias)

    @staticmethod
    def _up(x, skip):
        return F.interpolate(x, size=skip.shape[-2:], mode="bilinear", align_corners=False)

    def forward(self, x, return_feature=False):
        output_size = x.shape[-2:]
        x = (x - self.image_mean) / self.image_std
        s0 = self.stem(x)
        s1 = self.layer1(self.maxpool(s0))
        s2 = self.layer2(s1)
        s3 = self.layer3(s2)
        x = self.layer4(s3)
        feature = x.mean((2, 3))
        x = self.dec3(torch.cat([self._up(x, s3), s3], 1))
        x = self.dec2(torch.cat([self._up(x, s2), s2], 1))
        x = self.dec1(torch.cat([self._up(x, s1), s1], 1))
        x = self.dec0(torch.cat([self._up(x, s0), s0], 1))
        x = self.full(F.interpolate(x, size=output_size, mode="bilinear", align_corners=False))
        logits = self.out(x)
        return (logits, feature) if return_feature else logits
