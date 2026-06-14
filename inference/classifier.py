import numpy as np
import os

try:
    import cv2
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
except ImportError:
    cv2 = None
    torch = None
    nn = None
    F = None


class BaseClassifier:
    def predict_fake_probability(self, face_image):
        raise NotImplementedError


class HeuristicClassifier(BaseClassifier):
    """Deterministic placeholder until the Xception weights are supplied."""

    def predict_fake_probability(self, face_image):
        image = face_image.astype(np.float32) / 255.0
        contrast = float(image.std())
        brightness = float(image.mean())
        score = 0.35 + (contrast * 0.8) + (abs(brightness - 0.5) * 0.25)
        return max(0.0, min(1.0, score))


def build_classifier(model_path=None):
    if model_path and os.path.exists(model_path):
        return XceptionClassifier(model_path)
    return HeuristicClassifier()


class XceptionClassifier(BaseClassifier):
    def __init__(self, weights_path, device=None):
        if not os.path.exists(weights_path):
            raise FileNotFoundError(f"Model weights not found: {weights_path}")
        if torch is None or cv2 is None:
            raise RuntimeError("PyTorch and OpenCV are required to load Xception weights")

        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        self.model = Xception(num_classes=2)
        state = torch.load(weights_path, map_location=self.device)
        if isinstance(state, dict) and "state_dict" in state:
            state = state["state_dict"]
        elif isinstance(state, dict) and "model_state_dict" in state:
            state = state["model_state_dict"]
        state = {key.replace("module.", "", 1): value for key, value in state.items()}
        self.model.load_state_dict(state)
        self.model.to(self.device)
        self.model.eval()

    def predict_fake_probability(self, face_image):
        image = cv2.resize(face_image, (299, 299), interpolation=cv2.INTER_AREA)
        image = image.astype(np.float32) / 255.0
        image = (image - 0.5) / 0.5
        tensor = torch.from_numpy(image.transpose(2, 0, 1)).unsqueeze(0).float().to(self.device)
        with torch.no_grad():
            logits = self.model(tensor)
            probabilities = torch.softmax(logits, dim=1)
        return float(probabilities[0, 1].detach().cpu().item())


class SeparableConv2d(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size=1, stride=1, padding=0, dilation=1, bias=False):
        super().__init__()
        self.conv1 = nn.Conv2d(
            in_channels,
            in_channels,
            kernel_size,
            stride,
            padding,
            dilation,
            groups=in_channels,
            bias=bias,
        )
        self.pointwise = nn.Conv2d(in_channels, out_channels, 1, 1, 0, 1, 1, bias=bias)

    def forward(self, x):
        x = self.conv1(x)
        return self.pointwise(x)


class Block(nn.Module):
    def __init__(self, in_filters, out_filters, reps, strides=1, start_with_relu=True, grow_first=True):
        super().__init__()

        if out_filters != in_filters or strides != 1:
            self.skip = nn.Conv2d(in_filters, out_filters, 1, stride=strides, bias=False)
            self.skipbn = nn.BatchNorm2d(out_filters)
        else:
            self.skip = None

        rep = []
        filters = in_filters
        if grow_first:
            rep.append(nn.ReLU(inplace=True))
            rep.append(SeparableConv2d(in_filters, out_filters, 3, stride=1, padding=1, bias=False))
            rep.append(nn.BatchNorm2d(out_filters))
            filters = out_filters

        for _ in range(reps - 1):
            rep.append(nn.ReLU(inplace=True))
            rep.append(SeparableConv2d(filters, filters, 3, stride=1, padding=1, bias=False))
            rep.append(nn.BatchNorm2d(filters))

        if not grow_first:
            rep.append(nn.ReLU(inplace=True))
            rep.append(SeparableConv2d(in_filters, out_filters, 3, stride=1, padding=1, bias=False))
            rep.append(nn.BatchNorm2d(out_filters))

        if not start_with_relu:
            rep = rep[1:]
        else:
            rep[0] = nn.ReLU(inplace=False)

        if strides != 1:
            rep.append(nn.MaxPool2d(3, strides, 1))

        self.rep = nn.Sequential(*rep)

    def forward(self, inp):
        x = self.rep(inp)
        if self.skip is not None:
            skip = self.skipbn(self.skip(inp))
        else:
            skip = inp
        return x + skip


class Xception(nn.Module):
    def __init__(self, num_classes=2):
        super().__init__()
        self.num_classes = num_classes

        self.conv1 = nn.Conv2d(3, 32, 3, 2, 0, bias=False)
        self.bn1 = nn.BatchNorm2d(32)
        self.conv2 = nn.Conv2d(32, 64, 3, bias=False)
        self.bn2 = nn.BatchNorm2d(64)

        self.block1 = Block(64, 128, 2, 2, start_with_relu=False, grow_first=True)
        self.block2 = Block(128, 256, 2, 2, start_with_relu=True, grow_first=True)
        self.block3 = Block(256, 728, 2, 2, start_with_relu=True, grow_first=True)

        self.block4 = Block(728, 728, 3, 1, start_with_relu=True, grow_first=True)
        self.block5 = Block(728, 728, 3, 1, start_with_relu=True, grow_first=True)
        self.block6 = Block(728, 728, 3, 1, start_with_relu=True, grow_first=True)
        self.block7 = Block(728, 728, 3, 1, start_with_relu=True, grow_first=True)
        self.block8 = Block(728, 728, 3, 1, start_with_relu=True, grow_first=True)
        self.block9 = Block(728, 728, 3, 1, start_with_relu=True, grow_first=True)
        self.block10 = Block(728, 728, 3, 1, start_with_relu=True, grow_first=True)
        self.block11 = Block(728, 728, 3, 1, start_with_relu=True, grow_first=True)

        self.block12 = Block(728, 1024, 2, 2, start_with_relu=True, grow_first=False)

        self.conv3 = SeparableConv2d(1024, 1536, 3, 1, 1)
        self.bn3 = nn.BatchNorm2d(1536)
        self.conv4 = SeparableConv2d(1536, 2048, 3, 1, 1)
        self.bn4 = nn.BatchNorm2d(2048)
        self.fc = nn.Linear(2048, num_classes)

    def forward(self, x):
        x = self.conv1(x)
        x = self.bn1(x)
        x = F.relu(x, inplace=True)

        x = self.conv2(x)
        x = self.bn2(x)
        x = F.relu(x, inplace=True)

        x = self.block1(x)
        x = self.block2(x)
        x = self.block3(x)
        x = self.block4(x)
        x = self.block5(x)
        x = self.block6(x)
        x = self.block7(x)
        x = self.block8(x)
        x = self.block9(x)
        x = self.block10(x)
        x = self.block11(x)
        x = self.block12(x)

        x = self.conv3(x)
        x = self.bn3(x)
        x = F.relu(x, inplace=True)

        x = self.conv4(x)
        x = self.bn4(x)
        x = F.relu(x, inplace=True)

        x = F.adaptive_avg_pool2d(x, (1, 1))
        x = torch.flatten(x, 1)
        return self.fc(x)
