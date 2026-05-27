#!/usr/bin/env python3
"""
5-class Concat 분류기 학습 (Approach A - Stage 2)

이전 18번 스크립트 + normal 클래스 추가
ResNet50 + ConvNeXtV2-Base + Swin-Base → concat → MLP → 5 classes

목적: YOLO bbox crop을 받아서:
  - normal: FP 제거
  - scratch/dent/breakage/separation: 손상 유형 분류
"""

import argparse
import json
import os
import time
from collections import Counter

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
import timm
from sklearn.metrics import f1_score, classification_report


# 5 classes (ImageFolder 알파벳 순)
CLASS_NAMES = ["breakage", "dent", "normal", "scratch", "separation"]
NUM_CLASSES = 5


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--data-root", default="./datasets/cls_crops_5class")
    p.add_argument("--epochs-phase1", type=int, default=5)
    p.add_argument("--epochs-phase2", type=int, default=15)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--lr-mlp", type=float, default=3e-4)
    p.add_argument("--lr-backbone", type=float, default=1e-5)
    p.add_argument("--device", default="cuda:2")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--output-dir", default="./outputs/concat_5class_v1")
    p.add_argument("--patience", type=int, default=5)
    p.add_argument("--label-smooth", type=float, default=0.1)
    p.add_argument("--mixup-alpha", type=float, default=0.2)
    p.add_argument("--weight-decay", type=float, default=1e-4)
    p.add_argument("--dropout", type=float, default=0.3)
    p.add_argument("--resume", default=None,
                   help="Path to last_ckpt.pt to resume from")
    return p.parse_args()


class ConcatModel(nn.Module):
    def __init__(self, num_classes=5, dropout=0.3):
        super().__init__()
        self.resnet = timm.create_model("resnet50", pretrained=True,
                                         num_classes=0, global_pool="avg")
        self.convnext = timm.create_model("convnextv2_base", pretrained=True,
                                           num_classes=0, global_pool="avg")
        self.swin = timm.create_model("swin_base_patch4_window7_224",
                                       pretrained=True, num_classes=0,
                                       global_pool="avg")
        self.dim_r = self.resnet.num_features
        self.dim_c = self.convnext.num_features
        self.dim_s = self.swin.num_features
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
        for m in [self.resnet, self.convnext, self.swin]:
            for p in m.parameters():
                p.requires_grad = False

    def unfreeze_backbones(self):
        for m in [self.resnet, self.convnext, self.swin]:
            for p in m.parameters():
                p.requires_grad = True

    def forward(self, x):
        with torch.amp.autocast("cuda"):
            f_r = self.resnet(x)
            f_c = self.convnext(x)
            f_s = self.swin(x)
        return self.mlp(torch.cat([f_r, f_c, f_s], dim=1))


def get_class_weights(dataset):
    targets = [s[1] for s in dataset.samples]
    cnt = Counter(targets)
    total = len(targets)
    n_cls = len(cnt)
    return torch.FloatTensor([total / (n_cls * cnt[i]) for i in range(n_cls)])


def mixup_data(x, y, alpha=0.2):
    lam = np.random.beta(alpha, alpha) if alpha > 0 else 1.0
    idx = torch.randperm(x.size(0), device=x.device)
    return lam * x + (1 - lam) * x[idx], y, y[idx], lam


def mixup_criterion(criterion, pred, y_a, y_b, lam):
    return lam * criterion(pred, y_a) + (1 - lam) * criterion(pred, y_b)


def train_epoch(model, loader, optimizer, criterion, scaler, device, mixup_alpha):
    model.train()
    tot_loss, correct, total = 0.0, 0, 0
    for imgs, labels in loader:
        imgs, labels = imgs.to(device), labels.to(device)
        optimizer.zero_grad()
        mixed, y_a, y_b, lam = mixup_data(imgs, labels, mixup_alpha)
        with torch.amp.autocast("cuda"):
            out = model(mixed)
            loss = mixup_criterion(criterion, out, y_a, y_b, lam)
        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()
        tot_loss += loss.item() * imgs.size(0)
        correct += (out.argmax(1) == labels).sum().item()
        total += imgs.size(0)
    return tot_loss / total, correct / total


def save_full_ckpt(path, model, optimizer, scheduler, phase, epoch,
                    best_f1, patience, history, scaler):
    ckpt = {
        "model": model.state_dict(),
        "optimizer": optimizer.state_dict() if optimizer is not None else None,
        "scheduler": scheduler.state_dict() if scheduler is not None else None,
        "scaler": scaler.state_dict() if scaler is not None else None,
        "phase": phase,
        "epoch": epoch,
        "best_f1": best_f1,
        "patience": patience,
        "history": history,
    }
    tmp = path + ".tmp"
    torch.save(ckpt, tmp)
    os.replace(tmp, path)


def evaluate(model, loader, device):
    model.eval()
    all_preds, all_labels = [], []
    with torch.no_grad():
        for imgs, labels in loader:
            imgs = imgs.to(device)
            with torch.amp.autocast("cuda"):
                out = model(imgs)
            all_preds.extend(out.argmax(1).cpu().tolist())
            all_labels.extend(labels.tolist())
    acc = (np.array(all_preds) == np.array(all_labels)).mean()
    macro_f1 = f1_score(all_labels, all_preds, average="macro")
    return acc, macro_f1, all_preds, all_labels


def main():
    args = parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    device = torch.device(args.device)

    train_tf = transforms.Compose([
        transforms.Resize(256),
        transforms.RandomResizedCrop(224, scale=(0.7, 1.0), ratio=(0.85, 1.15)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(15),
        transforms.ColorJitter(0.3, 0.3, 0.3, 0.05),
        transforms.RandAugment(num_ops=2, magnitude=9),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        transforms.RandomErasing(p=0.25, scale=(0.02, 0.2)),
    ])
    val_tf = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])

    train_ds = datasets.ImageFolder(os.path.join(args.data_root, "train"), train_tf)
    val_ds = datasets.ImageFolder(os.path.join(args.data_root, "val"), val_tf)
    print(f"Classes: {train_ds.classes}")
    print(f"Train: {len(train_ds):,}, Val: {len(val_ds):,}")

    class_weights = get_class_weights(train_ds).to(device)
    print(f"Class weights: {class_weights.tolist()}")

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True,
                              num_workers=args.workers, pin_memory=True, drop_last=True)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False,
                            num_workers=args.workers, pin_memory=True)

    model = ConcatModel(num_classes=NUM_CLASSES, dropout=args.dropout).to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights, label_smoothing=args.label_smooth)
    scaler = torch.amp.GradScaler("cuda")

    best_f1 = 0.0
    patience = 0
    history = []
    start_phase = 1
    start_epoch = 1

    ckpt_path = os.path.join(args.output_dir, "last_ckpt.pt")

    # ─── Resume 처리 ───
    if args.resume and os.path.exists(args.resume):
        print(f"\n[RESUME] Loading checkpoint: {args.resume}")
        ckpt = torch.load(args.resume, map_location=device, weights_only=False)
        model.load_state_dict(ckpt["model"])
        best_f1 = ckpt.get("best_f1", 0.0)
        patience = ckpt.get("patience", 0)
        history = ckpt.get("history", [])
        last_phase = ckpt.get("phase", 1)
        last_epoch = ckpt.get("epoch", 0)
        # 마지막 완료 epoch의 다음부터 시작
        if last_phase == 1 and last_epoch < args.epochs_phase1:
            start_phase = 1
            start_epoch = last_epoch + 1
        else:
            start_phase = 2
            start_epoch = (last_epoch + 1) if last_phase == 2 else 1
        print(f"[RESUME] phase={start_phase}, start_epoch={start_epoch}, "
              f"best_f1={best_f1:.4f}, patience={patience}")
        resume_optim_state = ckpt.get("optimizer")
        resume_sched_state = ckpt.get("scheduler")
        resume_scaler_state = ckpt.get("scaler")
        if resume_scaler_state is not None:
            scaler.load_state_dict(resume_scaler_state)
    else:
        resume_optim_state = None
        resume_sched_state = None

    # ─── Phase 1: Frozen ───
    if start_phase == 1:
        print(f"\n=== Phase 1: Frozen backbones ({args.epochs_phase1} epochs, start={start_epoch}) ===")
        model.freeze_backbones()
        optimizer = torch.optim.AdamW(model.mlp.parameters(),
                                       lr=args.lr_mlp, weight_decay=args.weight_decay)
        if resume_optim_state is not None and start_epoch > 1:
            try:
                optimizer.load_state_dict(resume_optim_state)
                print("[RESUME] Phase 1 optimizer state loaded")
            except Exception as e:
                print(f"[RESUME] Phase 1 optimizer state mismatch, fresh: {e}")
        for ep in range(start_epoch, args.epochs_phase1 + 1):
            t0 = time.time()
            tr_loss, tr_acc = train_epoch(model, train_loader, optimizer, criterion,
                                           scaler, device, args.mixup_alpha)
            val_acc, macro_f1, preds, labels = evaluate(model, val_loader, device)
            print(f"P1-Ep{ep:02d} | tr_loss: {tr_loss:.4f} tr_acc: {tr_acc:.4f} | "
                  f"val_acc: {val_acc:.4f} macro_f1: {macro_f1:.4f} | {time.time()-t0:.0f}s",
                  flush=True)
            history.append({"phase": 1, "epoch": ep, "tr_loss": tr_loss,
                            "val_acc": val_acc, "macro_f1": macro_f1})
            if macro_f1 > best_f1:
                best_f1 = macro_f1
                torch.save(model.state_dict(), os.path.join(args.output_dir, "best.pt"))
                print(f"  → Best saved (F1: {best_f1:.4f})", flush=True)
            # 매 epoch마다 full ckpt 저장
            save_full_ckpt(ckpt_path, model, optimizer, None, 1, ep,
                           best_f1, patience, history, scaler)

        # Phase 1 끝나면 Phase 2로
        start_epoch = 1
        resume_optim_state = None
        resume_sched_state = None

    # ─── Phase 2: Unfreeze + fine-tune ───
    print(f"\n=== Phase 2: Fine-tune all ({args.epochs_phase2} epochs, start={start_epoch}) ===")
    model.unfreeze_backbones()
    backbone_params = list(model.resnet.parameters()) + \
                       list(model.convnext.parameters()) + list(model.swin.parameters())
    optimizer = torch.optim.AdamW([
        {"params": backbone_params, "lr": args.lr_backbone},
        {"params": model.mlp.parameters(), "lr": args.lr_mlp * 0.3},
    ], weight_decay=args.weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs_phase2)

    if resume_optim_state is not None and start_epoch > 1:
        try:
            optimizer.load_state_dict(resume_optim_state)
            print("[RESUME] Phase 2 optimizer state loaded")
        except Exception as e:
            print(f"[RESUME] Phase 2 optimizer state mismatch, fresh: {e}")
    if resume_sched_state is not None and start_epoch > 1:
        try:
            scheduler.load_state_dict(resume_sched_state)
            print("[RESUME] Phase 2 scheduler state loaded")
        except Exception as e:
            print(f"[RESUME] Phase 2 scheduler state mismatch, fresh: {e}")

    for ep in range(start_epoch, args.epochs_phase2 + 1):
        t0 = time.time()
        tr_loss, tr_acc = train_epoch(model, train_loader, optimizer, criterion,
                                       scaler, device, args.mixup_alpha)
        scheduler.step()
        val_acc, macro_f1, preds, labels = evaluate(model, val_loader, device)
        print(f"P2-Ep{ep:02d} | tr_loss: {tr_loss:.4f} tr_acc: {tr_acc:.4f} | "
              f"val_acc: {val_acc:.4f} macro_f1: {macro_f1:.4f} | {time.time()-t0:.0f}s",
              flush=True)
        history.append({"phase": 2, "epoch": ep, "tr_loss": tr_loss,
                        "val_acc": val_acc, "macro_f1": macro_f1})
        if macro_f1 > best_f1:
            best_f1 = macro_f1
            patience = 0
            torch.save(model.state_dict(), os.path.join(args.output_dir, "best.pt"))
            print(f"  → Best saved (F1: {best_f1:.4f})", flush=True)
            report = classification_report(labels, preds, target_names=train_ds.classes, digits=4)
            with open(os.path.join(args.output_dir, "best_report.txt"), "w") as f:
                f.write(report)
        else:
            patience += 1
        # 매 epoch마다 full ckpt 저장
        save_full_ckpt(ckpt_path, model, optimizer, scheduler, 2, ep,
                       best_f1, patience, history, scaler)
        if patience >= args.patience:
            print(f"Early stopping at ep {ep}", flush=True)
            break

    torch.save(model.state_dict(), os.path.join(args.output_dir, "last.pt"))
    with open(os.path.join(args.output_dir, "history.json"), "w") as f:
        json.dump(history, f, indent=2)
    with open(os.path.join(args.output_dir, "config.json"), "w") as f:
        json.dump(vars(args), f, indent=2)
    print(f"\nDone. Best macro F1: {best_f1:.4f}")


if __name__ == "__main__":
    main()
