import os

import torch
import torch.nn as nn
import torch.optim as optim
import typer
from model import get_model
from tqdm import tqdm

import wandb
from data import PokeData


def train_model(num_classes: int = 1000, batch_size: int = 32, num_epochs: int = 100, lr: float = 1e-4, wd: float = 1e-4) -> None:
    # Initialize Weights & Biases
    run = wandb.init(
        project="pokedec_train",
        entity="pokedec_mlops",
        config={"lr": lr, "batch_size": batch_size, "epochs": num_epochs},
        job_type="train",
        name=f"pokedec_model_bs_{batch_size}_e_{num_epochs}_lr_{lr}_wd_{wd}",
    )

    # Load model
    model = get_model(num_classes=num_classes)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    model = model.to(device)

    # Load data
    poke_data = PokeData(data_path='data', batch_size=batch_size)
    train_loader = poke_data._get_train_loader()
    val_loader = poke_data._get_val_loader()

    # Define loss and optimizer
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=wd)

    # Learning rate scheduler (optional)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=5, gamma=0.1)   


    # Training loop
    for epoch in range(num_epochs):
        print(f"Epoch {epoch+1}/{num_epochs}")

        # Training phase
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0
        for inputs, labels in tqdm(train_loader):
            inputs, labels = inputs.to(device), labels.to(device)
            optimizer.zero_grad()

            # Forward pass
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            # Statistics
            running_loss += loss.item() * inputs.size(0)
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += predicted.eq(labels).sum().item()

        epoch_loss = running_loss / len(train_loader.dataset)
        epoch_acc = correct / total
        print(f"Train Loss: {epoch_loss:.4f}, Train Acc: {epoch_acc:.4f}")


        # Validation phase
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0
        with torch.no_grad():
            for inputs, labels in val_loader:
                inputs, labels = inputs.to(device), labels.to(device)
                outputs = model(inputs)
                loss = criterion(outputs, labels)

                val_loss += loss.item() * inputs.size(0)
                _, predicted = outputs.max(1)
                val_total += labels.size(0)
                val_correct += predicted.eq(labels).sum().item()

        val_loss /= len(val_loader.dataset)
        val_acc = val_correct / val_total
        print(f"Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.4f}")
        
        wandb.log({"train_loss": epoch_loss, "train_accuracy": epoch_acc, "val_loss": val_loss, "val_accuracy": val_acc})

        # Step the scheduler
        scheduler.step()
    
    print("Finished Training")

    # Save the model
    os.makedirs("models/sweep", exist_ok=True)
    torch.save(model.state_dict(), f"models/sweep/pokedec_model_bs_{batch_size}_e_{num_epochs}_lr_{lr}_wd_{wd}.pth")
    artifact = wandb.Artifact(
        name=f"pokedec_models",
        type="model",
        description="Model trained to classfiy Pokemon during sweep",
    )
    artifact.add_file(f"models/sweep/pokedec_model_bs_{batch_size}_e_{num_epochs}_lr_{lr}_wd_{wd}.pth")
    run.log_artifact(artifact)
    wandb.finish()

if __name__ == "__main__":
    typer.run(train_model)