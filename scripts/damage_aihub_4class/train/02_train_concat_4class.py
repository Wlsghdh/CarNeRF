#!/usr/bin/env python3
"""
Multi-backbone Concat 분류기 (논문 제안 방식)

ResNet50 + ConvNeXt V2-Base + Swin-Base
→ feature concat → MLP classifier
→ 4-class softmax (scratch/dent/breakage/separation)

학습 전략:
  Phase 1 (5 epoch): Backbone 동결, MLP만 학습
  Phase 2 (15 epoch): Backbone 일부 unfreeze + MLP fine-tune

Augmentation: RandAug + RandomErasing + ColorJitter + MixUp
Loss: Class-weighted Cross-Entropy + Label smoothing
"""

import argparse
import json
import os
import time
from collections import Counter

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
import timm
from sklearn.metrics import f1_score, classification_report


CLASS_NAMES = ["breakage", "dent", "scratch", "separation"]  # ImageFolder 알파벳 순


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--data-root", default="./datasets/cls_crops")
    p.add_argument("--epochs-phase1", type=int, default=5)
    p.add_argument("--epochs-phase2", type=int, default=15)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--lr-mlp", type=float, default=3e-4)
    p.add_argument("--lr-backbone", type=float, default=1e-5)
    p.add_argument("--device", default="cuda:2")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--output-dir", default="./outputs/concat_v1")
    p.add_argument("--patience", type=int, default=5)
    p.add_argument("--label-smooth", type=float, default=0.1)
    p.add_argument("--mixup-alpha", type=float, default=0.2)
    p.add_argument("--weight-decay", type=float, default=1e-4)
    p.add_argument("--dropout", type=float, default=0.3)
    return p.parse_args()


class ConcatModel(nn.Module):
    """3개 backbone에서 feature 추출 → concat → MLP"""

    def __init__(self, num_classes=4, dropout=0.3):
        super().__init__()
        # Backbones (timm으로 통일)
        self.resnet = timm.create_model(
            "resnet50", pretrained=True, num_classes=0, global_pool="avg"
        )
        self.convnext = timm.create_model(
            "convnextv2_base", pretrained=True, num_classes=0, global_pool="avg"
        )
        self.swin = timm.create_model(
            "swin_base_patch4_window7_224", pretrained=True,
            num_classes=0, global_pool="avg"
        )
        # Feature dims (확인)
        self.dim_r = self.resnet.num_features    # 2048
        self.dim_c = self.convnext.num_features  # 1024
        self.dim_s = self.swin.num_features      # 1024
        total = self.dim_r + self.dim_c + self.dim_s

        self.mlp = nn.Sequential(
            nn.Linear(total, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout),
            nn.Linear(512, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout * 0.7),
            nn.Linear(128, num_classes),
        )

    def freeze_backbones(self):
        for backbone in [self.resnet, self.convnext, self.swin]:
            for p in backbone.parameters():
                p.requires_grad = False

    def unfreeze_backbones(self, last_n_blocks=None):
        """일부만 unfreeze (옵션). None이면 전체."""
        for backbone in [self.resnet, self.convnext, self.swin]:
            for p in backbone.parameters():
                p.requires_grad = True

    def forward(self, x):
        with torch.amp.autocast("cuda"):
            f_r = self.resnet(x)
            f_c = self.convnext(x)
            f_s = self.swin(x)
        feat = torch.cat([f_r, f_c, f_s], dim=1)
        out = self.mlp(feat)
        return out


def get_transforms(img_size=224, train=True):
    if train:
        return transforms.Compose([
            transforms.Resize(256),
            transforms.RandomResizedCrop(img_size, scale=(0.7, 1.0), ratio=(0.85, 1.15)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(15),
            transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3, hue=0.05),
            transforms.RandAugment(num_ops=2, magnitude=9),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
            transforms.RandomErasing(p=0.25, scale=(0.02, 0.2)),
        ])
    return transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(img_size),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])


def get_class_weights(dataset):
    targets = [s[1] for s in dataset.samples]
    counter = Counter(targets)
    total = len(targets)
    n_cls = len(counter)
    return torch.FloatTensor([total / (n_cls * counter[i]) for i in range(n_cls)])


def mixup_data(x, y, alpha=0.2):
    if alpha > 0:
        lam = np.random.beta(alpha, alpha)
    else:
        lam = 1.0
    idx = torch.randperm(x.size(0), device=x.device)
    return lam * x + (1 - lam) * x[idx], y, y[idx], lam


def mixup_criterion(criterion, pred, y_a, y_b, lam):
    return lam * criterion(pred, y_a) + (1 - lam) * criterion(pred, y_b)


def train_one_epoch(model, loader, optimizer, criterion, scaler, device,
                     mixup_alpha=0.2):
    model.train()
    total_loss, correct, total = 0.0, 0, 0
    for imgs, labels in loader:
        imgs = imgs.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)
        optimizer.zero_grad()
        mixed, y_a, y_b, lam = mixup_data(imgs, labels, mixup_alpha)
        with torch.amp.autocast("cuda"):
            outputs = model(mixed)
            loss = mixup_criterion(criterion, outputs, y_a, y_b, lam)
        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()
        total_loss += loss.item() * imgs.size(0)
        correct += (outputs.argmax(1) == labels).sum().item()
        total += imgs.size(0)
    return total_loss / total, correct / total


def evaluate(model, loader, device):
    model.eval()
    all_preds, all_labels = [], []
    with torch.no_grad():
        for imgs, labels in loader:
            imgs = imgs.to(device)
            with torch.amp.autocast("cuda"):
                outputs = model(imgs)
            preds = outputs.argmax(1).cpu().tolist()
            all_preds.extend(preds)
            all_labels.extend(labels.tolist())
    acc = (np.array(all_preds) == np.array(all_labels)).mean()
    macro_f1 = f1_score(all_labels, all_preds, average="macro")
    weighted_f1 = f1_score(all_labels, all_preds, average="weighted")
    return acc, macro_f1, weighted_f1, all_preds, all_labels


def main():
    args = parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    device = torch.device(args.device)

    print("Loading datasets...")
    train_ds = datasets.ImageFolder(
        os.path.join(args.data_root, "train"), get_transforms(224, train=True)
    )
    val_ds = datasets.ImageFolder(
        os.path.join(args.data_root, "val"), get_transforms(224, train=False)
    )
    print(f"Classes: {train_ds.classes}")
    print(f"Train: {len(train_ds):,}, Val: {len(val_ds):,}")

    class_weights = get_class_weights(train_ds).to(device)
    print(f"Class weights: {class_weights.tolist()}")

    train_loader = DataLoader(
        train_ds, batch_size=args.batch_size, shuffle=True,
        num_workers=args.workers, pin_memory=True, drop_last=True
    )
    val_loader = DataLoader(
        val_ds, batch_size=args.batch_size, shuffle=False,
        num_workers=args.workers, pin_memory=True
    )

    print("\nBuilding Concat model (ResNet50 + ConvNeXtV2-Base + Swin-Base)...")
    model = ConcatModel(num_classes=4, dropout=args.dropout).to(device)
    n_total = sum(p.numel() for p in model.parameters())
    print(f"  Total params: {n_total/1e6:.1f}M")
    print(f"  Feature dims: R={model.dim_r}, C={model.dim_c}, S={model.dim_s}")

    criterion = nn.CrossEntropyLoss(
        weight=class_weights, label_smoothing=args.label_smooth
    )

    history = []
    best_f1 = 0.0
    patience_counter = 0
    scaler = torch.amp.GradScaler("cuda")

    # ── Phase 1: Backbone freeze + MLP only ──
    print(f"\n=== Phase 1: Frozen backbones, MLP-only ({args.epochs_phase1} epochs) ===")
    model.freeze_backbones()
    mlp_params = list(model.mlp.parameters())
    optimizer = torch.optim.AdamW(
        mlp_params, lr=args.lr_mlp, weight_decay=args.weight_decay
    )

    for epoch in range(1, args.epochs_phase1 + 1):
        t0 = time.time()
        tr_loss, tr_acc = train_one_epoch(
            model, train_loader, optimizer, criterion, scaler, device,
            mixup_alpha=args.mixup_alpha
        )
        val_acc, macro_f1, w_f1, preds, labels = evaluate(model, val_loader, device)
        elapsed = time.time() - t0
        print(f"P1-Epoch {epoch:02d}/{args.epochs_phase1} | "
              f"tr_loss: {tr_loss:.4f} tr_acc: {tr_acc:.4f} | "
              f"val_acc: {val_acc:.4f} macro_f1: {macro_f1:.4f} w_f1: {w_f1:.4f} | "
              f"{elapsed:.0f}s")
        history.append({"phase": 1, "epoch": epoch, "tr_loss": tr_loss,
                        "tr_acc": tr_acc, "val_acc": val_acc,
                        "macro_f1": macro_f1, "w_f1": w_f1})
        if macro_f1 > best_f1:
            best_f1 = macro_f1
            torch.save(model.state_dict(), os.path.join(args.output_dir, "best.pt"))
            print(f"  → Best (macro_f1: {best_f1:.4f})")

    # ── Phase 2: Unfreeze backbone + lower lr ──
    print(f"\n=== Phase 2: Fine-tune full model ({args.epochs_phase2} epochs) ===")
    model.unfreeze_backbones()
    backbone_params = (
        list(model.resnet.parameters())
        + list(model.convnext.parameters())
        + list(model.swin.parameters())
    )
    optimizer = torch.optim.AdamW([
        {"params": backbone_params, "lr": args.lr_backbone},
        {"params": model.mlp.parameters(), "lr": args.lr_mlp * 0.3},
    ], weight_decay=args.weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=args.epochs_phase2
    )

    for epoch in range(1, args.epochs_phase2 + 1):
        t0 = time.time()
        tr_loss, tr_acc = train_one_epoch(
            model, train_loader, optimizer, criterion, scaler, device,
            mixup_alpha=args.mixup_alpha
        )
        scheduler.step()
        val_acc, macro_f1, w_f1, preds, labels = evaluate(model, val_loader, device)
        elapsed = time.time() - t0
        print(f"P2-Epoch {epoch:02d}/{args.epochs_phase2} | "
              f"tr_loss: {tr_loss:.4f} tr_acc: {tr_acc:.4f} | "
              f"val_acc: {val_acc:.4f} macro_f1: {macro_f1:.4f} w_f1: {w_f1:.4f} | "
              f"{elapsed:.0f}s")
        history.append({"phase": 2, "epoch": epoch, "tr_loss": tr_loss,
                        "tr_acc": tr_acc, "val_acc": val_acc,
                        "macro_f1": macro_f1, "w_f1": w_f1})

        if macro_f1 > best_f1:
            best_f1 = macro_f1
            patience_counter = 0
            torch.save(model.state_dict(), os.path.join(args.output_dir, "best.pt"))
            print(f"  → Best (macro_f1: {best_f1:.4f})")

            report = classification_report(
                labels, preds, target_names=train_ds.classes, digits=4
            )
            with open(os.path.join(args.output_dir, "best_report.txt"), "w") as fp:
                fp.write(report)
        else:
            patience_counter += 1
            if patience_counter >= args.patience:
                print(f"  Early stopping at epoch {epoch}")
                break

    # Save
    with open(os.path.join(args.output_dir, "history.json"), "w") as fp:
        json.dump(history, fp, indent=2)
    with open(os.path.join(args.output_dir, "config.json"), "w") as fp:
        json.dump(vars(args), fp, indent=2)

    print(f"\nDone. Best macro F1: {best_f1:.4f}")


if __name__ == "__main__":
    main()
