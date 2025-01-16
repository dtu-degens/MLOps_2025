import torch
import torch.nn as nn
import torch.optim as optim
from tqdm import tqdm

from src.pokedec.data import PokeData
from src.pokedec.model import get_model


def train_model(num_classes: int, batch_size: int, epochs: int, lr: int) -> None:
    # Load model
    model = get_model('resnet50', num_classes=num_classes)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = model.to(device)

    # Load data
    poke_data = PokeData('data', batch_size=batch_size)
    train_loader = poke_data._get_train_loader()
    val_loader = poke_data._get_val_loader()
    test_lodaer = poke_data._get_test_loader()

    # Define loss and optimizer
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)

    # Learning rate scheduler (optional)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=5, gamma=0.1)   


    # Training loop
    num_epochs = epochs
    for epoch in range(num_epochs):
        print(f"Epoch {epoch+1}/{num_epochs}")

        # Training phase
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0
        for inputs, labels in tqdm(PokeData.train):
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

        epoch_loss = running_loss / len(PokeData.train)
        epoch_acc = correct / total
        print(f"Train Loss: {epoch_loss:.4f}, Train Acc: {epoch_acc:.4f}")


        # Validation phase
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0
        with torch.no_grad():
            for inputs, labels in PokeData.val:
                inputs, labels = inputs.to(device), labels.to(device)
                outputs = model(inputs)
                loss = criterion(outputs, labels)

                val_loss += loss.item() * inputs.size(0)
                _, predicted = outputs.max(1)
                val_total += labels.size(0)
                val_correct += predicted.eq(labels).sum().item()

        val_loss /= len(PokeData.val)
        val_acc = val_correct / val_total
        print(f"Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.4f}")


        # Step the scheduler
        scheduler.step()
    
    print("Finished Training")

    # Save the model
    torch.save(model.state_dict(), 'resnet50d_finetuned.pth')
